"""
build_relevance_audit_sample.py — implements docs/checklist.md §14
(Relevance Audit انسانی)

Reads apply_eligibility.py's six per-record outputs under data/interim/ and
draws a stratified, blinded sample for human review of the automatic
Included/Excluded decision:

    Included (eligible=True)  <- opinion_main + opinion_limited + opinion_untimed
    Excluded (eligible=False) <- context_only + audit_only + quarantine

For each platform, N_PER_GROUP records are sampled from each of the two
groups (default 20+20=40/platform, i.e. 120 total — above §14's "حداقل ۳۰
رکورد در هر پلتفرم, با پوشش هر دو گروه"), seed=1405 (docs/checklist.md's
project-wide fixed seed, same one build_labeling_sample.py uses).

Two kinds of output are written:

  docs/relevance_audit/relevance_audit_{platform}.csv
      Annotator-facing. Row order shuffled, dataset_target/eligible/
      exclusion-reason columns withheld so annotators judge relevance from
      the text/query alone, not from seeing the system's own decision.
      Blank columns for a human to fill: human_relevance
      (relevant/not_relevant/uncertain) and reviewer_notes.

  data/audits/relevance_audit_answer_key.csv
      sample_id -> dataset_target/eligible/primary_exclusion_reason, all
      platforms. NOT for annotators — used later by
      score_relevance_audit.py (once the annotator-facing CSVs come back
      filled in) to compute Inclusion precision / false-exclusion rate per
      §14, joined back on sample_id.

Usage:
    python src/preprocessing/build_relevance_audit_sample.py
    python src/preprocessing/build_relevance_audit_sample.py --n-per-group 30
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent.parent
INTERIM_DIR = ROOT / "data" / "interim"
OUTPUT_DIR = ROOT / "docs" / "relevance_audit"
ANSWER_KEY_PATH = ROOT / "data" / "audits" / "relevance_audit_answer_key.csv"

RANDOM_SEED = 1405  # docs/checklist.md §17's project-wide fixed seed
DEFAULT_N_PER_GROUP = 20  # 20 Included + 20 Excluded per platform = 40/platform (> §14's min 30, covers both groups)

INCLUDED_TARGETS = ("opinion_main", "opinion_limited", "opinion_untimed")
EXCLUDED_TARGETS = ("context_only", "audit_only", "quarantine")
ALL_TARGETS = INCLUDED_TARGETS + EXCLUDED_TARGETS

LOAD_COLS = [
    "platform", "platform_content_id", "record_uid", "text_raw",
    "query_id", "matched_query_ids", "source_id", "content_type",
    "dataset_target", "primary_exclusion_reason",
]

ANNOTATOR_COLUMNS = [
    "sample_id", "platform", "text_raw", "content_type",
    "query_id", "matched_query_ids", "source_id",
    "human_relevance", "reviewer_notes",
]
ANSWER_KEY_COLUMNS = [
    "sample_id", "platform", "eligible", "dataset_target", "primary_exclusion_reason",
]


def _load_all(interim_dir: Path) -> pd.DataFrame:
    frames = []
    for target in ALL_TARGETS:
        path = interim_dir / f"{target}.parquet"
        if not path.exists():
            raise SystemExit(
                f"missing {path} — run src/preprocessing/apply_eligibility.py first"
            )
        df = pd.read_parquet(path)
        if not len(df):
            continue
        keep = [c for c in LOAD_COLS if c in df.columns]
        frames.append(df[keep])
    if not frames:
        raise SystemExit(f"no rows found across {ALL_TARGETS} under {interim_dir}")
    out = pd.concat(frames, ignore_index=True, sort=False)
    out["eligible"] = out["dataset_target"].isin(INCLUDED_TARGETS)
    return out


def _sample_group(df: pd.DataFrame, n: int, seed: int) -> pd.DataFrame:
    if len(df) <= n:
        return df
    return df.sample(n=n, random_state=seed)


def build_sample(n_per_group: int, seed: int) -> pd.DataFrame:
    all_decided = _load_all(INTERIM_DIR)

    chunks = []
    for platform, plat_df in all_decided.groupby("platform"):
        for eligible_flag in (True, False):
            group = plat_df[plat_df["eligible"] == eligible_flag]
            sampled = _sample_group(group, n_per_group, seed)
            if len(group) < n_per_group:
                print(
                    f"  WARNING: platform={platform} eligible={eligible_flag} "
                    f"only has {len(group)} < requested {n_per_group}; taking all of it"
                )
            chunks.append(sampled)

    sample = pd.concat(chunks, ignore_index=True, sort=False)
    # shuffle row order within the whole sample so Included/Excluded aren't
    # visually grouped in the annotator-facing file (§14: judge from text/query,
    # not from position).
    sample = sample.sample(frac=1.0, random_state=seed).reset_index(drop=True)
    sample.insert(0, "sample_id", [f"RA{seed}-{i:04d}" for i in range(len(sample))])
    return sample


def write_outputs(sample: pd.DataFrame, output_dir: Path, answer_key_path: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    answer_key_path.parent.mkdir(parents=True, exist_ok=True)

    for col in ("human_relevance", "reviewer_notes"):
        if col not in sample.columns:
            sample[col] = ""

    for platform, plat_df in sample.groupby("platform"):
        out_cols = [c for c in ANNOTATOR_COLUMNS if c in plat_df.columns]
        out_path = output_dir / f"relevance_audit_{platform}.csv"
        plat_df[out_cols].to_csv(out_path, index=False, encoding="utf-8-sig")
        print(f"  {platform:10s} {len(plat_df):4d} rows -> {out_path}")

    answer_key_cols = [c for c in ANSWER_KEY_COLUMNS if c in sample.columns]
    sample[answer_key_cols].to_csv(answer_key_path, index=False, encoding="utf-8-sig")
    print(f"  answer key ({len(sample)} rows, NOT for annotators) -> {answer_key_path}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n-per-group", type=int, default=DEFAULT_N_PER_GROUP,
                         help="records sampled per platform per Included/Excluded group (default: 20)")
    parser.add_argument("--seed", type=int, default=RANDOM_SEED)
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    print(f"Sampling {args.n_per_group} Included + {args.n_per_group} Excluded per platform, seed={args.seed}")
    sample = build_sample(n_per_group=args.n_per_group, seed=args.seed)
    print()
    print("Writing outputs:")
    write_outputs(sample, OUTPUT_DIR, ANSWER_KEY_PATH)
