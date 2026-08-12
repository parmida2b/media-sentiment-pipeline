"""
author_hash.py — salted author-identifier hashing (Parmida)

Project brief sections 3/10/43 prohibit storing raw usernames/display names
unless strictly necessary. youtube_extract_incremental.py uses this instead
of putting author_display_name on the record.

Hashes author_channel_id (YouTube's stable per-user id) rather than the
display name, because display names change and channel_id is what later
milestones (e.g. author-balanced weighting, project brief section 25) would
actually need to group by the same author across comments/videos.

2026-08-12 (decision_log.md): reformatted to match docs/raw_schema_v05.md
§5's formula, sha256(f"{platform}:{stable_author_id}:{PROJECT_AUTHOR_SALT}")
- ordering/content of the pre-hash string changed from the old
"channel_id:{salt}:{channel_id}" scheme, so old and new hashes for the same
real author do NOT match (see src/ingestion/backfill_author_hash_v05.py for
the one-time re-hash of already-collected data). The old display_name
fallback (for when channel_id was unavailable) was also dropped: v05 defines
no format for that case, and hashing a mutable display name worked against
the whole point of a stable per-author id anyway. Callers should record
author_id_status separately (v05 §5) when this returns None instead.
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


def hash_author(platform: str, channel_id: str | None) -> str | None:
    """Returns a salted sha256 hex digest identifying the author on this
    platform, per docs/raw_schema_v05.md §5:
        sha256(f"{platform}:{stable_author_id}:{PROJECT_AUTHOR_SALT}")

    Returns None if no stable id is available - deliberately no fallback to
    a mutable display name (v05 defines no format for that case; the
    fallback here was intentionally dropped on 2026-08-12, see module
    docstring). Callers should set author_id_status separately when this
    returns None."""
    if not channel_id:
        return None
    salt = _get_salt()
    digest_input = f"{platform}:{channel_id}:{salt}"
    return hashlib.sha256(digest_input.encode("utf-8")).hexdigest()
