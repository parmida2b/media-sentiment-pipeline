"""
author_hash.py — salted author-identifier hashing (Parmida)

Project brief sections 3/10/43 prohibit storing raw usernames/display names
unless strictly necessary. youtube_extract_incremental.py uses this instead
of putting author_display_name on the record.

Hashes author_channel_id (YouTube's stable per-user id) rather than the
display name, because display names change and channel_id is what later
milestones (e.g. author-balanced weighting, project brief section 25) would
actually need to group by the same author across comments/videos.
"""

import hashlib
import os

# Only used if AUTHOR_HASH_SALT is unset in .env - documented here rather
# than hidden, so a missing .env value fails loud (via the printed warning)
# instead of silently producing unsalted-equivalent hashes.
_FALLBACK_SALT = "media-sentiment-pipeline-starter-unsalted-fallback"

_warned = False


def _get_salt() -> str:
    global _warned
    salt = os.getenv("AUTHOR_HASH_SALT")
    if not salt:
        if not _warned:
            print(
                "[warn] AUTHOR_HASH_SALT is not set in .env — using a fixed "
                "fallback salt. Set AUTHOR_HASH_SALT before collecting data "
                "you intend to keep, otherwise author hashes aren't reproducible "
                "against a real secret."
            )
            _warned = True
        return _FALLBACK_SALT
    return salt


def hash_author(channel_id: str | None, display_name: str | None) -> str | None:
    """Returns a salted sha256 hex digest identifying the author, preferring
    the stable channel_id over the mutable display name. Returns None if
    neither is available (nothing to hash)."""
    salt = _get_salt()

    if channel_id:
        digest_input = f"channel_id:{salt}:{channel_id}"
    elif display_name:
        # Prefixed differently so a channel_id-based hash and a
        # display-name-based hash for the "same" author never collide.
        digest_input = f"display_name:{salt}:{display_name}"
    else:
        return None

    return hashlib.sha256(digest_input.encode("utf-8")).hexdigest()
