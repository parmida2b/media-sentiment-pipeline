"""
geo_tagger.py — per-video geo/perspective LLM tagging + relevance filter (Parmida)

Runs once per video (never per comment) via Groq, the same provider
already wired up in src/annotation/compare_llm_sentiment.py. Output is appended to {data_dir}/video_geo_metadata.jsonl and
cached by video_id so a video with hundreds of comments only ever costs one
LLM call, across process restarts. `data_dir` is topic-scoped (see
config/config_loader.py) so switching topics doesn't reuse another topic's
cached relevance tags.

Deliberately does not touch config/schema.py (team convention: Parmida
maintains that file) — this metadata lives in its own side file and
gets joined by video_id/post_id at analysis time.

Multi-key support (2026-08-12): set GROQ_API_KEYS (comma-separated) instead
of a single GROQ_API_KEY to pool several accounts' free-tier daily quota -
each teammate's own Groq key, not throwaway/duplicate accounts (see that
constraint in Groq's ToS). A key that hits its daily RPD/TPD cap is skipped
for the rest of the process; GroqQuotaExceeded only propagates once every
configured key is exhausted. See _load_groq_keys()/_available_groq_clients().
"""

import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# llama-3.1-8b-instant instead of llama-3.3-70b-versatile: same provider/key,
# but Groq's free tier grants the small/fast model a much higher daily
# request quota than the 70b model, which is what was running out mid-run.
# Structured 4-field classification (country/perspective/relevance) doesn't
# need the bigger model's reasoning headroom.
GROQ_MODEL_NAME = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

MAX_RETRIES = 3
BACKOFF_BASE_SECONDS = 2.0

VALID_PERSPECTIVES = {"state_media", "western", "independent", "diaspora", "other"}


class GroqQuotaExceeded(RuntimeError):
    """Raised when Groq reports the *daily* quota (RPD/TPD) is exhausted —
    as opposed to a transient per-minute rate limit. Retrying won't help
    until the provider's daily reset, so the caller should stop the run
    cleanly (geo_tagger's cache lets a later run pick up where this one
    left off) instead of grinding through every remaining video with
    failed calls."""


PROMPT_TEMPLATE = """You are tagging a YouTube news video for a research pipeline studying \
media coverage of: {topic}.

Video title: \"\"\"{title}\"\"\"
Video description (may be truncated): \"\"\"{description}\"\"\"{hint}

Respond with ONLY a JSON object, no other text:
{{
  "origin_country": "<ISO 3166-1 alpha-2 country code of the source, or \\"unknown\\">",
  "perspective": "<one of: state_media, western, independent, diaspora, other>",
  "is_relevant": <true if this video is actually about {topic}, else false>,
  "confidence": <float 0.0-1.0>
}}
"""

_groq_keys: list[str] | None = None  # lazy-loaded (None = not loaded yet), see _load_groq_keys
_groq_clients: dict[str, "Groq"] = {}  # one cached client per key, built lazily on first use
_exhausted_keys: set[str] = set()  # keys that hit their *daily* quota this run - see GroqQuotaExceeded


def _load_groq_keys() -> list[str]:
    """Multi-key support (2026-08-12): GROQ_API_KEYS (comma-separated) lets
    several Groq accounts' free-tier daily quotas be pooled, since a single
    key's RPD/TPD cap was the thing stopping full runs (see decision_log.md
    2026-08-08). Falls back to the single GROQ_API_KEY for anyone who hasn't
    switched over - existing .env files keep working unchanged."""
    multi = os.getenv("GROQ_API_KEYS")
    if multi:
        keys = [k.strip() for k in multi.split(",") if k.strip()]
        if keys:
            return keys
    single = os.getenv("GROQ_API_KEY")
    return [single] if single else []


