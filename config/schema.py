"""
schema.py — unified data format definition for the whole team
---------------------------------------------------------------
This file is the single source of truth for the data format.
Only Hossein edits this file; everyone else just imports from it.
If a field needs to change, coordinate with the team first.

Version: v1 - Day 1
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any
import json


@dataclass
class AuthorMetadata:
    author_display_name: Optional[str] = None
    author_channel_id: Optional[str] = None   # or user_id, depending on the platform
    like_count: int = 0
    follower_count: Optional[int] = None      # if the platform provides it (e.g. Reddit/Telegram)
    account_age_days: Optional[int] = None    # for bot filtering later (Ali/Reyhaneh)


@dataclass
class Record:
    """A standard record - the output of every extraction module must match this shape."""
    text: str
    date: str                      # ISO 8601, e.g. "2026-03-05T12:00:00Z"
    source: str                    # "youtube" | "reddit" | "telegram" | ...
    platform: str                  # usually the same as source, kept separate for flexibility
    author_metadata: AuthorMetadata

    # Optional fields shared across sources
    language: Optional[str] = None         # "fa" | "en" | "ar" | ...
    post_id: Optional[str] = None          # video_id / submission_id / message_id
    post_title: Optional[str] = None
    reply_count: int = 0
    is_reply: bool = False

    def to_json_line(self) -> str:
        d = asdict(self)
        return json.dumps(d, ensure_ascii=False)


def validate_record(d: Dict[str, Any]) -> bool:
    """Quick check before saving - prevents incomplete data from entering the pipeline."""
    required = ["text", "date", "source", "platform"]
    return all(k in d and d[k] not in (None, "") for k in required)


if __name__ == "__main__":
    # usage example
    r = Record(
        text="sample comment text",
        date="2026-03-05T12:00:00Z",
        source="youtube",
        platform="youtube",
        author_metadata=AuthorMetadata(author_display_name="test_user", like_count=3),
        language="fa",
        post_id="abc123",
    )
    print(r.to_json_line())
