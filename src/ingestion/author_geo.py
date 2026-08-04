"""
author_geo.py — per-comment geo tagging aligned with the project brief's
geographic-scope section ("دامنه‌ی جغرافیایی").

The brief fixes a small vocabulary for geo_method (geotag / profile /
timezone / text_place / source_community / language_weak), says to walk it
top-down and record whichever one first produced evidence, and requires
geo_confidence to be categorical (high/medium/low) and geo_granularity to be
one of country/region/city/unknown. It also says location must describe the
COMMENTER (the observation unit), not the video/channel the comment sits
under.

geotag / profile / timezone are never reachable here: the YouTube Data API
does not expose a commenter's geotag, profile location, or timezone on a
comment resource, so this module only ever produces one of the remaining
three.

text_place deliberately matches a narrow self-identification phrase (e.g.
"as an Iranian", "من ایرانی‌ام", "I live in..."), not a bare country/place
mention. On an Iran-US conflict dataset, nearly every on-topic comment says
"Iran" or "America" simply because that IS the topic — bare keyword matching
would mislabel most commenters as being from whichever country they are
talking about. That is the exact failure mode the brief's own geography
section warns about when it calls inferring location from "place names
inside the text" indefensible; the narrower self-identification phrasing is
how this module still offers text_place as a real (if rare) signal without
falling into that trap.
"""

import re

# Self-identification patterns -> ISO 3166-1 alpha-2. Deliberately a short,
# hand-written list, not an exhaustive gazetteer - see module docstring.
_TEXT_PLACE_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b(i'?m|i am|as an?)\s+iranian\b", re.I), "IR"),
    (re.compile(r"\bi\s+live\s+in\s+iran\b", re.I), "IR"),
    (re.compile(r"\b(i'?m|i am|as an?)\s+american\b", re.I), "US"),
    (re.compile(r"\bi\s+live\s+in\s+(the\s+us|the\s+u\.s\.?|america|the\s+united\s+states)\b", re.I), "US"),
    (re.compile(r"من\s+ایرانی(‌ام|\s+هستم)?\b"), "IR"),
    (re.compile(r"(ساکن|زندگی\s+می‌کنم\s+در)\s+ایران\b"), "IR"),
    (re.compile(r"من\s+(آمریکایی|امریکایی)(‌ام|\s+هستم)?\b"), "US"),
    (re.compile(r"(ساکن|زندگی\s+می‌کنم\s+در)\s+(آمریکا|امریکا)\b"), "US"),
    (re.compile(r"أنا\s+إيراني"), "IR"),
    (re.compile(r"أنا\s+أمريكي"), "US"),
]


def _match_text_place(text: str) -> str | None:
    for pattern, country in _TEXT_PLACE_PATTERNS:
        if pattern.search(text):
            return country
    return None


def tag_geo(text: str, channel_hint: dict | None, detected_language: str) -> dict:
    """geo_method/geo_confidence/geo_granularity/country_or_region/geo_limitations
    for one comment, walking the brief's method precedence top-down (skipping
    geotag/profile/timezone, which this API never provides)."""
    place = _match_text_place(text or "")
    if place:
        return {
            "geo_method": "text_place",
            "geo_confidence": "medium",
            "geo_granularity": "country",
            "country_or_region": place,
            "geo_limitations": (
                "Matched a self-identification phrase in the commenter's own "
                "text against a small hand-written pattern list (see "
                "author_geo.py) - narrow by design, so this under-detects "
                "far more often than it mislabels."
            ),
        }

    if channel_hint and channel_hint.get("country"):
        return {
            "geo_method": "source_community",
            "geo_confidence": "low",
            "geo_granularity": "country",
            "country_or_region": channel_hint["country"],
            "geo_limitations": (
                "Inferred from the curated channel registry's known country "
                "for this video's channel - describes the channel/community "
                "the comment appears under, not the individual commenter's "
                "own location."
            ),
        }

    return {
        "geo_method": "language_weak",
        "geo_confidence": "low",
        "geo_granularity": "unknown",
        "country_or_region": "unknown",
        "geo_limitations": (
            f"Only signal available was the comment's detected language "
            f"({detected_language}). Per the project brief (\"language of "
            "text != author's country, never\"), that is not converted into "
            "a country_or_region."
        ),
    }
