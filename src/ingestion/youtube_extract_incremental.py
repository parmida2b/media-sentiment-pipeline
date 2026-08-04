"""
youtube_extract_incremental.py — v2 YouTube collector (Parmida, Day 3+)

Closes gaps between the v1 collector (youtube_extract.py) and the project
brief's requirements — see docs/decision_log.md for the full rationale:
  - content_id / parent_id (brief section 10 — needed for dedup/uniqueness;
    v1 never captured YouTube's own comment id)
  - author_hash instead of a raw username (sections 3/10/43 — v1 stores
    author_display_name in plain text, which the brief prohibits)
  - collected_at_utc / collection_run_id / query_id (section 10)
  - a real Collection Manifest per run (section 11 — v1's checkpoint.json is
    operational state, not the manifest the brief describes)
  - automation_risk_score (section 16 — absent in v1)
  - per-commenter geo tagging via author_geo.py, matching the brief's
    controlled vocabulary for geo_method/geo_confidence/geo_granularity
    (section 11) instead of stamping the video's inferred origin onto every
    commenter under it

It's also incremental/self-updating: instead of re-scanning the whole
project window every run like v1 does, it tracks a global search watermark
plus a per-video "last comment seen" watermark (incremental_state.py), so a
weekly re-run (scripts/run_youtube_incremental_weekly.ps1) only pulls what's
new — both newly published videos AND new comments on videos already known.

Writes to SEPARATE output (youtube_comments_v2.jsonl,
collection_manifest_v2.jsonl) — v1's already-collected data and its
checkpoint state are never touched. Quota accounting IS shared with v1 via
the same checkpoint.json (see incremental_state.py's docstring for why).

Reuses, unmodified: channels.py, geo_tagger.py, checkpoint.py, and several
pure helpers imported directly from youtube_extract.py (channel resolution,
batch video-details fetch, language detection). Query search and comment
fetch needed their own watermark-aware versions below, since v1's hardcode
the fixed project-start date.

Usage:
    python src/ingestion/youtube_extract_incremental.py
"""

import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from config.schema import Record, AuthorMetadata
from config import query_registry_loader

import author_geo
import author_hash
import automation_risk
import channels
import checkpoint
import geo_tagger
import incremental_state
import youtube_extract as v1

COLLECTOR_VERSION = "youtube_extract_incremental v1.0"

# Re-check the last 2 days on every run (comment moderation/indexing can lag
# a video's publish time) - content_id dedup at write time makes this safe.
OVERLAP_BUFFER_SECONDS = 2 * 24 * 3600

# Conservative reservation for a video's comment pagination (up to 3 pages
# of 100), checked once before starting a video rather than interrupted
# mid-pagination — mirrors v1's COMMENT_FETCH_QUOTA_RESERVE.
COMMENT_FETCH_QUOTA_RESERVE = 3 * checkpoint.QUOTA_COSTS["comment_threads"]

DATA_DIR = v1.DATA_DIR
OUTPUT_PATH = DATA_DIR / "youtube_comments_v2.jsonl"
MANIFEST_PATH = DATA_DIR / "collection_manifest_v2.jsonl"

DEFAULT_WATERMARK_ISO = f"{v1.CONFIG.date_range.start.isoformat()}T00:00:00Z"


def _is_quota_error(e: HttpError) -> bool:
    status = getattr(getattr(e, "resp", None), "status", None)
    return status == 403 and "quota" in str(e).lower()


def _parse_rfc3339(s: str) -> datetime | None:
    try:
        return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def _utc_now_rfc3339() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _current_until_dt() -> datetime:
    # Recomputed per call (not hoisted once) so a long run doesn't exclude
    # comments posted after the script started when date_range.end is
    # "auto" — v1.CONFIG.date_range.end is frozen at import time.
    if v1.CONFIG.date_range.end_is_auto:
        return datetime.now(timezone.utc)
    return v1.CONFIG.date_range.end


