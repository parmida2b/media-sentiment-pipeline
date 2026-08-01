"""
youtube_extract.py — Day 1+ extraction (Parmida)
Pulls comments from news videos about whatever topic is configured in
config/config.yaml, via the official YouTube Data API v3, and writes them
out in the shared Record format defined in config/schema.py.

Source diversity comes from two layers: a categorized channel registry
(config/config.yaml: youtube.channels) covering Iranian/diaspora/US/Arab/
European/international-thinktank outlets, and a regionCode x
relevanceLanguage matrix (config/config.yaml: youtube.regions) applied to
generic search queries — so coverage isn't solely dependent on which
channels we happened to hand-pick.

Because search.list costs 100x more quota than videos.list/commentThreads.list,
and the full channel+region matrix easily exceeds the default 10,000/day
quota, the run is resumable across multiple invocations/days via
checkpoint.py. Each video also gets a one-time LLM geo/perspective tag +
relevance check (geo_tagger.py, cached by video_id) so irrelevant videos
don't waste comment-fetching quota, and results land in
{topic_id}/video_geo_metadata.jsonl without touching config/schema.py.

All output for a given topic lives under data/raw/{CONFIG.topic_id}/ so
switching topics in config.yaml doesn't mix its checkpoint/cache/comments
with a previous topic's run.

Usage:
    python src/ingestion/youtube_extract.py
"""

import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import jdatetime
from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from config.schema import Record, AuthorMetadata
from config import config_loader

import channels
import checkpoint
import geo_tagger

load_dotenv()

API_KEY = os.getenv("YOUTUBE_API_KEY")

CONFIG = config_loader.load_config()

# Analysis window, topic, and search parameters all come from config.yaml —
# see roadmap_pipeline.md's "no topic hardcoded in code" rule.
START_DATE = CONFIG.date_range.start
START_DATE_JALALI = jdatetime.date.fromgregorian(date=START_DATE)
START_DATE_UTC = datetime(START_DATE.year, START_DATE.month, START_DATE.day, tzinfo=timezone.utc)
END_DATE_UTC = CONFIG.date_range.end
PUBLISHED_AFTER_RFC3339 = START_DATE_UTC.strftime("%Y-%m-%dT%H:%M:%SZ")

# Search queries used to discover relevant news videos, combined across
# languages. Tune config.yaml's keywords_* lists once the team agrees on
# which keywords best represent the statistical population (see
# GIT_WORKFLOW.md / project brief on source justification).
SEARCH_QUERIES = [*CONFIG.keywords_en, *CONFIG.keywords_fa, *CONFIG.keywords_ar]

# (regionCode, relevanceLanguage) pairs applied to SEARCH_QUERIES above, so
# result diversity doesn't depend solely on manually curated channels.
REGION_CODES = [tuple(pair) for pair in CONFIG.youtube.get("regions", [])]

# Query used when searching within a specific resolved channel (the
# channelId scope already narrows results, so this stays generic).
CHANNEL_SEARCH_QUERY = CONFIG.youtube.get("channel_search_query", CONFIG.topic)

# Explicit video IDs to always include (e.g. specific news segments the team
# picked by hand), at zero quota cost.
EXPLICIT_VIDEO_IDS = CONFIG.youtube.get("explicit_video_ids", [])

MAX_VIDEOS_PER_QUERY = CONFIG.youtube.get("max_videos_per_query", 5)
MAX_COMMENTS_PER_VIDEO = CONFIG.youtube.get("max_comments_per_video", 300)

# Curated outlet registry — see config.yaml's youtube.channels for what this
# actually contains and why it needs manual attention when the topic changes.
CHANNEL_REGISTRY = CONFIG.youtube.get("channels", {})
CHANNEL_PRIORITY_ORDER = CONFIG.youtube.get("channel_priority_order", list(CHANNEL_REGISTRY.keys()))
# Conservative per-video quota reservation for commentThreads.list pagination
# (up to 3 pages of 100 for MAX_COMMENTS_PER_VIDEO=300) — checked once before
# starting a video's comment fetch rather than interrupted mid-pagination, to
# avoid partial-fetch/duplicate-record complexity across resumed runs.
COMMENT_FETCH_QUOTA_RESERVE = 3 * checkpoint.QUOTA_COSTS["comment_threads"]