def _available_groq_clients():
    """Yields (key, client) for every configured key not yet marked
    exhausted *this run* (_exhausted_keys resets only on process restart -
    a key that hit its daily cap won't un-exhaust itself until Groq's own
    daily reset anyway, so there's no point retrying it mid-run). Each
    client is built once and cached, however many videos/posts get tagged."""
    global _groq_keys
    if _groq_keys is None:
        _groq_keys = _load_groq_keys()

    if not _groq_keys:
        return

    from groq import Groq
    for key in _groq_keys:
        if key in _exhausted_keys:
            continue
        if key not in _groq_clients:
            _groq_clients[key] = Groq(api_key=key)
        yield key, _groq_clients[key]


def _is_daily_quota_message(message: str) -> bool:
    # Groq's 429 body text says e.g. "...on requests per day (RPD): Limit
    # 14400, Used 14400..." for a daily cap, vs "...on tokens per minute
    # (TPM)..." for a transient one. No day/date is ever coming back sooner
    # by retrying, so treat "per day"/RPD/TPD mentions as non-retryable.
    text = (message or "").lower()
    return "per day" in text or "rpd" in text or "tpd" in text


def _retry_after_seconds(exc) -> float | None:
    response = getattr(exc, "response", None)
    header = response.headers.get("retry-after") if response is not None else None
    if header is None:
        return None
    try:
        return float(header)
    except (TypeError, ValueError):
        return None


def _call_groq_with_retry(client, prompt: str):
    """Calls the Groq chat completion endpoint, retrying transient errors
    (per-minute rate limits, connection hiccups, 5xx) with backoff. Raises
    GroqQuotaExceeded immediately -- no retry -- when Groq reports the
    *daily* quota is exhausted, since waiting a few seconds won't fix that."""
    from groq import APIConnectionError, InternalServerError, RateLimitError

    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            return client.chat.completions.create(
                model=GROQ_MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
            )
        except RateLimitError as e:
            message = str(getattr(e, "message", None) or e)
            if _is_daily_quota_message(message):
                raise GroqQuotaExceeded(message) from e
            last_error = e
            if attempt < MAX_RETRIES - 1:
                wait_s = _retry_after_seconds(e) or (BACKOFF_BASE_SECONDS * (2 ** attempt))
                print(f"[warn] geo_tagger: Groq rate limit (attempt {attempt + 1}/{MAX_RETRIES}), "
                      f"retrying in {wait_s:.1f}s: {message}")
                time.sleep(wait_s)
        except (APIConnectionError, InternalServerError) as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                wait_s = BACKOFF_BASE_SECONDS * (2 ** attempt)
                print(f"[warn] geo_tagger: transient Groq error (attempt {attempt + 1}/{MAX_RETRIES}), "
                      f"retrying in {wait_s:.1f}s: {e}")
                time.sleep(wait_s)

    raise last_error


def _parse_llm_json(raw_text: str) -> dict:
    raw_text = raw_text.strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        raw_text = raw_text.replace("json\n", "", 1)
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        return {}


def _detect_text_language(text: str) -> str:
    # Same lightweight heuristic as youtube_extract.detect_language, kept
    # local to avoid a circular import (youtube_extract imports this module).
    persian_only = set("پچژگی‌ک")
    has_persian = any(ch in persian_only for ch in text)
    has_arabic_script = any("؀" <= ch <= "ۿ" for ch in text)
    if not has_arabic_script:
        return "en"
    return "fa" if has_persian else "ar"


def _metadata_path(data_dir: Path) -> Path:
    return data_dir / "video_geo_metadata.jsonl"