def _fallback_queries() -> list[tuple[str, str]]:
    """(query_id, query_text) pairs used only if config/query_registry.yaml
    has no active entries, so this script still runs off config.yaml alone."""
    pairs = []
    for lang, keywords in (("fa", v1.CONFIG.keywords_fa), ("en", v1.CONFIG.keywords_en), ("ar", v1.CONFIG.keywords_ar)):
        for i, kw in enumerate(keywords):
            pairs.append((f"cfg_{lang}_{i}", kw))
    return pairs


def load_existing_content_ids(path: Path) -> set[str]:
    ids: set[str] = set()
    if not path.exists():
        return ids
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            content_id = record.get("content_id")
            if content_id:
                ids.add(content_id)
    return ids


def search_video_ids_since(youtube, query: str, max_results: int, state: dict,
                            published_after_rfc3339: str, channel_id: str | None = None,
                            region_code: str | None = None, relevance_language: str | None = None) -> list[str] | None:
    """Like v1.search_video_ids but with a caller-supplied publishedAfter
    cursor instead of v1's fixed project-start constant, and newest-first
    ordering (so a quota-limited run still prioritizes the newest videos)."""
    kwargs = dict(
        q=query, part="id", type="video", order="date",
        maxResults=max_results, publishedAfter=published_after_rfc3339,
    )
    if channel_id:
        kwargs["channelId"] = channel_id
    if region_code:
        kwargs["regionCode"] = region_code
    if relevance_language:
        kwargs["relevanceLanguage"] = relevance_language

    try:
        response = youtube.search().list(**kwargs).execute()
    except HttpError as e:
        print(f"[warn] search failed for query {query!r}: {e}")
        if _is_quota_error(e):
            raise
        return None
    checkpoint.spend(state, checkpoint.QUOTA_COSTS["search"])
    return [item["id"]["videoId"] for item in response.get("items", [])]


def fetch_comments_for_video_since(youtube, video_id: str, video_title: str, max_comments: int,
                                    state: dict, since_dt: datetime, until_dt: datetime) -> list[dict]:
    """Raw comment dicts (not Record yet — automation_risk needs the whole
    batch first) carrying content_id/parent_id, newer than since_dt. Raises
    HttpError on a real quota failure so the caller can stop cleanly.

    Note (shared limitation with v1): commentThreads.list orders by the
    TOP-LEVEL comment's time, so once a thread older than since_dt is hit,
    its replies are not re-checked even though a reply could technically be
    newer than since_dt — a YouTube API ordering limitation, not something
    this script can work around without a much more expensive full re-scan.
    """
    comments: list[dict] = []
    page_token = None
    while len(comments) < max_comments:
        try:
            response = youtube.commentThreads().list(
                part="snippet,replies",
                videoId=video_id,
                maxResults=min(100, max_comments - len(comments)),
                textFormat="plainText",
                order="time",
                pageToken=page_token,
            ).execute()
        except HttpError as e:
            if _is_quota_error(e):
                raise
            print(f"[warn] could not fetch comments for video {video_id}: {e}")
            break
        checkpoint.spend(state, checkpoint.QUOTA_COSTS["comment_threads"])

        hit_older_comment = False
        for item in response.get("items", []):
            top_comment = item["snippet"]["topLevelComment"]
            top_snippet = top_comment["snippet"]
            top_id = top_comment["id"]
            ts = _parse_rfc3339(top_snippet.get("publishedAt", ""))

            if ts is not None and ts < since_dt:
                hit_older_comment = True
            elif ts is not None and since_dt <= ts <= until_dt:
                comments.append({
                    "content_id": top_id,
                    "parent_id": None,
                    "text": top_snippet.get("textOriginal", top_snippet.get("textDisplay", "")),
                    "date": top_snippet.get("publishedAt", ""),
                    "author_display_name": top_snippet.get("authorDisplayName"),
                    "author_channel_id": (top_snippet.get("authorChannelId") or {}).get("value"),
                    "like_count": top_snippet.get("likeCount", 0),
                    "is_reply": False,
                    "reply_count": item["snippet"].get("totalReplyCount", 0),
                    "video_id": video_id,
                    "video_title": video_title,
                })

            for reply in item.get("replies", {}).get("comments", []):
                r_snippet = reply["snippet"]
                r_ts = _parse_rfc3339(r_snippet.get("publishedAt", ""))
                if r_ts is None or not (since_dt <= r_ts <= until_dt):
                    continue
                comments.append({
                    "content_id": reply["id"],
                    "parent_id": r_snippet.get("parentId") or top_id,
                    "text": r_snippet.get("textOriginal", r_snippet.get("textDisplay", "")),
                    "date": r_snippet.get("publishedAt", ""),
                    "author_display_name": r_snippet.get("authorDisplayName"),
                    "author_channel_id": (r_snippet.get("authorChannelId") or {}).get("value"),
                    "like_count": r_snippet.get("likeCount", 0),
                    "is_reply": True,
                    "reply_count": 0,
                    "video_id": video_id,
                    "video_title": video_title,
                })

        if hit_older_comment:
            break  # order=time desc -> everything after this is even older
        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return comments[:max_comments]