# Topic-scoped so rerunning for a different topic (config.yaml: topic_id)
# never mixes checkpoint/cache/comments with a previous topic's data.
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "raw" / CONFIG.topic_id
RESOLVED_CHANNELS_PATH = DATA_DIR / "resolved_channels.json"
# When end="auto" (open-ended, "up to now"), END_DATE_UTC re-resolves to a
# new "now" on every process run, which would otherwise shift this filename
# every calendar day and silently fragment output across many near-empty
# files even though checkpoint.py is designed for one logical job to span
# many runs/days. Use a stable "ongoing" suffix for that case; only bake in
# a literal end date once config.yaml pins one down explicitly.
_end_jalali = jdatetime.date.fromgregorian(date=END_DATE_UTC.date())
if CONFIG.date_range.end_is_auto:
    _end_suffix = "ongoing"
else:
    _end_suffix = _end_jalali.strftime("%Y-%m-%d")
OUTPUT_PATH = DATA_DIR / (
    f"youtube_comments_{START_DATE_JALALI.strftime('%Y-%m-%d')}"
    f"_to_{_end_suffix}.jsonl"
)


def has_persian_only_chars(text: str) -> bool:
    persian_only = set("پچژگی‌ک")
    return any(ch in persian_only for ch in text)


def has_arabic_script(text: str) -> bool:
    return any("؀" <= ch <= "ۿ" for ch in text)


def detect_language(text: str) -> str:
    if not has_arabic_script(text):
        return "en"
    return "fa" if has_persian_only_chars(text) else "ar"


def load_resolved_channels() -> dict[str, str]:
    if not RESOLVED_CHANNELS_PATH.exists():
        return {}
    import json
    with open(RESOLVED_CHANNELS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_resolved_channels(resolved: dict[str, str]) -> None:
    import json
    RESOLVED_CHANNELS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RESOLVED_CHANNELS_PATH, "w", encoding="utf-8") as f:
        json.dump(resolved, f, ensure_ascii=False, indent=2)


def find_channel_id(youtube, name: str, expected_handle: str, state: dict) -> str | None:
    # channels.list's forHandle param resolves a handle directly to its
    # channel (1 unit, exact match) instead of the old search.list + fuzzy
    # customUrl-matching approach (up to 105 units, and prone to missing the
    # channel if it wasn't in the top 5 name-search results).
    try:
        response = youtube.channels().list(part="snippet", forHandle=expected_handle).execute()
    except HttpError as e:
        print(f"[warn] channel lookup failed for {name!r} (@{expected_handle}): {e}")
        if _is_quota_error(e):
            raise  # don't cache a permanent miss for a transient/quota failure
        return None
    checkpoint.spend(state, checkpoint.QUOTA_COSTS["channels_list"])

    items = response.get("items", [])
    if items:
        channel_id = items[0]["id"]
        title = items[0]["snippet"]["title"]
        print(f"  resolved channel {name!r} -> {title!r} ({channel_id})")
        return channel_id
    print(f"[warn] could not confirm official channel for {name!r} (expected handle @{expected_handle})")
    return None


def resolve_all_channels(youtube, state: dict) -> dict[str, str]:
    resolved = load_resolved_channels()
    for category, channel in channels.iter_channels(CHANNEL_REGISTRY, CHANNEL_PRIORITY_ORDER):
        key = f"{category}/{channel['handle']}"
        if key in resolved:
            continue
        if not checkpoint.has_budget(state, checkpoint.QUOTA_COSTS["channels_list"]):
            continue
        try:
            channel_id = find_channel_id(youtube, channel["name"], channel["handle"], state)
        except HttpError:
            print("[quota] real API quota appears exhausted — stopping channel resolution early "
                  "(nothing marked as checked, safe to resume later).")
            break
        checkpoint.save_checkpoint(state, DATA_DIR)
        # Cache the miss too (as None), not just successes — otherwise a
        # channel whose handle never resolves gets retried on every future
        # run forever, burning quota for a lookup that will never succeed.
        resolved[key] = channel_id
        save_resolved_channels(resolved)
    return resolved