def load_tagged_metadata(data_dir: Path) -> dict[str, dict]:
    """video_id -> cached metadata record, loaded from the jsonl file."""
    cache: dict[str, dict] = {}
    metadata_path = _metadata_path(data_dir)
    if not metadata_path.exists():
        return cache
    with open(metadata_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            vid = record.get("video_id")
            if vid:
                cache[vid] = record
    return cache


def _append_metadata_record(record: dict, data_dir: Path) -> None:
    metadata_path = _metadata_path(data_dir)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    with open(metadata_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _call_llm(title: str, description: str, channel_hint: dict | None, topic: str) -> dict:
    clients = list(_available_groq_clients())
    if not clients:
        # No key configured at all, or every configured key already hit its
        # daily quota this run — fail open (treat as relevant, low
        # confidence) rather than silently dropping videos/posts.
        return {
            "origin_country": (channel_hint or {}).get("country", "unknown"),
            "perspective": "other",
            "is_relevant": True,
            "confidence": 0.0,
        }

    hint = ""
    if channel_hint:
        hint = (
            f"\nKnown source channel: {channel_hint['channel_name']} "
            f"(category: {channel_hint['category']}, country: {channel_hint['country']}). "
            "Use this as a strong prior, but still judge relevance/perspective from the content."
        )

    prompt = PROMPT_TEMPLATE.format(
        title=title, description=(description or "")[:500], hint=hint, topic=topic,
    )

    # Multi-key rotation (2026-08-12): try each configured key in turn;
    # a key hitting its *daily* quota just gets skipped for the rest of
    # this process, not treated as a hard stop, as long as another
    # configured key still has headroom. Only once every key is exhausted
    # does this propagate GroqQuotaExceeded - same external contract as
    # before, so callers (youtube_extract.py, reddit_to_record.py) don't
    # need to change: they already stop cleanly on that exception.
    result: dict = {}
    quota_error: GroqQuotaExceeded | None = None
    for key, client in clients:
        try:
            response = _call_groq_with_retry(client, prompt)
            result = _parse_llm_json(response.choices[0].message.content)
            quota_error = None
            break
        except GroqQuotaExceeded as e:
            _exhausted_keys.add(key)
            remaining = len(_groq_keys) - len(_exhausted_keys)
            print(
                f"[warn] geo_tagger: Groq key ...{key[-4:]} hit its daily quota - "
                f"rotating to next key ({remaining} key(s) with headroom left)."
            )
            quota_error = e
            continue
        except Exception as e:
            # Anything else (bad request for this one video, retries exhausted
            # on a transient error, ...) — fail open for just this video
            # rather than burning through every remaining key over it.
            print(f"[warn] geo_tagger LLM call failed after retries: {e}")
            result = {}
            quota_error = None
            break

    if quota_error is not None:
        # Every configured key is exhausted - not retryable within this run,
        # let it propagate so the caller stops cleanly (cache already has
        # everything tagged so far; safe to resume after Groq's daily reset,
        # or once a fresh key is added to GROQ_API_KEYS).
        raise GroqQuotaExceeded(
            f"All {len(_groq_keys)} configured Groq key(s) exhausted their daily quota."
        ) from quota_error

    perspective = result.get("perspective")
    if perspective not in VALID_PERSPECTIVES:
        perspective = "other"

    confidence = result.get("confidence", 0.0)
    if not isinstance(confidence, (int, float)):
        confidence = 0.0

    return {
        "origin_country": result.get("origin_country") or (channel_hint or {}).get("country", "unknown"),
        "perspective": perspective,
        "is_relevant": bool(result.get("is_relevant", True)),
        "confidence": float(confidence),
    }


def tag_video_cached(video_id: str, title: str, description: str,
                      channel_hint: dict | None, cache: dict[str, dict],
                      topic: str, data_dir: Path) -> dict:
    """
    Returns the metadata record for this video_id, using `cache` (as
    produced by load_tagged_metadata) to skip the LLM call entirely for
    videos already tagged in a prior run. `topic` is what the LLM judges
    relevance against; `data_dir` is the topic-scoped dir the record is
    appended to.
    """
    if video_id in cache:
        return cache[video_id]

    llm_result = _call_llm(title, description, channel_hint, topic)

    record = {
        "video_id": video_id,
        "source_channel": (channel_hint or {}).get("channel_name"),
        "source_country": (channel_hint or {}).get("country") or llm_result["origin_country"],
        "region": (channel_hint or {}).get("category"),
        "perspective": llm_result["perspective"],
        "language": _detect_text_language(f"{title} {description or ''}"),
        "is_relevant": llm_result["is_relevant"],
        "confidence": llm_result["confidence"],
    }

    _append_metadata_record(record, data_dir)
    cache[video_id] = record
    return record
