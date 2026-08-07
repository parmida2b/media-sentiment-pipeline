"""
join_and_clean.py — preprocessing entry point for YouTube data (Parmida).

Per docs/project_brief_for_llm.md's remaining-work list and the pipeline
placement decision in docs/cross_platform_alignment_guide_fa.md §4: this is
where "Tier B" (per-user, cross-video bot scoring, user_features.py) runs,
after extraction (data_collection stage) is done for whatever's been
collected so far — it needs every video's comments loaded together, which
Tier A (inside youtube_extract.py, one video at a time) can't see.

Scope of THIS version: only the bot-detection wiring described in that doc.
Full-text dedup, language detection, and text normalization are still open
items on docs/project_brief_for_llm.md's roadmap - intentionally left for a
separate change so this one stays reviewable.

Input:
  data/raw/{topic_id}/youtube_comments_*.jsonl   (one or more files/weeks)
  data/raw/{topic_id}/video_geo_metadata.jsonl   (optional, joined in when present)

Output:
  data/interim/clean.jsonl          - every input record, unchanged, plus
                                       automation_risk_score_user,
                                       is_flagged_bot_suspect, and joined
                                       video_geo (when available). Nothing
                                       is dropped.
  outputs/audits/cleaning_report.md - human-readable summary for the team

Filtering/exclusion based on automation_risk_score_user is a separate,
team-reviewed decision (raw_schema_v03.md §12.3's Eligibility-Filter rule
applies here too, not just inside the Collector) - not done by this script.

Usage:
    python src/preprocessing/join_and_clean.py
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from config.config_loader import load_config  # noqa: E402

from user_features import FLAG_THRESHOLD, build_user_table, score_users  # noqa: E402


def _load_jsonl(path: Path) -> list[dict]:
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def _load_all_comments(raw_dir: Path) -> list[dict]:
    records = []
    for path in sorted(raw_dir.glob("youtube_comments_*.jsonl")):
        records.extend(_load_jsonl(path))
    return records


def _load_geo_lookup(raw_dir: Path) -> dict[str, dict]:
    geo_path = raw_dir / "video_geo_metadata.jsonl"
    if not geo_path.exists():
        return {}
    return {row["video_id"]: row for row in _load_jsonl(geo_path) if row.get("video_id")}


def _user_key(record: dict) -> str | None:
    meta = record.get("author_metadata") or {}
    return meta.get("author_hash") or meta.get("author_channel_id")


def run(topic_id: str | None = None) -> None:
    cfg = load_config()
    topic_id = topic_id or cfg.topic_id
    raw_dir = ROOT / "data" / "raw" / topic_id
    interim_dir = ROOT / "data" / "interim"
    audits_dir = ROOT / "outputs" / "audits"
    interim_dir.mkdir(parents=True, exist_ok=True)
    audits_dir.mkdir(parents=True, exist_ok=True)

    comments = _load_all_comments(raw_dir)
    if not comments:
        raise SystemExit(f"no youtube_comments_*.jsonl files found under {raw_dir}")
    geo_lookup = _load_geo_lookup(raw_dir)

    user_rows = score_users(build_user_table(comments))
    user_by_key = {row["user_key"]: row for row in user_rows}

    out_path = interim_dir / "clean.jsonl"
    with open(out_path, "w", encoding="utf-8") as out:
        for record in comments:
            user_row = user_by_key.get(_user_key(record))
            record["automation_risk_score_user"] = (
                user_row["automation_risk_score_user"] if user_row else None
            )
            record["is_flagged_bot_suspect"] = bool(user_row and user_row["is_flagged_bot_suspect"])
            geo = geo_lookup.get(record.get("post_id"))
            if geo:
                record.setdefault("video_geo", geo)
            out.write(json.dumps(record, ensure_ascii=False) + "\n")

    report_path = audits_dir / "cleaning_report.md"
    _write_cleaning_report(report_path, comments, user_rows, raw_dir)
    print(f"wrote {len(comments)} records -> {out_path}")
    print(f"wrote report -> {report_path}")


def _write_cleaning_report(path: Path, comments: list[dict], user_rows: list[dict], raw_dir: Path) -> None:
    flagged = sorted(
        (r for r in user_rows if r["is_flagged_bot_suspect"]),
        key=lambda r: r["automation_risk_score_user"],
        reverse=True,
    )
    pct_flagged = (len(flagged) / len(user_rows) * 100) if user_rows else 0.0

    lines = [
        "# Cleaning report — YouTube bot-detection pass",
        "",
        f"- Source: `{raw_dir}`",
        f"- Total comment/reply records: {len(comments)}",
        f"- Distinct users seen: {len(user_rows)}",
        f"- Users flagged (`automation_risk_score_user >= {FLAG_THRESHOLD}`): "
        f"{len(flagged)} ({pct_flagged:.1f}% of users)",
        "",
        "> `automation_risk_score_user` is a heuristic risk score in [0,1], "
        "**not a bot verdict** — see `docs/cross_platform_alignment_guide_fa.md` "
        "§4. Nothing was removed from `clean.jsonl`; this flag is for manual "
        "review / a later, team-reviewed eligibility decision.",
        "",
        "## Top 20 highest-risk users (manual spot-check candidates)",
        "",
        "| user_key | score | total_interactions | exact_duplicate_ratio | "
        "url_interaction_ratio | hour_coverage_ratio |",
        "|---|---|---|---|---|---|",
    ]
    for row in flagged[:20]:
        lines.append(
            f"| `{row['user_key'][:24]}` | {row['automation_risk_score_user']} | "
            f"{row['total_interactions']} | {row['exact_duplicate_ratio']} | "
            f"{row['url_interaction_ratio']} | {row['hour_coverage_ratio']} |"
        )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    run()
