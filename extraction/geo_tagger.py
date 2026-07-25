"""
geo_tagger.py — per-video geo/perspective LLM tagging + relevance filter (Parmida)

Runs once per video (never per comment) via Groq, the same provider
already wired up in sentiment/compare_llm_sentiment.py (no GEMINI_API_KEY
is configured for this project, so Groq is the only LLM actually
available). Output is appended
to data/raw/video_geo_metadata.jsonl and cached by video_id so a video with
hundreds of comments only ever costs one LLM call, across process restarts.

Deliberately does not touch config/schema.py (team convention: only
Hossein edits that file) — this metadata lives in its own side file and
gets joined by video_id/post_id at analysis time.
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
METADATA_PATH = ROOT / "data" / "raw" / "video_geo_metadata.jsonl"

GROQ_MODEL_NAME = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

VALID_PERSPECTIVES = {"state_media", "western", "independent", "diaspora", "other"}

PROMPT_TEMPLATE = """You are tagging a YouTube news video for a research pipeline studying \
media coverage of the Iran-US conflict.

Video title: \"\"\"{title}\"\"\"
Video description (may be truncated): \"\"\"{description}\"\"\"{hint}

Respond with ONLY a JSON object, no other text:
{{
  "origin_country": "<ISO 3166-1 alpha-2 country code of the source, or \\"unknown\\">",
  "perspective": "<one of: state_media, western, independent, diaspora, other>",
  "is_relevant": <true if this video is actually about the Iran-US conflict, else false>,
  "confidence": <float 0.0-1.0>
}}
"""

_groq_client = None
_groq_unavailable = False


def _get_groq_client():
    global _groq_client, _groq_unavailable
    if _groq_client is not None or _groq_unavailable:
        return _groq_client

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        _groq_unavailable = True
        return None

    from groq import Groq
    _groq_client = Groq(api_key=api_key)
    return _groq_client


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


def load_tagged_metadata() -> dict[str, dict]:
    """video_id -> cached metadata record, loaded from the jsonl file."""
    cache: dict[str, dict] = {}
    if not METADATA_PATH.exists():
        return cache
    with open(METADATA_PATH, "r", encoding="utf-8") as f:
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


def _append_metadata_record(record: dict) -> None:
    METADATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(METADATA_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _call_llm(title: str, description: str, channel_hint: dict | None) -> dict:
    client = _get_groq_client()
    if client is None:
        # No GROQ_API_KEY configured — fail open (treat as relevant, low
        # confidence) rather than silently dropping videos.
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
        title=title, description=(description or "")[:500], hint=hint,
    )

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        result = _parse_llm_json(response.choices[0].message.content)
    except Exception as e:
        print(f"[warn] geo_tagger LLM call failed: {e}")
        result = {}

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
                      channel_hint: dict | None, cache: dict[str, dict]) -> dict:
    """
    Returns the metadata record for this video_id, using `cache` (as
    produced by load_tagged_metadata) to skip the LLM call entirely for
    videos already tagged in a prior run.
    """
    if video_id in cache:
        return cache[video_id]

    llm_result = _call_llm(title, description, channel_hint)

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

    _append_metadata_record(record)
    cache[video_id] = record
    return record