def main():
    if not v1.API_KEY:
        print("YOUTUBE_API_KEY is not set in .env — aborting.")
        return

    collection_run_id = f"v2_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    started_at_utc = _utc_now_rfc3339()
    print(f"[{collection_run_id}] starting incremental YouTube collection")
    print(f"Output: {OUTPUT_PATH.name} | Manifest: {MANIFEST_PATH.name}\n")

    state = incremental_state.load_state(DATA_DIR, DEFAULT_WATERMARK_ISO)
    v2_state = incremental_state.v2(state)
    published_after = v2_state["global_search_watermark"]
    print(f"Search watermark: {published_after} "
          f"(quota used today: {state['quota_used_today']}/{checkpoint.MAX_DAILY_QUOTA})\n")

    active_queries = query_registry_loader.load_active_queries()
    query_pairs = [(q.query_id, q.query_text) for q in active_queries] or _fallback_queries()
    if not active_queries:
        print("[warn] config/query_registry.yaml has no active entries — "
              "falling back to config.yaml's flat keyword lists.\n")

    youtube = build("youtube", "v3", developerKey=v1.API_KEY)

    rate_limit_events = 0
    known_gaps: list[str] = []
    video_query_map: dict[str, str] = {}
    newest_seen_overall: str | None = None
    quota_exhausted = False

    for vid in v1.EXPLICIT_VIDEO_IDS:
        incremental_state.mark_video_known(state, vid)
        video_query_map.setdefault(vid, "explicit")

    print("Discovery pass (query x region)...")
    for query_id, query_text in query_pairs:
        if quota_exhausted:
            break
        for region_code, relevance_language in v1.REGION_CODES:
            if not checkpoint.has_budget(state, checkpoint.QUOTA_COSTS["search"]):
                known_gaps.append("Search budget exhausted before all query x region combos were checked this run.")
                quota_exhausted = True
                break
            combo_key = f"query:{query_id}|region:{region_code}"
            try:
                video_ids = search_video_ids_since(
                    youtube, query_text, v1.MAX_VIDEOS_PER_QUERY, state,
                    published_after, region_code=region_code, relevance_language=relevance_language,
                )
            except HttpError:
                rate_limit_events += 1
                known_gaps.append("Real API quota appears exhausted during query discovery — stopped early, safe to resume next run.")
                quota_exhausted = True
                break
            if video_ids is None:
                continue
            for vid in video_ids:
                incremental_state.mark_video_known(state, vid)
                video_query_map.setdefault(vid, combo_key)
            if video_ids:
                print(f"  {combo_key}: {len(video_ids)} video(s)")
            incremental_state.save_state(state, DATA_DIR)

    if not quota_exhausted:
        print("\nResolving/searching curated channels...")
        resolved = v1.resolve_all_channels(youtube, state)
        for category, channel in channels.iter_channels(v1.CHANNEL_REGISTRY, v1.CHANNEL_PRIORITY_ORDER):
            if quota_exhausted:
                break
            reg_key = f"{category}/{channel['handle']}"
            channel_id = resolved.get(reg_key)
            if not channel_id:
                continue
            if not checkpoint.has_budget(state, checkpoint.QUOTA_COSTS["search"]):
                known_gaps.append("Search budget exhausted before all curated channels were checked this run.")
                quota_exhausted = True
                break
            combo_key = f"channel:{reg_key}"
            try:
                video_ids = search_video_ids_since(
                    youtube, v1.CHANNEL_SEARCH_QUERY, v1.MAX_VIDEOS_PER_QUERY, state,
                    published_after, channel_id=channel_id,
                )
            except HttpError:
                rate_limit_events += 1
                known_gaps.append("Real API quota appears exhausted during channel discovery — stopped early, safe to resume next run.")
                quota_exhausted = True
                break
            if video_ids is None:
                continue
            for vid in video_ids:
                incremental_state.mark_video_known(state, vid)
                video_query_map.setdefault(vid, combo_key)
            if video_ids:
                print(f"  {combo_key}: {len(video_ids)} video(s)")
            incremental_state.save_state(state, DATA_DIR)

    known_video_ids = list(v2_state["known_video_ids"])
    print(f"\n{len(known_video_ids)} known video(s) total. Fetching details + geo/relevance tags...")

    details = v1.get_video_details(youtube, known_video_ids, state)
    tagged_cache = geo_tagger.load_tagged_metadata(DATA_DIR)

    existing_content_ids = load_existing_content_ids(OUTPUT_PATH)
    written_this_run: set[str] = set()
    new_records: list[Record] = []
    skipped_irrelevant = 0
    collected_at = _utc_now_rfc3339()

    print("\nChecking known videos for new comments...")
    for i, video_id in enumerate(known_video_ids, 1):
        if not checkpoint.has_budget(state, COMMENT_FETCH_QUOTA_RESERVE):
            known_gaps.append(f"Comment-fetch budget exhausted after {i - 1}/{len(known_video_ids)} known videos this run.")
            break

        detail = details.get(video_id, {"title": "", "description": ""})
        combo = video_query_map.get(video_id, "")
        channel_hint = None
        if combo.startswith("channel:"):
            _, reg_key = combo.split(":", 1)
            category, handle = reg_key.split("/", 1)
            ch = next((c for c in v1.CHANNEL_REGISTRY.get(category, []) if c["handle"] == handle), None)
            if ch:
                channel_hint = {"category": category, "channel_name": ch["name"], "country": ch["country"]}

        tag = geo_tagger.tag_video_cached(
            video_id, detail["title"], detail["description"], channel_hint,
            tagged_cache, v1.CONFIG.topic, DATA_DIR,
        )
        if not tag["is_relevant"]:
            skipped_irrelevant += 1
            continue

        since_iso = incremental_state.get_video_watermark(state, video_id, DEFAULT_WATERMARK_ISO)
        since_dt = _parse_rfc3339(since_iso)
        until_dt = _current_until_dt()

        try:
            video_comments = fetch_comments_for_video_since(
                youtube, video_id, detail["title"], v1.MAX_COMMENTS_PER_VIDEO, state, since_dt, until_dt,
            )
        except HttpError:
            rate_limit_events += 1
            known_gaps.append(
                f"Real API quota appears exhausted while fetching comments "
                f"({i - 1}/{len(known_video_ids)} known videos processed) — stopped early, safe to resume next run."
            )
            break

        if not video_comments:
            continue

        risk_scores = automation_risk.score_batch(video_comments)

        video_new_count = 0
        for c in video_comments:
            content_id = c["content_id"]
            if content_id in existing_content_ids or content_id in written_this_run:
                continue
            written_this_run.add(content_id)
            video_new_count += 1

            detected_language = v1.detect_language(c["text"])
            geo = author_geo.tag_geo(c["text"], channel_hint, detected_language)

            new_records.append(Record(
                text=c["text"],
                date=c["date"],
                source="youtube",
                platform="youtube",
                author_metadata=AuthorMetadata(
                    author_channel_id=c["author_channel_id"],
                    like_count=c["like_count"],
                    author_hash=author_hash.hash_author(c["author_channel_id"], c["author_display_name"]),
                ),
                language=detected_language,
                post_id=video_id,
                post_title=detail["title"],
                reply_count=c["reply_count"],
                is_reply=c["is_reply"],
                content_id=content_id,
                parent_id=c["parent_id"],
                collected_at_utc=collected_at,
                collection_run_id=collection_run_id,
                query_id=video_query_map.get(video_id, "unknown"),
                geo_method=geo["geo_method"],
                geo_confidence=geo["geo_confidence"],
                geo_granularity=geo["geo_granularity"],
                country_or_region=geo["country_or_region"],
                geo_limitations=geo["geo_limitations"],
                automation_risk_score=risk_scores.get(content_id),
            ))

        if video_new_count:
            newest_for_video = max(c["date"] for c in video_comments)
            incremental_state.update_video_watermark(state, video_id, newest_for_video)
            if newest_seen_overall is None or newest_for_video > newest_seen_overall:
                newest_seen_overall = newest_for_video
            print(f"  [{i}/{len(known_video_ids)}] {video_id} — {detail['title'][:50]!r}: {video_new_count} new comment(s)")

        incremental_state.save_state(state, DATA_DIR)
        time.sleep(0.2)  # be polite to the API

    if skipped_irrelevant:
        known_gaps.append(f"{skipped_irrelevant} video(s) skipped as not relevant per geo_tagger's relevance tag.")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "a", encoding="utf-8") as f:
        for record in new_records:
            f.write(record.to_json_line() + "\n")

    if newest_seen_overall:
        incremental_state.update_global_search_watermark(state, newest_seen_overall, OVERLAP_BUFFER_SECONDS)

    finished_at_utc = _utc_now_rfc3339()
    incremental_state.record_run(state, collection_run_id, len(new_records))
    incremental_state.save_state(state, DATA_DIR)

    manifest_entry = {
        "collection_run_id": collection_run_id,
        "platform": "youtube",
        "query_version": query_registry_loader.get_registry_version() if active_queries else "config.yaml-fallback",
        "started_at_utc": started_at_utc,
        "finished_at_utc": finished_at_utc,
        "requested_window": {
            "start": v1.CONFIG.date_range.start.isoformat(),
            "end": "auto" if v1.CONFIG.date_range.end_is_auto else v1.CONFIG.date_range.end.date().isoformat(),
        },
        "observed_window": {
            "search_watermark_used": published_after,
            "newest_comment_seen": newest_seen_overall,
        },
        "records_received": len(new_records),
        "rate_limit_events": rate_limit_events,
        "known_gaps": known_gaps,
        "collector_version": COLLECTOR_VERSION,
        "terms_basis": "YouTube Data API v3, official developer key (YOUTUBE_API_KEY env var), within documented daily quota budget (checkpoint.py).",
    }
    with open(MANIFEST_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(manifest_entry, ensure_ascii=False) + "\n")

    print(f"\nWrote {len(new_records)} new record(s) to {OUTPUT_PATH.name}")
    print(f"Manifest entry appended to {MANIFEST_PATH.name}")
    print(f"Quota used today: {state['quota_used_today']}/{checkpoint.MAX_DAILY_QUOTA}")
    if known_gaps:
        print("Known gaps this run:")
        for gap in known_gaps:
            print(f"  - {gap}")


if __name__ == "__main__":
    main()
