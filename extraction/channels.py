"""
channels.py — structured, categorized YouTube channel registry (Parmida)

Each entry is verified at runtime against the channel's own `customUrl`
(via youtube_extract.find_channel_id) rather than trusted by search order,
so a misnamed handle just logs a warning and gets skipped instead of
silently pulling in the wrong channel.

This starter list is a first pass, not exhaustive — extend per category
as the team identifies more sources to cover.
"""

CHANNEL_REGISTRY = {
    "iran_state": [
        {"name": "Press TV", "handle": "presstelevision", "country": "IR"},
        {"name": "IRIB News", "handle": "iribn", "country": "IR"},
    ],
    "iran_diaspora": [
        {"name": "Iran International", "handle": "iranintl", "country": "GB"},
        {"name": "BBC Persian", "handle": "bbcnewspersian", "country": "GB"},
        {"name": "VOA Persian", "handle": "voafarsi", "country": "US"},
    ],
    "us_western": [
        {"name": "CNN", "handle": "cnn", "country": "US"},
        {"name": "The New York Times", "handle": "nytimes", "country": "US"},
        {"name": "CBS News", "handle": "cbsnews", "country": "US"},
    ],
    "arab_gulf": [
        {"name": "Al Jazeera English", "handle": "aljazeeraenglish", "country": "QA"},
        {"name": "Al Arabiya", "handle": "alarabiya", "country": "AE"},
    ],
    "european_western": [
        {"name": "BBC News", "handle": "bbcnews", "country": "GB"},
        {"name": "Sky News", "handle": "skynews", "country": "GB"},
        {"name": "DW News", "handle": "dwnews", "country": "DE"},
        {"name": "France 24", "handle": "france24_en", "country": "FR"},
        {"name": "euronews", "handle": "euronews", "country": "FR"},
        {"name": "RFI", "handle": "rfi_en", "country": "FR"},
    ],
    "international_thinktank": [
        {"name": "CSIS", "handle": "csis", "country": "US"},
        {"name": "Reuters", "handle": "reuters", "country": "GB"},
    ],
}

# Discovery priority order — checkpoint.py resumability means this alone
# determines what gets covered first across multiple runs/days, no
# separate "day N" bookkeeping needed.
PRIORITY_ORDER = [
    "iran_state",
    "us_western",
    "european_western",
    "arab_gulf",
    "iran_diaspora",
    "international_thinktank",
]


def iter_channels():
    """Yield (category, channel_dict) in PRIORITY_ORDER."""
    for category in PRIORITY_ORDER:
        for channel in CHANNEL_REGISTRY.get(category, []):
            yield category, channel
