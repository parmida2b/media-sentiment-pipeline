"""
tests/test_schema.py — unit tests for config/schema.py.

Covers roadmap_pipeline.md's own §3 unit-test ask: "تست schema.py:
رکوردهای ناقص باید توسط validate_record رد بشن" (incomplete records must be
rejected by validate_record).
"""

import json

from config.schema import AuthorMetadata, Record, validate_record

REQUIRED_FIELDS = ["text", "date", "source", "platform"]


def _complete_record_dict() -> dict:
    return {
        "text": "sample comment text",
        "date": "2026-03-05T12:00:00Z",
        "source": "youtube",
        "platform": "youtube",
    }


def test_validate_record_accepts_complete_record():
    assert validate_record(_complete_record_dict()) is True


def test_validate_record_rejects_missing_required_field():
    for field in REQUIRED_FIELDS:
        d = _complete_record_dict()
        del d[field]
        assert validate_record(d) is False, f"missing '{field}' should be rejected"


def test_validate_record_rejects_empty_string_required_field():
    # An empty string is present as a key but has no real content -- must be
    # treated the same as missing, not silently accepted.
    for field in REQUIRED_FIELDS:
        d = _complete_record_dict()
        d[field] = ""
        assert validate_record(d) is False, f"empty '{field}' should be rejected"


def test_validate_record_rejects_none_required_field():
    for field in REQUIRED_FIELDS:
        d = _complete_record_dict()
        d[field] = None
        assert validate_record(d) is False, f"None '{field}' should be rejected"


def test_validate_record_ignores_missing_optional_fields():
    # Only the 4 required fields matter -- a dict with just those (no
    # optional fields at all) must still pass.
    assert validate_record(_complete_record_dict()) is True


def test_record_to_json_line_round_trips_and_is_valid_json():
    r = Record(
        text="متن نمونه",
        date="2026-03-05T12:00:00Z",
        source="youtube",
        platform="youtube",
        author_metadata=AuthorMetadata(author_hash="deadbeef", like_count=3),
        language="fa",
        post_id="abc123",
    )
    line = r.to_json_line()
    # Must be exactly one line (JSONL contract) and must not \n-escape --
    # trailing/embedded newlines would corrupt every downstream line-based
    # JSONL reader in src/ingestion/.
    assert "\n" not in line
    parsed = json.loads(line)
    assert parsed["text"] == "متن نمونه"
    assert parsed["author_metadata"]["author_hash"] == "deadbeef"
    assert parsed["post_id"] == "abc123"


def test_record_to_json_line_preserves_non_ascii_unescaped():
    # ensure_ascii=False is load-bearing: Record.to_json_line() must not
    # \uXXXX-escape Persian/Arabic text, or every raw JSONL file becomes
    # unreadable without a JSON parser just to eyeball it.
    r = Record(
        text="سلام",
        date="2026-03-05T12:00:00Z",
        source="youtube",
        platform="youtube",
        author_metadata=AuthorMetadata(),
    )
    assert "سلام" in r.to_json_line()