def _is_quota_error(e: HttpError) -> bool:
    status = getattr(getattr(e, "resp", None), "status", None)
    return status == 403 and "quota" in str(e).lower()


def search_video_ids(youtube, query: str, max_results: int, state: dict,
                      channel_id: str | None = None, region_code: str | None = None,
                      relevance_language: str | None = None) -> list[str] | None:
    """Returns None (not []) on a failed call, so callers don't permanently
    mark_discovered a combo as "checked, zero results" when we never actually
    got a real answer from the API (e.g. real quota exhausted before our
    local checkpoint's budget tracker caught up)."""
    kwargs = dict(
        q=query, part="id", type="video", order="relevance",
        maxResults=max_results, publishedAfter=PUBLISHED_AFTER_RFC3339,
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


def run_discovery(youtube, state: dict) -> None:
    if EXPLICIT_VIDEO_IDS and "explicit" not in state["discovered"]:
        checkpoint.mark_discovered(state, "explicit", list(EXPLICIT_VIDEO_IDS))
        checkpoint.save_checkpoint(state, DATA_DIR)

    for query in SEARCH_QUERIES:
        for region_code, relevance_language in REGION_CODES:
            combo_key = f"query:{query}|region:{region_code}"
            if combo_key in state["discovered"]:
                continue
            if not checkpoint.has_budget(state, checkpoint.QUOTA_COSTS["search"]):
                print("[quota] search budget exhausted — skipping remaining query x region combos this run.")
                return
            try:
                video_ids = search_video_ids(
                    youtube, query, MAX_VIDEOS_PER_QUERY, state,
                    region_code=region_code, relevance_language=relevance_language,
                )
            except HttpError:
                print("[quota] real API quota appears exhausted — stopping discovery early "
                      "(nothing marked as checked, safe to resume later).")
                return
            if video_ids is None:
                continue  # transient failure — leave uncached so a later run retries it
            checkpoint.mark_discovered(state, combo_key, video_ids)
            checkpoint.save_checkpoint(state, DATA_DIR)
            print(f"  discovered {len(video_ids)} videos for {combo_key}")

    resolved = resolve_all_channels(youtube, state)
    for category, channel in channels.iter_channels(CHANNEL_REGISTRY, CHANNEL_PRIORITY_ORDER):
        reg_key = f"{category}/{channel['handle']}"
        channel_id = resolved.get(reg_key)
        if not channel_id:
            continue
        combo_key = f"channel:{reg_key}"
        if combo_key in state["discovered"]:
            continue
        if not checkpoint.has_budget(state, checkpoint.QUOTA_COSTS["search"]):
            print("[quota] search budget exhausted — skipping remaining channels this run.")
            return
        try:
            video_ids = search_video_ids(youtube, CHANNEL_SEARCH_QUERY, MAX_VIDEOS_PER_QUERY, state, channel_id=channel_id)
        except HttpError:
            print("[quota] real API quota appears exhausted — stopping discovery early "
                  "(nothing marked as checked, safe to resume later).")
            return
        if video_ids is None:
            continue  # transient failure — leave uncached so a later run retries it
        checkpoint.mark_discovered(state, combo_key, video_ids)
        checkpoint.save_checkpoint(state, DATA_DIR)
        print(f"  discovered {len(video_ids)} videos for {combo_key}")


def build_video_channel_hints(state: dict) -> dict[str, dict]:
    """video_id -> {"category", "channel_name", "country"} for videos discovered via a channel-scoped search."""
    hints = {}
    for combo_key, video_ids in state["discovered"].items():
        if not combo_key.startswith("channel:"):
            continue
        category, handle = combo_key[len("channel:"):].split("/", 1)
        channel = next((c for c in CHANNEL_REGISTRY.get(category, []) if c["handle"] == handle), None)
        if not channel:
            continue
        for vid in video_ids:
            hints[vid] = {"category": category, "channel_name": channel["name"], "country": channel["country"]}
    return hints


def get_video_details(youtube, video_ids: list[str], state: dict) -> dict[str, dict]:
    details = {}
    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i:i + 50]
        if not checkpoint.has_budget(state, checkpoint.QUOTA_COSTS["videos_list"]):
            print("[quota] budget exhausted — stopping video-details fetch.")
            break
        try:
            response = youtube.videos().list(part="snippet", id=",".join(chunk)).execute()
        except HttpError as e:
            print(f"[warn] videos.list failed: {e}")
            continue
        checkpoint.spend(state, checkpoint.QUOTA_COSTS["videos_list"])
        for item in response.get("items", []):
            snippet = item["snippet"]
            details[item["id"]] = {
                "title": snippet.get("title", ""),
                "description": snippet.get("description", ""),
            }
    return details


