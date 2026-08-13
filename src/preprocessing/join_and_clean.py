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
  data/raw/reddit/reddit_comments_*.jsonl        (Day 5, Parmida - written by
      src/ingestion/reddit_to_record.py, same Record shape. NOT topic_id-
      scoped like YouTube's path - Reddit's existing collector scripts
      (reddit_parent_post_collector.py / reddit_raw_json_pipeline.py) already
      use a fixed data/raw/reddit/ path, so this reads from there rather than
      retrofitting topic-scoping onto them. video_geo_metadata.jsonl has no
      Reddit equivalent yet (see reddit_to_record.py's module docstring for
      why) - Reddit records simply never match the geo lookup below, same as
      any YouTube record for an untagged video.
  data/raw/x/x_comments_*.jsonl                  (Day 5, Parmida - written by
      src/ingestion/x_to_record.py, same Record shape, same fixed non-
      topic_id-scoped path pattern as Reddit above (x_scraper.py already
      uses its own fixed output root, see x_to_record.py's module
      docstring). X has no video_geo_metadata.jsonl either yet - Tier-0 geo
      tagging was never wired in for X (same "not done yet" reasoning as
      automation_risk_score - see x_to_record.py's docstring), so X records
      simply never match the geo lookup below, same as Reddit/untagged
      YouTube.

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
from src.common.jsonl_io import read_jsonl_file as _load_jsonl  # noqa: E402


def _load_all_comments(raw_dir: Path) -> tuple[list[dict], dict[str, int]]:
    """Returns (records, counts_by_platform). raw_dir is the topic-scoped
    YouTube dir; Reddit and X are each read from their own fixed
    data/raw/{reddit,x}/ dir (see module docstring) regardless of topic_id."""
    counts: dict[str, int] = {}

    youtube_records: list[dict] = []
    for path in sorted(raw_dir.glob("youtube_comments_*.jsonl")):
        youtube_records.extend(_load_jsonl(path))
    counts["youtube"] = len(youtube_records)

    reddit_dir = raw_dir.parent / "reddit"
    reddit_records: list[dict] = []
    for path in sorted(reddit_dir.glob("reddit_comments_*.jsonl")):
        reddit_records.extend(_load_jsonl(path))
    counts["reddit"] = len(reddit_records)

    x_dir = raw_dir.parent / "x"
    x_records: list[dict] = []
    for path in sorted(x_dir.glob("x_comments_*.jsonl")):
        x_records.extend(_load_jsonl(path))
    counts["x"] = len(x_records)

    return youtube_records + reddit_records + x_records, counts


def _load_geo_lookup(raw_dir: Path) -> dict[str, dict]:
    """Both YouTube's and Reddit's video_geo_metadata.jsonl are written by
    the same geo_tagger.tag_video_cached() (see reddit_to_record.py) and use
    the same {"video_id": <id>, ...} shape, so they merge into one lookup
    dict keyed by id (video_id for YouTube, post_id for Reddit - the field
    is still literally called "video_id" in the cache record, a naming
    leak from geo_tagger.py being YouTube-first, not a bug)."""
    lookup: dict[str, dict] = {}
    for geo_path in (
        raw_dir / "video_geo_metadata.jsonl",
        raw_dir.parent / "reddit" / "video_geo_metadata.jsonl",
    ):
        if not geo_path.exists():
            continue
        lookup.update(
            {row["video_id"]: row for row in _load_jsonl(geo_path) if row.get("video_id")}
        )
    return lookup


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

    comments, platform_counts = _load_all_comments(raw_dir)
    if not comments:
        raise SystemExit(
            f"no youtube_comments_*.jsonl found under {raw_dir}, no "
            f"reddit_comments_*.jsonl found under {raw_dir.parent / 'reddit'}, "
            f"and no x_comments_*.jsonl found under {raw_dir.parent / 'x'}"
        )
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
    _write_cleaning_report(report_path, comments, user_rows, raw_dir, platform_counts)
    print(f"wrote {len(comments)} records -> {out_path} ({platform_counts})")
    print(f"wrote report -> {report_path}")


def _write_cleaning_report(
    path: Path, comments: list[dict], user_rows: list[dict], raw_dir: Path,
    platform_counts: dict[str, int],
) -> None:
    flagged = sorted(
        (r for r in user_rows if r["is_flagged_bot_suspect"]),
        key=lambda r: r["automation_risk_score_user"],
        reverse=True,
    )
    pct_flagged = (len(flagged) / len(user_rows) * 100) if user_rows else 0.0

    lines = [
        "# Cleaning report — cross-platform bot-detection pass",
        "",
        f"- Sources: `{raw_dir}` (YouTube), `{raw_dir.parent / 'reddit'}` (Reddit), "
        f"`{raw_dir.parent / 'x'}` (X)",
        f"- Records by platform: {platform_counts}",
        f"- Total comment/reply records: {len(comments)}",
        f"- Distinct users seen: {len(user_rows)} (per-platform - a real "
        "person active on both YouTube and Reddit has two separate "
        "user_keys here, one per platform's own author_hash; see "
        "cross_platform_alignment_guide_fa.md §5 checklist item 4, "
        "cross-platform identity linkage is explicitly not attempted)",
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
