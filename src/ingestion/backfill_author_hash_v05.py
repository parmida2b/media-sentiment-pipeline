"""
backfill_author_hash_v05.py — one-time re-hash of already-collected YouTube
author_hash values from the old (v03) formula to the new (v05) formula.

Context (see docs/decision_log.md 2026-08-12): author_hash.py's hash_author()
changed from
    channel_id path:   sha256(f"channel_id:{SALT}:{channel_id}")
    display_name path: sha256(f"display_name:{SALT}:{display_name}")  (fallback)
to docs/raw_schema_v05.md §5's formula
    sha256(f"{platform}:{channel_id}:{SALT}")
(no display_name fallback — author_hash is None when channel_id is absent).

Old and new hashes for the SAME real author do not match (different pre-hash
string), so every already-collected record's author_hash needs recomputing,
not just new collection going forward. This is a one-time, explicitly
requested backfill (not something main collection re-runs on its own).

What it does, per platform data dir (currently just youtube/{topic_id}):
  1. Copies the existing youtube_comments_v2.jsonl and youtube_raw_export.csv
     into an archive_before_author_hash_v05_backfill_{date}/ folder, untouched
     (source of truth if anything here needs to be undone).
  2. Streams the JSONL, recomputes author_hash for every record from its
     still-present raw author_metadata.author_channel_id, and writes a
     corrected JSONL to a temp file.
  3. Streams the CSV and overwrites its author_hash column using a
     content_id -> new_hash map built in step 2 (keyed by content_id, not by
     row position, so this doesn't depend on the two files staying in lockstep
     row-for-row).
  4. Sanity-checks row counts match the originals, then atomically replaces
     both files.

Idempotent: recomputing an already-correct hash yields the same value, so
re-running this after a successful backfill is a no-op (aside from rewriting
files with identical content and making a redundant archive copy).

Usage:
    python src/ingestion/backfill_author_hash_v05.py
"""

import csv
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from config import config_loader
from config.raw_schema_columns import RAW_SCHEMA_COLUMNS

import author_hash

load_dotenv()

CONFIG = config_loader.load_config()
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "raw" / CONFIG.topic_id
JSONL_PATH = DATA_DIR / "youtube_comments_v2.jsonl"
CSV_PATH = DATA_DIR / "youtube_raw_export.csv"

TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")
ARCHIVE_DIR = DATA_DIR / f"archive_before_author_hash_v05_backfill_{TODAY}"


def backup_originals() -> None:
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    for path in (JSONL_PATH, CSV_PATH):
        if not path.exists():
            print(f"[warn] {path} does not exist — nothing to back up/backfill for it.")
            continue
        dest = ARCHIVE_DIR / path.name
        if dest.exists():
            print(f"[skip] {dest} already backed up (re-run) — not overwriting archive copy.")
            continue
        shutil.copy2(path, dest)
        print(f"[backup] {path} -> {dest}")


def rehash_jsonl() -> tuple[dict[str, str | None], int, int]:
    """Returns (content_id -> new author_hash map, records processed, records changed)."""
    if not JSONL_PATH.exists():
        return {}, 0, 0

    tmp_path = JSONL_PATH.with_suffix(".jsonl.rehash_tmp")
    content_id_to_hash: dict[str, str | None] = {}
    processed = 0
    changed = 0

    with open(JSONL_PATH, "r", encoding="utf-8") as fin, \
         open(tmp_path, "w", encoding="utf-8") as fout:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            processed += 1

            content_id = record.get("content_id")
            author_metadata = record.get("author_metadata") or {}
            channel_id = author_metadata.get("author_channel_id")
            old_hash = author_metadata.get("author_hash")

            new_hash = author_hash.hash_author("youtube", channel_id)
            if new_hash != old_hash:
                changed += 1
            author_metadata["author_hash"] = new_hash
            record["author_metadata"] = author_metadata

            if content_id:
                content_id_to_hash[content_id] = new_hash

            fout.write(json.dumps(record, ensure_ascii=False) + "\n")

    old_count = sum(1 for _ in open(JSONL_PATH, "r", encoding="utf-8") if _.strip())
    new_count = sum(1 for _ in open(tmp_path, "r", encoding="utf-8") if _.strip())
    if new_count != old_count:
        tmp_path.unlink()
        raise RuntimeError(
            f"JSONL row count mismatch after rehash ({old_count} -> {new_count}) — "
            "aborted, original file untouched."
        )

    tmp_path.replace(JSONL_PATH)
    return content_id_to_hash, processed, changed


def rehash_csv(content_id_to_hash: dict[str, str | None]) -> tuple[int, int]:
    """Overwrites the author_hash column using the JSONL-derived map, keyed by
    platform_content_id. Returns (rows processed, rows changed)."""
    if not CSV_PATH.exists():
        return 0, 0

    tmp_path = CSV_PATH.with_suffix(".csv.rehash_tmp")
    processed = 0
    changed = 0

    with open(CSV_PATH, "r", encoding="utf-8", newline="") as fin, \
         open(tmp_path, "w", encoding="utf-8", newline="") as fout:
        reader = csv.DictReader(fin)
        writer = csv.DictWriter(fout, fieldnames=RAW_SCHEMA_COLUMNS)
        writer.writeheader()
        for row in reader:
            processed += 1
            content_id = row.get("platform_content_id")
            old_value = row.get("author_hash", "")
            if content_id in content_id_to_hash:
                new_value = content_id_to_hash[content_id] or ""
            else:
                # No matching JSONL record (shouldn't happen on clean data,
                # but don't silently invent a value) - leave the CSV row's
                # existing author_hash untouched rather than guessing.
                new_value = old_value
            if new_value != old_value:
                changed += 1
            row["author_hash"] = new_value
            writer.writerow(row)

    with open(CSV_PATH, "r", encoding="utf-8", newline="") as f:
        old_count = sum(1 for _ in csv.reader(f)) - 1  # minus header
    with open(tmp_path, "r", encoding="utf-8", newline="") as f:
        new_count = sum(1 for _ in csv.reader(f)) - 1
    if new_count != old_count:
        tmp_path.unlink()
        raise RuntimeError(
            f"CSV row count mismatch after rehash ({old_count} -> {new_count}) — "
            "aborted, original file untouched."
        )

    tmp_path.replace(CSV_PATH)
    return processed, changed


def main() -> None:
    print(f"Backfilling author_hash (v03 -> v05 formula) for {DATA_DIR}\n")
    backup_originals()

    print("\nRe-hashing JSONL (source of truth - has raw author_channel_id)...")
    content_id_to_hash, jsonl_processed, jsonl_changed = rehash_jsonl()
    print(f"  {jsonl_processed} record(s) processed, {jsonl_changed} hash value(s) changed.")

    print("\nRe-hashing CSV export (author_hash column only, keyed by platform_content_id)...")
    csv_processed, csv_changed = rehash_csv(content_id_to_hash)
    print(f"  {csv_processed} row(s) processed, {csv_changed} hash value(s) changed.")

    print(f"\nDone. Pre-backfill originals archived under {ARCHIVE_DIR}")


if __name__ == "__main__":
    main()