def comment_to_record(comment_snippet: dict, video_id: str, video_title: str,
                       is_reply: bool, reply_count: int = 0) -> Record:
    text = comment_snippet.get("textOriginal", comment_snippet.get("textDisplay", ""))
    return Record(
        text=text,
        date=comment_snippet.get("publishedAt", ""),
        source="youtube",
        platform="youtube",
        author_metadata=AuthorMetadata(
            author_display_name=comment_snippet.get("authorDisplayName"),
            author_channel_id=(comment_snippet.get("authorChannelId") or {}).get("value"),
            like_count=comment_snippet.get("likeCount", 0),
        ),
        language=detect_language(text),
        post_id=video_id,
        post_title=video_title,
        reply_count=reply_count,
        is_reply=is_reply,
    )


def _in_date_range(published_at: str) -> bool:
    ts = datetime.strptime(published_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return START_DATE_UTC <= ts <= END_DATE_UTC


def fetch_comments_for_video(youtube, video_id: str, video_title: str,
                              max_comments: int, state: dict) -> list[Record]:
    """Raises HttpError on a real-quota failure instead of swallowing it, so
    the caller can avoid mark_comments_fetched-ing a video we never actually
    got comments for (that would permanently skip it on future runs)."""
    records: list[Record] = []
    page_token = None
    while len(records) < max_comments:
        try:
            response = youtube.commentThreads().list(
                part="snippet,replies",
                videoId=video_id,
                maxResults=min(100, max_comments - len(records)),
                textFormat="plainText",
                order="time",  # newest first, so we can stop once we age out of the window
                pageToken=page_token,
            ).execute()
        except HttpError as e:
            if _is_quota_error(e):
                raise
            # comments disabled on the video, video not found, etc. — this
            # video genuinely has nothing more to give, safe to mark done.
            print(f"[warn] could not fetch comments for video {video_id}: {e}")
            break
        checkpoint.spend(state, checkpoint.QUOTA_COSTS["comment_threads"])

        hit_older_comment = False
        for item in response.get("items", []):
            top_snippet = item["snippet"]["topLevelComment"]["snippet"]
            if not _in_date_range(top_snippet.get("publishedAt", "")):
                hit_older_comment = True
                continue

            total_replies = item["snippet"].get("totalReplyCount", 0)
            records.append(comment_to_record(
                top_snippet, video_id, video_title,
                is_reply=False, reply_count=total_replies,
            ))

            for reply in item.get("replies", {}).get("comments", []):
                if _in_date_range(reply["snippet"].get("publishedAt", "")):
                    records.append(comment_to_record(
                        reply["snippet"], video_id, video_title,
                        is_reply=True,
                    ))

        if hit_older_comment:
            break  # sorted by time desc — everything after this is even older

        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return records[:max_comments]


def main():
    if not API_KEY:
        print("YOUTUBE_API_KEY is not set in .env — aborting.")
        return

    print(f"Date window: {START_DATE_JALALI.strftime('%Y-%m-%d')} (Jalali) / {START_DATE.isoformat()} "
          f"-> {_end_jalali.strftime('%Y-%m-%d')} (Jalali) / {END_DATE_UTC.date().isoformat()}")
    print(f"Output file: {OUTPUT_PATH.name}\n")

    state = checkpoint.load_checkpoint(DATA_DIR)

    generic_combos = len(SEARCH_QUERIES) * len(REGION_CODES)
    channel_combos = sum(len(v) for v in CHANNEL_REGISTRY.values())
    estimated_quota = (generic_combos + channel_combos) * checkpoint.QUOTA_COSTS["search"]
    runs_needed = -(-estimated_quota // checkpoint.MAX_DAILY_QUOTA)  # ceil div
    print(f"Full discovery needs ~{estimated_quota} quota units "
          f"({generic_combos} query x region + {channel_combos} channel combos, 100 each) "
          f"-> ~{runs_needed} run(s) at the {checkpoint.MAX_DAILY_QUOTA}/day budget.")
    print(f"Quota already used today ({state['quota_date_pt']} PT): {state['quota_used_today']}\n")

    youtube = build("youtube", "v3", developerKey=API_KEY)

    print("Discovery pass (search.list)...")
    run_discovery(youtube, state)

    video_ids = checkpoint.all_discovered_video_ids(state)
    if not video_ids:
        print("No videos discovered yet — check config.yaml's keywords/channels or quota budget.")
        return

    print(f"\n{len(video_ids)} videos discovered so far. Fetching details + geo/relevance tags...")
    details = get_video_details(youtube, video_ids, state)
    channel_hints = build_video_channel_hints(state)
    tagged_cache = geo_tagger.load_tagged_metadata(DATA_DIR)

    all_records: list[Record] = []
    skipped_irrelevant = 0
    for video_id in video_ids:
        if video_id in state["comments_fetched"]:
            continue
        if not checkpoint.has_budget(state, COMMENT_FETCH_QUOTA_RESERVE):
            print("\n[quota] Daily budget reached. Progress saved — re-run later to continue.")
            break

        detail = details.get(video_id, {"title": "", "description": ""})
        tag = geo_tagger.tag_video_cached(
            video_id, detail["title"], detail["description"],
            channel_hints.get(video_id), tagged_cache,
            CONFIG.topic, DATA_DIR,
        )

        if not tag["is_relevant"]:
            print(f"  [skip] {video_id} — {detail['title'][:60]!r} not relevant "
                  f"(perspective={tag['perspective']}, confidence={tag['confidence']:.2f})")
            checkpoint.mark_comments_fetched(state, video_id)
            checkpoint.save_checkpoint(state, DATA_DIR)
            skipped_irrelevant += 1
            continue

        print(f"Fetching comments for {video_id} — {detail['title'][:60]!r} "
              f"(perspective={tag['perspective']}, country={tag['source_country']})")
        try:
            records = fetch_comments_for_video(youtube, video_id, detail["title"], MAX_COMMENTS_PER_VIDEO, state)
        except HttpError:
            print("\n[quota] real API quota appears exhausted — stopping comment fetch early "
                  "(this video not marked done, safe to resume later).")
            break
        print(f"  -> {len(records)} records")
        all_records.extend(records)
        checkpoint.mark_comments_fetched(state, video_id)
        checkpoint.save_checkpoint(state, DATA_DIR)
        time.sleep(0.2)  # be polite to the API

    # Append rather than overwrite: all_records only holds comments fetched in
    # THIS run (checkpoint.comments_fetched makes earlier runs' videos skip the
    # fetch loop above), so "w" here would wipe out every prior run's output
    # each time the script resumes.
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "a", encoding="utf-8") as f:
        for record in all_records:
            f.write(record.to_json_line() + "\n")

    lang_counts = {}
    for r in all_records:
        lang_counts[r.language] = lang_counts.get(r.language, 0) + 1

    print(f"\nWrote {len(all_records)} records to {OUTPUT_PATH} (skipped {skipped_irrelevant} non-relevant videos)")
    print(f"Language breakdown: {lang_counts}")
    print(f"Quota used today: {state['quota_used_today']}/{checkpoint.MAX_DAILY_QUOTA}")
    if runs_needed > 1:
        print("Note: full source coverage spans multiple daily runs — re-run this script on "
              "subsequent days/quota resets to keep discovering and fetching where it left off.")


if __name__ == "__main__":
    main()
