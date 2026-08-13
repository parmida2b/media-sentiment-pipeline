"""
make_synthetic_annotated_dataset.py — synthetic stand-in for
data/processed/annotated_dataset.parquet (Parmida, Day 5+)

Pipeline B (docs/pipeline_b_input_contract.md) is only allowed to read one
file: the joined output of Pipeline A's `run_full_annotation.py`. That file
does not exist yet, so this script builds a FAKE dataset with EXACTLY the
same schema (every column name/type in the contract's table) so Pipeline B's
descriptive-stats and weekly-trend code (src/temporal_analysis/) can be
written and tested now, without waiting for real annotation to finish.

*** EVERY ROW THIS SCRIPT PRODUCES IS MADE UP. *** Text, engagement numbers,
labels, timestamps — none of it is real collected data and none of it may
ever be quoted or cited as a project finding (see the contract's closing
paragraph). It exists purely to exercise Pipeline B's code paths, including
edge cases real data is expected to contain:

  - realistic-but-imbalanced spread across 3 platforms (x/reddit/youtube)
    and 21 project weeks (W01-W21, per src/ingestion/project_calendar.py's
    START/END/project_week() — reused here, not reimplemented, so synthetic
    weeks line up with the real project calendar by construction)
  - a handful of low-volume weeks (<30 records) per platform
  - W21 always low-volume AND explicitly is_partial_week=True (it's a real
    5-day week per project_calendar.py, not an arbitrary choice)
  - one genuine data gap: reddit/W05 has ZERO rows (not just "few") — this
    is the case a weekly-trend script must surface explicitly instead of
    silently skipping a week that never appears in the dataframe
  - a batch of dataset_target="opinion_untimed" rows with created_at_utc
    and project_week genuinely null (not empty string)
  - a batch of annotation_status != "ok" rows (low_confidence /
    json_parse_failure / api_failure) that must be excluded from label
    tallies but reported as a coverage number (checklist.md §24)
  - is_near_duplicate / is_flagged_bot_suspect flags, each on a minority of
    rows, with near_duplicate_cluster_id populated only when the flag is set
  - an imbalanced language mix (fa/en dominant, ar a deliberate minority —
    matches docs/decision_log.md 2026-08-13's fa=45/en=45/ar=10 gold-sample
    split)
  - true nulls (Python None -> parquet null, not "") in every nullable
    column the contract lists, at a realistic non-zero rate

Usage:
    python scripts/make_synthetic_annotated_dataset.py
    python scripts/make_synthetic_annotated_dataset.py --seed 1405 --output data/processed/annotated_dataset.sample.parquet
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.annotation.model_routes import MODEL_ROUTES  # noqa: E402
from src.annotation.prompt_contract import PROMPT_VERSION  # noqa: E402
from src.annotation.schema import (  # noqa: E402
    CONTENT_TYPE_LABELS,
    EMOTION_LABELS,
    SENTIMENT_LABELS,
    STANCE_LABELS,
    TARGET_IDS,
)
from src.ingestion.project_calendar import END, START, project_week  # noqa: E402

DEFAULT_SEED = 1405  # docs/checklist.md §17 / decision_log.md 2026-08-13: project-wide fixed seed
DEFAULT_OUTPUT = ROOT / "data" / "processed" / "annotated_dataset.sample.parquet"

PLATFORMS = ["x", "reddit", "youtube"]
WEEKS = [f"W{w:02d}" for w in range(1, 22)]

# --- Edge cases the checklist prompt explicitly asked for -------------------

# One real data gap: this exact (platform, week) cell gets zero rows, not
# just few. A weekly-trend table must show n=0 here, not silently omit W05
# from reddit's series.
GAP_WEEKS: set[tuple[str, str]] = {("reddit", "W05")}

# A handful of additional low-volume weeks (<30 rows), spread across all
# three platforms so no single platform's code path goes untested.
LOW_VOLUME_WEEKS: dict[tuple[str, str], int] = {
    ("x", "W09"): 18,
    ("reddit", "W14"): 11,
    ("youtube", "W02"): 8,
}

# W21 is a real 5-day partial week (project_calendar.START/END), so it's
# naturally lower-volume than a full 7-day week — pinned explicitly (rather
# than left to the random draw) so it's <30 for every platform, exercising
# BOTH the is_partial_week flag AND the is_low_sample flag together.
PARTIAL_WEEK_COUNTS: dict[str, int] = {"x": 24, "reddit": 14, "youtube": 19}

# Most weeks: a random count in this range (comfortably >=30). Tuned so the
# full dataset (56 normal weeks + the fixed low-volume/gap/partial overrides
# above + the opinion_untimed batch) lands close to the requested ~3000 rows.
NORMAL_WEEK_RANGE = (33, 68)

# opinion_untimed rows (no timestamp at all) and non-"ok" annotation rows are
# both drawn as roughly this fraction of the *timed* row count.
UNTIMED_FRACTION = 0.045
NON_OK_FRACTION = 0.10  # split across low_confidence / json_parse_failure / api_failure

NEAR_DUPLICATE_RATE = 0.06
EXACT_DUPLICATE_RATE = 0.02
BOT_SUSPECT_RATE = 0.05

LANGUAGES = ["fa", "en", "ar", "other"]
LANGUAGE_WEIGHTS = [0.45, 0.40, 0.10, 0.05]  # fa/en dominant, ar a deliberate minority

SENTIMENT_WEIGHTS = {"negative": 0.42, "neutral": 0.28, "positive": 0.15, "mixed": 0.10, "unclear": 0.05}
STANCE_WEIGHTS = {"neutral_or_balanced": 0.30, "oppose": 0.25, "support": 0.20, "unrelated": 0.15, "unclear": 0.10}
EMOTION_WEIGHTS = {
    "anger": 0.25, "fear": 0.20, "sadness": 0.15, "hope": 0.10,
    "joy": 0.08, "disgust": 0.07, "surprise": 0.05, "none_or_unclear": 0.10,
}
CONTENT_TYPE_WEIGHTS = {
    "personal_opinion": 0.55, "news_or_report": 0.20, "quotation": 0.10,
    "satire": 0.05, "spam": 0.05, "unclear": 0.05,
}
TARGET_WEIGHTS = {  # primary T01-T03 weighted heavier, per schema.PRIMARY_TARGET_IDS
    "T01": 0.28, "T02": 0.22, "T03": 0.20, "T04": 0.12, "T05": 0.10, "T06": 0.08,
}

REASON_CODES = [
    "explicit_support_phrase", "explicit_oppose_phrase", "sarcastic_tone",
    "quotes_news_headline", "ambiguous_referent", "neutral_reporting_tone",
    "no_clear_target_mentioned", "context_inferred_from_thread",
    "strong_emotional_language", "factual_statement_no_opinion",
]

SOURCE_CONTAINERS = {
    "x": [None, None, "list:iran_watch", "search:iran_us_conflict"],
    "reddit": ["r/worldnews", "r/geopolitics", "r/IRstudies", "r/CredibleDefense", "r/iran"],
    "youtube": ["channel:bbcpersian", "channel:voanews", "channel:aljazeeraenglish", "channel:presstv"],
}
QUERY_IDS = [f"Q-IRUS-{i:03d}" for i in range(1, 16)]
QUERY_VERSIONS = ["v1", "v2", "v3"]
COUNTRIES = ["IR", "US", "GB", "CA", "TR", "AE", "DE", "FR"]
GEO_CONFIDENCES = ["high", "medium", "low"]

TEXT_FRAGMENTS = {
    "fa": [
        "این یک اظهار نظر مصنوعی درباره وضعیت منطقه است.",
        "به نظر می‌رسد شرایط سیاسی روزبه‌روز پیچیده‌تر می‌شود.",
        "خیلی‌ها نگران تأثیر این تحولات بر زندگی روزمره هستند.",
        "برخی کاربران این تصمیم را حمایت می‌کنند و برخی مخالفند.",
        "این متن صرفاً برای آزمایش خط لوله تحلیل داده تولید شده است.",
        "گزارش‌های خبری در این باره متناقض به نظر می‌رسند.",
        "احساس نگرانی در بین کاربران شبکه‌های اجتماعی زیاد شده است.",
        "این یک نقل‌قول فرضی از یک منبع خبری ساختگی است.",
    ],
    "en": [
        "This is a synthetic placeholder comment for pipeline testing.",
        "Many users seem divided over how this situation should be handled.",
        "The economic consequences of this policy remain unclear.",
        "This text is randomly generated and does not reflect any real opinion.",
        "Some commentators support the decision while others strongly oppose it.",
        "News coverage on this topic has been inconsistent across outlets.",
        "There is growing concern about the humanitarian impact of these events.",
        "This is a fabricated quote used only for schema testing purposes.",
    ],
    "ar": [
        "هذا نص تجريبي تم إنشاؤه لأغراض اختبار خط الأنابيب.",
        "يبدو أن الوضع السياسي يزداد تعقيدًا يومًا بعد يوم.",
        "ينقسم المستخدمون بين مؤيد ومعارض لهذا القرار.",
        "هذا اقتباس افتراضي من مصدر إخباري وهمي.",
    ],
    "other": [
        "Ceci est un commentaire synthétique généré pour tester le pipeline.",
        "Dies ist ein zufällig generierter Testkommentar ohne realen Bezug.",
        "Este es un comentario de prueba generado automáticamente.",
    ],
}

MODEL_VERSIONS = [route.model_name for route in MODEL_ROUTES]


def _weighted_choice(rng: np.random.Generator, weights: dict[str, float]) -> np.ndarray:
    keys = list(weights.keys())
    probs = np.array(list(weights.values()), dtype=float)
    probs = probs / probs.sum()
    return keys, probs


def week_bounds(w: int) -> tuple[datetime, datetime]:
    """Real week boundaries per project_calendar.START, mirroring the exact
    (start + (w-1)*7 days, +7 days) math project_week() itself uses, so a
    timestamp drawn here is guaranteed to round-trip back to the same week
    label through project_week()."""
    week_start = START + timedelta(days=(w - 1) * 7)
    week_end = min(week_start + timedelta(days=7) - timedelta(seconds=1), END)
    return week_start, week_end


def random_timestamp(rng: np.random.Generator, lo: datetime, hi: datetime) -> datetime:
    lo_ts, hi_ts = lo.timestamp(), hi.timestamp()
    return datetime.utcfromtimestamp(rng.uniform(lo_ts, hi_ts)).replace(tzinfo=lo.tzinfo)


def make_text(rng: np.random.Generator, language: str) -> str:
    fragments = TEXT_FRAGMENTS.get(language, TEXT_FRAGMENTS["en"])
    n_sentences = int(np.clip(1 + rng.poisson(1.3), 1, 6))
    chosen = rng.choice(fragments, size=n_sentences, replace=True)
    return " ".join(chosen.tolist())


def make_id(prefix: str, rng: np.random.Generator) -> str:
    """A plausible-looking, rng-derived (so seed-reproducible) unique id.
    Deliberately not uuid.uuid4() — that draws from OS randomness and would
    make the whole dataset non-reproducible across runs of the same seed."""
    raw = int(rng.integers(0, 2**63 - 1, dtype=np.int64))
    return f"{prefix}_{raw:016x}"


def build_weekly_counts(rng: np.random.Generator) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {}
    for platform in PLATFORMS:
        weekly: dict[str, int] = {}
        for week in WEEKS:
            if (platform, week) in GAP_WEEKS:
                n = 0
            elif (platform, week) in LOW_VOLUME_WEEKS:
                n = LOW_VOLUME_WEEKS[(platform, week)]
            elif week == "W21":
                n = PARTIAL_WEEK_COUNTS[platform]
            else:
                n = int(rng.integers(*NORMAL_WEEK_RANGE))
            weekly[week] = n
        counts[platform] = weekly
    return counts


def make_annotation_fields(rng: np.random.Generator, status: str) -> dict:
    """Build the §22 annotation-output columns for one row.

    For status == "ok"/"low_confidence" this draws real (weighted-random)
    labels. For "json_parse_failure"/"api_failure" the model call did not
    produce a usable structured output, so labels fall back to each axis's
    own "couldn't determine" enum member (sentiment/stance/content_type all
    have "unclear", emotion has "none_or_unclear") rather than a bare null —
    every one of those four columns is documented as plain `str` (not
    nullable) in pipeline_b_input_contract.md, only `target` is. `target` is
    set to None here even though stance_label != "unrelated" in this branch,
    which is a deliberate, documented deviation from the contract's literal
    "target is null only if stance_label=unrelated" rule — see this script's
    closing note / the prompt's schema-ambiguity write-up: a failed call has
    no real evidence for ANY Target, so nulling it seemed like the safer
    synthetic choice than fabricating one. confidence=0.0 is used as an
    explicit "no real confidence" sentinel, also to satisfy the non-nullable
    float type."""
    if status in ("json_parse_failure", "api_failure"):
        return {
            "target": None,
            "sentiment_label": "unclear",
            "stance_label": "unclear",
            "emotion_label": "none_or_unclear",
            "content_type_label": "unclear",
            "confidence": 0.0,
            "reason_code": status,
        }

    stance_keys, stance_probs = _weighted_choice(rng, STANCE_WEIGHTS)
    stance = rng.choice(stance_keys, p=stance_probs)
    sentiment_keys, sentiment_probs = _weighted_choice(rng, SENTIMENT_WEIGHTS)
    emotion_keys, emotion_probs = _weighted_choice(rng, EMOTION_WEIGHTS)
    content_type_keys, content_type_probs = _weighted_choice(rng, CONTENT_TYPE_WEIGHTS)

    if stance == "unrelated":
        target = None
    else:
        target_keys, target_probs = _weighted_choice(rng, TARGET_WEIGHTS)
        target = rng.choice(target_keys, p=target_probs)

    if status == "low_confidence":
        confidence = float(rng.uniform(0.30, 0.59))
    else:
        confidence = float(rng.uniform(0.60, 0.99))

    return {
        "target": target,
        "sentiment_label": rng.choice(sentiment_keys, p=sentiment_probs),
        "stance_label": stance,
        "emotion_label": rng.choice(emotion_keys, p=emotion_probs),
        "content_type_label": rng.choice(content_type_keys, p=content_type_probs),
        "confidence": confidence,
        "reason_code": rng.choice(REASON_CODES),
    }


def make_row(
    rng: np.random.Generator,
    platform: str,
    week: str | None,
    row_seq: int,
) -> dict:
    """Build one full-schema row. `week=None` means opinion_untimed (no
    timestamp at all — created_at_utc/project_week/in_window/is_partial_week
    all reflect "no time information available")."""
    content_id = make_id(platform, rng)
    has_parent = rng.random() < 0.35
    has_post = rng.random() < 0.95

    if week is None:
        dataset_target = "opinion_untimed"
        created_at_utc = None
        proj_week = None
        in_window = False
        is_partial_week = False
        provenance_quality = rng.choice(["full", "partial", "unknown"], p=[0.6, 0.3, 0.1])
        annotated_at = random_timestamp(rng, START, END + timedelta(days=20))
    else:
        w = int(week[1:])
        lo, hi = week_bounds(w)
        ts = random_timestamp(rng, lo, hi)
        proj_week, in_window, is_partial_week = project_week(ts)
        assert proj_week == week, f"week math drifted: expected {week}, got {proj_week}"
        created_at_utc = ts.strftime("%Y-%m-%dT%H:%M:%SZ")
        dataset_target = rng.choice(["opinion_main", "opinion_limited"], p=[0.85, 0.15])
        provenance_quality = "partial" if dataset_target == "opinion_limited" else rng.choice(
            ["full", "unknown"], p=[0.95, 0.05]
        )
        annotated_at = ts + timedelta(hours=float(rng.uniform(1, 96)))

    language = rng.choice(LANGUAGES, p=LANGUAGE_WEIGHTS)
    language_confidence = None if rng.random() < 0.05 else float(rng.uniform(0.55, 0.99))

    has_country = rng.random() < 0.45
    country = rng.choice(COUNTRIES) if has_country else None
    geo_confidence = rng.choice(GEO_CONFIDENCES, p=[0.2, 0.5, 0.3]) if has_country else None

    automation_risk_score_user = None if rng.random() < 0.10 else float(np.clip(rng.beta(2, 8), 0, 1))
    is_flagged_bot_suspect = bool(
        rng.random() < (0.6 if (automation_risk_score_user or 0) > 0.7 else BOT_SUSPECT_RATE)
    )

    is_near_duplicate = bool(rng.random() < NEAR_DUPLICATE_RATE)
    is_exact_duplicate = bool(rng.random() < EXACT_DUPLICATE_RATE)
    near_duplicate_cluster_id = make_id("cluster", rng) if is_near_duplicate else None

    status_roll = rng.random()
    if status_roll < NON_OK_FRACTION * 0.5:
        annotation_status = "low_confidence"
    elif status_roll < NON_OK_FRACTION * 0.8:
        annotation_status = "json_parse_failure"
    elif status_roll < NON_OK_FRACTION:
        annotation_status = "api_failure"
    else:
        annotation_status = "ok"

    annotation_fields = make_annotation_fields(rng, annotation_status)

    row = {
        "content_id": content_id,
        "platform": platform,
        "parent_id": make_id("parent", rng) if has_parent else None,
        "post_id": make_id("post", rng) if has_post else None,
        "dataset_target": dataset_target,
        "provenance_quality": provenance_quality,
        "created_at_utc": created_at_utc,
        "project_week": proj_week,
        "in_window": bool(in_window),
        "is_partial_week": bool(is_partial_week),
        "text_raw": make_text(rng, language),
        "source_id": None if rng.random() < 0.08 else f"SRC-{platform.upper()}-{int(rng.integers(1, 7)):02d}",
        "source_container": rng.choice(SOURCE_CONTAINERS[platform]),
        "query_id": None if rng.random() < 0.08 else rng.choice(QUERY_IDS),
        "query_version": None if rng.random() < 0.10 else rng.choice(QUERY_VERSIONS),
        "language_detected": language,
        "language_confidence": language_confidence,
        "country_or_region": country,
        "geo_confidence": geo_confidence,
        "engagement_score": int(rng.exponential(15)),
        "engagement_replies": int(rng.exponential(3)),
        "engagement_shares": int(rng.exponential(5)),
        "engagement_views": int(rng.exponential(800)),
        "author_hash": None if rng.random() < 0.07 else make_id("auth", rng)[:20],
        "automation_risk_score_user": automation_risk_score_user,
        "is_flagged_bot_suspect": is_flagged_bot_suspect,
        "is_exact_duplicate": is_exact_duplicate,
        "is_near_duplicate": is_near_duplicate,
        "near_duplicate_cluster_id": near_duplicate_cluster_id,
        "annotation_status": annotation_status,
        "model_version": rng.choice(MODEL_VERSIONS),
        "prompt_version": PROMPT_VERSION,
        "annotated_at_utc": annotated_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    row.update(annotation_fields)
    return row


def generate_dataset(seed: int = DEFAULT_SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    weekly_counts = build_weekly_counts(rng)

    rows: list[dict] = []
    seq = 0
    for platform in PLATFORMS:
        for week in WEEKS:
            n = weekly_counts[platform][week]
            for _ in range(n):
                rows.append(make_row(rng, platform, week, seq))
                seq += 1

    timed_total = len(rows)
    untimed_total = int(timed_total * UNTIMED_FRACTION)
    untimed_platforms = rng.choice(PLATFORMS, size=untimed_total)
    for platform in untimed_platforms:
        rows.append(make_row(rng, platform, None, seq))
        seq += 1

    df = pd.DataFrame(rows)

    # A few EXACT duplicates need to actually share text_raw with another row
    # to produce a measurable duplicate rate downstream (is_exact_duplicate
    # alone, without matching text, wouldn't let a text-based sanity check
    # confirm the flag means anything). Pair each is_exact_duplicate=True row
    # with a same-platform donor row's text.
    exact_dup_idx = df.index[df["is_exact_duplicate"]].tolist()
    for idx in exact_dup_idx:
        platform = df.at[idx, "platform"]
        donor_pool = df.index[(df["platform"] == platform) & (~df["is_exact_duplicate"])]
        if len(donor_pool) == 0:
            continue
        donor = rng.choice(donor_pool)
        df.at[idx, "text_raw"] = df.at[donor, "text_raw"]

    return df


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    df = generate_dataset(seed=args.seed)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(args.output, index=False, engine="pyarrow")

    print(f"Wrote {len(df)} synthetic rows to {args.output} (seed={args.seed}).")
    print(f"By platform: {df['platform'].value_counts().to_dict()}")
    print(f"By dataset_target: {df['dataset_target'].value_counts().to_dict()}")
    print(f"By annotation_status: {df['annotation_status'].value_counts().to_dict()}")
    print(f"By language_detected: {df['language_detected'].value_counts().to_dict()}")
    gap_check = df[(df["platform"] == "reddit") & (df["project_week"] == "W05")]
    print(f"reddit/W05 row count (expected 0, the deliberate data gap): {len(gap_check)}")
    w21 = df[df["project_week"] == "W21"]
    print(f"W21 rows: {len(w21)} (is_partial_week all True: {w21['is_partial_week'].all() if len(w21) else 'n/a'})")


if __name__ == "__main__":
    main()
