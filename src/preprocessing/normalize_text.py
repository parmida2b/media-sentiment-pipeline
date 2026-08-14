"""
normalize_text.py -- docs/checklist.md, Phase 5, item 11 (text processing,
derived layer).

Runs over all six apply_eligibility.py outputs (data/interim/*.parquet) and
adds the following columns -- text_raw itself is never touched:

  text_normalized        Unicode NFC + Unicode Cc/Cf (control/format)
                          character removal + collapsed horizontal
                          whitespace. Code-switching (multi-language text)
                          is NOT removed -- the whole string is kept, only
                          whitespace/control characters are touched.
  preprocessing_version   version tag for this transform (reproducibility)
  text_length             len(text_normalized), in characters
  urls_extracted          ";"-joined list of URLs found
  mentions_extracted      ";"-joined list of @handles found
  hashtags_extracted      ";"-joined list of #hashtags found
  emojis_extracted        ";"-joined list of unique emoji found
  pii_masked_flag         True if an email or phone-number-shaped run of
                          digits was found and masked in text_normalized

Language comes from the existing language_detected/language_reported
columns -- this script does not re-run language detection.

All six files are rewritten in place (row count never changes -- only
columns are added, so apply_eligibility.py's row-count reconciliation
equation still holds).

Usage:
    python src/preprocessing/normalize_text.py
    python src/preprocessing/normalize_text.py --dry-run
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent.parent
INTERIM_DIR = ROOT / "data" / "interim"

PREPROCESSING_VERSION = "normalize_text.v1_2026-08-14"

DATASET_TARGETS = [
    "opinion_main", "opinion_limited", "opinion_untimed",
    "context_only", "audit_only", "quarantine",
]

_URL_RE = re.compile(r"https?://\S+")
_MENTION_RE = re.compile(r"(?<!\w)@[A-Za-z0-9_]{1,30}")
_HASHTAG_RE = re.compile(r"(?<!\w)#[^\s#]+", re.UNICODE)
# BMP + common non-BMP emoji ranges (not exhaustive -- a best-effort visible-
# entity extraction for checklist item 11's "extract ... Emoji", not a full
# grapheme-aware emoji tokenizer). Built from chr()/range() rather than a
# literal character class so no raw non-ASCII bytes live in this file.
_EMOJI_RANGES = [
    (0x1F300, 0x1FAFF),  # misc symbols & pictographs .. symbols/pictographs extended-A
    (0x2600, 0x27BF),    # misc symbols, dingbats
    (0x1F1E6, 0x1F1FF),  # regional indicator (flag) letters
]
_EMOJI_CHARS = "".join(chr(c) for lo, hi in _EMOJI_RANGES for c in range(lo, hi + 1))
_EMOJI_RE = re.compile("[" + _EMOJI_CHARS + "❤️]")  # + heart + variation selector

_WHITESPACE_RUN_RE = re.compile(r"[ \t]+")
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE_RE = re.compile(r"(?<!\w)(\+?\d[\d\-\s()]{7,}\d)(?!\w)")

# Unicode general categories treated as "control/format, strip on sight":
#   Cc = control (C0/C1, incl. \x00-\x1f, \x7f)
#   Cf = format (LRM/RLM, bidi embedding/override/isolate marks, BOM/ZWNBSP, ...)
# \t, \n, \r are Cc but are explicitly kept (real line/paragraph structure).
_KEEP_CONTROL_CHARS = {"\t", "\n", "\r"}
_STRIP_CATEGORIES = {"Cc", "Cf"}


def _strip_control_chars(text: str) -> str:
    return "".join(
        ch for ch in text
        if ch in _KEEP_CONTROL_CHARS or unicodedata.category(ch) not in _STRIP_CATEGORIES
    )


def normalize_unicode(text: str) -> str:
    """NFC normalization + control/format-character stripping + collapsing
    runs of horizontal whitespace. Newlines are kept (text_length still
    reflects real multi-line content); code-switched (multi-language) text
    is kept whole -- this only touches whitespace/control characters, never
    removes or truncates a language's content."""
    t = unicodedata.normalize("NFC", text)
    t = _strip_control_chars(t)
    t = _WHITESPACE_RUN_RE.sub(" ", t)
    return t.strip()


def extract_entities(text: str) -> dict:
    return {
        "urls_extracted": ";".join(_URL_RE.findall(text)) or None,
        "mentions_extracted": ";".join(_MENTION_RE.findall(text)) or None,
        "hashtags_extracted": ";".join(_HASHTAG_RE.findall(text)) or None,
        "emojis_extracted": ";".join(dict.fromkeys(_EMOJI_RE.findall(text))) or None,
    }


def mask_pii(text: str) -> tuple[str, bool]:
    """Best-effort PII masking (checklist item 11, "mask likely PII"):
    replaces an email or a phone-number-shaped run of digits with a fixed
    placeholder. Conservative on purpose (few, well-defined patterns) --
    this is not a general PII detector, and false negatives are safer here
    than false positives that would mangle ordinary numeric text (dates,
    vote counts, prices) that make up a lot of real opinion content."""
    masked = False

    def _email_sub(m):
        nonlocal masked
        masked = True
        return "[EMAIL]"

    def _phone_sub(m):
        nonlocal masked
        masked = True
        return "[PHONE]"

    text = _EMAIL_RE.sub(_email_sub, text)
    text = _PHONE_RE.sub(_phone_sub, text)
    return text, masked


def process_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    normalized, lengths = [], []
    urls, mentions, hashtags, emojis, pii_flags = [], [], [], [], []

    for raw in df["text_raw"]:
        text = raw if isinstance(raw, str) else ""
        norm = normalize_unicode(text)
        entities = extract_entities(norm)
        norm_masked, was_masked = mask_pii(norm)

        normalized.append(norm_masked)
        lengths.append(len(norm_masked))
        urls.append(entities["urls_extracted"])
        mentions.append(entities["mentions_extracted"])
        hashtags.append(entities["hashtags_extracted"])
        emojis.append(entities["emojis_extracted"])
        pii_flags.append(was_masked)

    df["text_normalized"] = normalized
    df["preprocessing_version"] = PREPROCESSING_VERSION
    df["text_length"] = lengths
    df["urls_extracted"] = urls
    df["mentions_extracted"] = mentions
    df["hashtags_extracted"] = hashtags
    df["emojis_extracted"] = emojis
    df["pii_masked_flag"] = pii_flags
    return df


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    for target in DATASET_TARGETS:
        path = INTERIM_DIR / f"{target}.parquet"
        if not path.exists():
            print(f"skip {target}: {path} not found (run apply_eligibility.py first)")
            continue
        df = pd.read_parquet(path)
        n_before = len(df)
        already_done = "text_normalized" in df.columns
        out = process_dataframe(df)
        assert len(out) == n_before, f"row count changed for {target}: {n_before} -> {len(out)}"

        n_pii = int(out["pii_masked_flag"].sum())
        n_url = int(out["urls_extracted"].notna().sum())
        note = " (already had text_normalized -- overwritten)" if already_done else ""
        print(f"{target:16s} rows={n_before:8d}  pii_masked={n_pii:6d}  has_url={n_url:6d}{note}")
        if not args.dry_run:
            out.to_parquet(path, index=False)

    print(f"\npreprocessing_version={PREPROCESSING_VERSION}")
    if args.dry_run:
        print("--dry-run: nothing written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
