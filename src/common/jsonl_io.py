"""
jsonl_io.py — shared "read a JSONL file / pick a source dataset" helper.

Extracted because three call sites had each grown their own independent
"read one JSONL file, skip blank lines, json.loads each line" loop:
  - src/preprocessing/join_and_clean.py's _load_jsonl()
  - src/annotation/run_model_comparison.py's load_sample() (inline loop)
  - src/cost_tracking/estimate_full_run_cost.py's load_eligible_texts()

The last two had already silently diverged on top of that duplication:
run_model_comparison.py's RAW_GLOB only looked at
`data/raw/*/youtube_comments*.jsonl`, while estimate_full_run_cost.py's
RAW_GLOBS also looked at `data/raw/*/reddit_comments*.jsonl` — two scripts
reading two different populations with nothing anywhere flagging the
difference. Fixed as part of this change: both now call
load_source_records() with the SAME raw_globs (see each caller's own
RAW_GLOBS constant, which import this module's default via
DEFAULT_RAW_GLOBS so the list is defined once).

Decision (content, not just refactor): DEFAULT_RAW_GLOBS below includes
BOTH YouTube and Reddit. Once data/interim/clean.jsonl exists (written by
join_and_clean.py), every caller reads that instead and this fallback list
is moot — clean.jsonl already merges both platforms. The raw_globs fallback
only matters pre-preprocessing (clean.jsonl not built yet), and there is no
reason for a script running in that state to silently see YouTube-only data
when Reddit data may already be sitting on disk — that would just be the
same kind of unannounced divergence this change is fixing. The Reddit glob
points at the FIXED `data/raw/reddit/` directory (not a topic-scoped
`data/raw/*/` one), matching reddit_to_record.py's actual, non-topic-scoped
output path (see that module's docstring) and join_and_clean.py's existing
`raw_dir.parent / "reddit"` lookup — not the topic-scoped wildcard
`data/raw/*/reddit_comments*.jsonl` estimate_full_run_cost.py used to have,
which only ever matched by coincidence (because "reddit" happens to be a
valid glob match for the topic_id slot), not by design.
"""

from __future__ import annotations

import glob
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

DEFAULT_RAW_GLOBS: list[str] = [
    str(ROOT / "data" / "raw" / "*" / "youtube_comments*.jsonl"),
    str(ROOT / "data" / "raw" / "reddit" / "reddit_comments*.jsonl"),
]


def read_jsonl_file(path: Path) -> list[dict]:
    """Read one JSONL file, skipping blank lines."""
    records: list[dict] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def load_source_records(clean_path: Path, raw_globs: list[str]) -> list[dict]:
    """Read every record from clean_path if it exists, else concatenate
    every file matched by raw_globs (each pattern glob'd and sorted
    independently, in the order given).

    This is only the "which files populate this run, and read them" part —
    prefer the already-joined/cleaned dataset when present, otherwise fall
    back to raw extraction output directly (e.g. before preprocessing has
    run). Any downstream filtering, sampling, or per-platform bookkeeping is
    the caller's job, not this function's.
    """
    if clean_path.exists():
        return read_jsonl_file(clean_path)

    records: list[dict] = []
    for pattern in raw_globs:
        for fp in sorted(glob.glob(pattern)):
            records.extend(read_jsonl_file(Path(fp)))
    return records
