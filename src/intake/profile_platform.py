"""
profile_platform.py -- legacy raw-data inventory/profile for one platform.

Implements the "Freeze and Inventory" (doc section 3) and "Initial profile
without changing data" (doc section 4) steps of
docs/legacy_data_intake_and_harmonization_plan_v1.md for files that are
already sitting under data/raw/, without collecting anything new and
without rewriting/renaming/cleaning the source files.

For --platform {youtube,reddit,x} it:
  1. Walks data/raw/ recursively and finds files that (a) look like the
     requested platform and (b) look like row-based opinion content (they
     have a recognizable free-text field) rather than a run log, a config
     file, or a derived side-file (checkpoint/registry/geo-tag output).
  2. Computes real, checkable stats per file (row count, sha256, oldest /
     newest parseable timestamp, missing id/timestamp/text counts, id
     duplicates, ...) by reading every record -- no sampling, no guessing.
  3. Appends one new manifest row per newly-seen raw file to
     docs/data_handoff_manifest_template.csv (existing rows are never
     rewritten; a file already recorded there is skipped, not duplicated).
  4. Replaces the single summary row for that platform in
     docs/collection_coverage_template.csv with the aggregated numbers
     (that template is a one-row-per-platform summary, so "update" there
     means replace-in-place, not append).

Any column that cannot be determined from the file itself (or from a
directly matching companion file already on disk, e.g. a run log with an
exact schema match) is written as "unknown" -- never guessed. See
docs/legacy_data_intake_and_harmonization_plan_v1.md sections 1, 3, 4, 6.

Usage:
    python src/intake/profile_platform.py --platform youtube
    python src/intake/profile_platform.py --platform reddit --dry-run
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RAW_DIR = REPO_ROOT / "data" / "raw"
DEFAULT_MANIFEST = REPO_ROOT / "docs" / "data_handoff_manifest_template.csv"
DEFAULT_COVERAGE = REPO_ROOT / "docs" / "collection_coverage_template.csv"

UNKNOWN = "unknown"

PLATFORMS = ("youtube", "reddit", "x")
PLATFORM_ALIASES = {
    "youtube": {"youtube", "yt"},
    "reddit": {"reddit"},
    "x": {"x", "twitter", "tweet", "tweets"},
}

# Candidate field/column names, in priority order. The first one present in
# a file's own schema (CSV header / JSON(L) record keys) is used for that
# file. Names come from config/raw_schema_columns.py (this project's own
# harmonized export contract) plus the native field names actually observed
# in data/raw/ (e.g. youtube_comments_*.jsonl uses "post_id"/"date"/"text").
TEXT_FIELD_CANDIDATES = [
    "text_raw", "text", "body", "selftext", "full_text", "comment_text", "content",
]
ID_FIELD_CANDIDATES = [
    "platform_content_id", "post_id", "comment_id", "submission_id", "tweet_id", "id",
]
TIMESTAMP_FIELD_CANDIDATES = [
    "created_at_utc", "date", "created_utc", "created_at", "timestamp", "published_at",
]
QUERY_FIELD_CANDIDATES = ["query_id", "query", "query_text"]
SOURCE_FIELD_CANDIDATES = ["source_id", "source_container", "source"]

DELETED_TEXT_MARKERS = {"[deleted]", "[removed]"}

RECORD_EXTENSIONS = {".csv", ".json", ".jsonl"}

SECRET_PATTERNS = {
    "api_key": re.compile(r"api[_-]?key\s*[:=]", re.I),
    "auth_token": re.compile(r"\b(access|auth|bearer|refresh)[_-]?token\b", re.I),
    "password": re.compile(r"\bpassword\b", re.I),
    "secret": re.compile(r"\bsecret\b", re.I),
    "cookie": re.compile(r"\bcookie\b", re.I),
    "aws_access_key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "google_api_key": re.compile(r"AIza[0-9A-Za-z_\-]{35}"),
    "bearer_header": re.compile(r"Bearer\s+[A-Za-z0-9\-_.]{10,}"),
}
SECRET_SCAN_ROW_SAMPLE = 50

TS_TZ_MARKER = re.compile(r"(Z|[+-]\d{2}:?\d{2})$")

MANIFEST_COLUMNS = [
    "handoff_id", "platform", "provided_by", "received_at_utc", "original_file_name",
    "relative_path", "file_role", "file_format", "file_size_bytes", "sha256",
    "source_schema_version", "source_query_registry_version", "collector_name",
    "collector_version", "run_log_available", "config_available", "contains_secrets",
    "notes",
]
COVERAGE_COLUMNS = [
    "platform", "source_file", "quality_grade", "raw_n", "parseable_n",
    "unique_platform_id_n", "missing_id_n", "missing_timestamp_n", "missing_text_n",
    "oldest_created_at_utc", "newest_created_at_utc", "days_with_data", "weeks_with_data",
    "duplicate_id_n", "query_known_pct", "source_known_pct", "notes",
]

# Run-log shape actually used in this repo (MANIFEST_COLUMNS in
# src/ingestion/youtube_extract.py == youtube_runs.csv header).
RUN_LOG_MARKER_COLUMNS = {"collection_run_id", "started_at_utc", "finished_at_utc"}


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------

def find_field(keys: Iterable[str], candidates: list[str]) -> str | None:
    lower_map = {str(k).strip().lower(): k for k in keys}
    for cand in candidates:
        if cand in lower_map:
            return lower_map[cand]
    return None


def is_blank(value: Any) -> bool:
    return value is None or str(value).strip() == ""


def parse_ts_utc(value: Any) -> tuple[datetime | None, str]:
    """Returns (datetime_or_None, status).

    status is one of: "ok", "empty", "no_timezone_marker", "parse_error".
    Per plan section 5: a naive/local timestamp without an explicit
    timezone marker is NOT assumed to be UTC -- it is reported as
    unreliable instead of silently converted.
    """
    if is_blank(value):
        return None, "empty"
    s = str(value).strip()
    # epoch seconds/millis (inherently UTC, no tz ambiguity)
    try:
        f = float(s)
        if 946684800 <= f <= 4102444800:  # 2000-01-01 .. 2100-01-01
            return datetime.fromtimestamp(f, tz=timezone.utc), "ok"
        if 946684800000 <= f <= 4102444800000:
            return datetime.fromtimestamp(f / 1000.0, tz=timezone.utc), "ok"
    except ValueError:
        pass
    if not TS_TZ_MARKER.search(s):
        return None, "no_timezone_marker"
    iso = s[:-1] + "+00:00" if s.endswith("Z") else s
    try:
        dt = datetime.fromisoformat(iso)
    except ValueError:
        return None, "parse_error"
    return dt.astimezone(timezone.utc), "ok"


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def detect_platform_token(value: str) -> str | None:
    s = value.strip().lower()
    for plat, aliases in PLATFORM_ALIASES.items():
        if s == plat or s in aliases:
            return plat
    return None


def path_tokens(path: Path) -> set[str]:
    return {t for t in re.split(r"[^a-z0-9]+", str(path).lower()) if t}


def scan_for_secrets(header_keys: Iterable[str], sample_rows: list[dict], filename: str) -> list[str]:
    haystack_parts = [filename, " ".join(str(k) for k in header_keys)]
    for row in sample_rows:
        haystack_parts.extend(str(v) for v in row.values() if v is not None)
    haystack = "\n".join(haystack_parts)
    hits = [name for name, pat in SECRET_PATTERNS.items() if pat.search(haystack)]
    return hits


# ---------------------------------------------------------------------------
# record iteration (csv / json array / jsonl)
# ---------------------------------------------------------------------------

@dataclass
class RecordSource:
    kind: str  # "csv" | "json_array" | "jsonl" | "json_object" | "unreadable" | "empty"
    header_keys: list[str] = field(default_factory=list)
    records: Iterator[dict] | None = None
    parse_error_lines: int = 0
    decode_replacement_chars: int = 0


def open_record_source(path: Path) -> RecordSource:
    ext = path.suffix.lower()
    if ext == ".csv":
        try:
            fh = path.open("r", encoding="utf-8-sig", errors="replace", newline="")
        except OSError:
            return RecordSource(kind="unreadable")
        reader = csv.DictReader(fh)
        header = reader.fieldnames or []
        if not header:
            fh.close()
            return RecordSource(kind="empty")

        def _gen():
            with fh:
                for row in reader:
                    yield row

        return RecordSource(kind="csv", header_keys=list(header), records=_gen())

    try:
        raw = path.read_bytes()
    except OSError:
        return RecordSource(kind="unreadable")
    if not raw.strip():
        return RecordSource(kind="empty")
    text = raw.decode("utf-8", errors="replace")
    replacement_chars = text.count("�")

    # Try whole-file JSON first (array-of-records or a single object).
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = None

    if isinstance(parsed, list):
        dict_records = [r for r in parsed if isinstance(r, dict)]
        header = list(dict_records[0].keys()) if dict_records else []
        return RecordSource(
            kind="json_array", header_keys=header, records=iter(dict_records),
            decode_replacement_chars=replacement_chars,
        )
    if isinstance(parsed, dict):
        return RecordSource(kind="json_object", decode_replacement_chars=replacement_chars)

    # Fall back to JSON Lines.
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return RecordSource(kind="empty")
    records: list[dict] = []
    parse_errors = 0
    for ln in lines:
        try:
            obj = json.loads(ln)
        except json.JSONDecodeError:
            parse_errors += 1
            continue
        if isinstance(obj, dict):
            records.append(obj)
        else:
            parse_errors += 1
    header = list(records[0].keys()) if records else []
    return RecordSource(
        kind="jsonl", header_keys=header, records=iter(records),
        parse_error_lines=parse_errors, decode_replacement_chars=replacement_chars,
    )


# ---------------------------------------------------------------------------
# per-file profiling
# ---------------------------------------------------------------------------

@dataclass
class FileProfile:
    path: Path
    relative_path: str
    file_format: str
    file_size_bytes: int
    sha256: str
    mtime_utc: str
    raw_n: int = 0
    parseable_n: int | None = None
    text_field: str | None = None
    id_field: str | None = None
    ts_field: str | None = None
    query_field: str | None = None
    source_field: str | None = None
    missing_text_n: int = 0
    missing_id_n: int | None = None
    missing_ts_n: int | None = None
    unique_id_n: int | None = None
    duplicate_id_n: int | None = None
    query_known_n: int | None = None
    source_known_n: int | None = None
    oldest_ts: datetime | None = None
    newest_ts: datetime | None = None
    ts_no_tz_marker_n: int = 0
    ts_parse_error_n: int = 0
    dates_with_data: set = field(default_factory=set)
    weeks_with_data: set = field(default_factory=set)
    parse_error_lines: int = 0
    decode_replacement_chars: int = 0
    platform_detect_method: str = UNKNOWN
    collector_version_values: set = field(default_factory=set)
    schema_matches_raw_schema_v03: bool = False
    contains_secrets: bool = False
    secret_hit_types: list[str] = field(default_factory=list)
    all_id_values: list = field(default_factory=list)
    notes_registry_match: str | None = None
    source_values_seen: set = field(default_factory=set)
    source_field_downgraded: bool = False


@dataclass
class SkipInfo:
    path: Path
    reason: str


def profile_file(
    path: Path, target_platform: str, raw_schema_columns: list[str] | None,
    registry_query_ids: set[str] | None, registry_version: str | None,
) -> FileProfile | SkipInfo:
    src = open_record_source(path)

    if src.kind in ("unreadable", "empty"):
        return SkipInfo(path, f"{src.kind}: could not read a record schema from this file")
    if src.kind == "json_object":
        return SkipInfo(path, "top-level JSON object (config/lookup shaped), not row-based content")

    text_field = find_field(src.header_keys, TEXT_FIELD_CANDIDATES)
    if text_field is None:
        return SkipInfo(
            path,
            f"no recognizable free-text field in schema (keys seen: {', '.join(src.header_keys) or 'none'})",
        )

    id_field = find_field(src.header_keys, ID_FIELD_CANDIDATES)
    ts_field = find_field(src.header_keys, TIMESTAMP_FIELD_CANDIDATES)
    query_field = find_field(src.header_keys, QUERY_FIELD_CANDIDATES)
    source_field = find_field(src.header_keys, SOURCE_FIELD_CANDIDATES)
    platform_field = find_field(src.header_keys, ["platform"])

    stat = path.stat()
    profile = FileProfile(
        path=path,
        relative_path=path.resolve().relative_to(REPO_ROOT).as_posix(),
        file_format={"csv": "csv", "json_array": "json", "jsonl": "jsonl"}[src.kind],
        file_size_bytes=stat.st_size,
        sha256=sha256_of(path),
        mtime_utc=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        text_field=text_field,
        id_field=id_field,
        ts_field=ts_field,
        query_field=query_field,
        source_field=source_field,
        parse_error_lines=src.parse_error_lines,
        decode_replacement_chars=src.decode_replacement_chars,
    )
    if id_field is not None:
        profile.missing_id_n = 0
        profile.all_id_values = []
    if ts_field is not None:
        profile.missing_ts_n = 0
        profile.parseable_n = 0
    if query_field is not None:
        profile.query_known_n = 0
    if source_field is not None:
        profile.source_known_n = 0

    platform_values_seen: set[str] = set()
    sample_rows: list[dict] = []

    for row in src.records:
        profile.raw_n += 1
        if len(sample_rows) < SECRET_SCAN_ROW_SAMPLE:
            sample_rows.append(row)

        if platform_field is not None:
            v = row.get(platform_field)
            if not is_blank(v):
                detected = detect_platform_token(str(v))
                if detected:
                    platform_values_seen.add(detected)

        text_val = row.get(text_field)
        if is_blank(text_val) or str(text_val).strip() in DELETED_TEXT_MARKERS:
            profile.missing_text_n += 1

        if id_field is not None:
            id_val = row.get(id_field)
            if is_blank(id_val):
                profile.missing_id_n += 1
            else:
                profile.all_id_values.append(str(id_val).strip())

        if ts_field is not None:
            dt, status = parse_ts_utc(row.get(ts_field))
            if status == "empty":
                profile.missing_ts_n += 1
            elif status == "no_timezone_marker":
                profile.ts_no_tz_marker_n += 1
            elif status == "parse_error":
                profile.ts_parse_error_n += 1
            else:
                profile.parseable_n += 1
                if profile.oldest_ts is None or dt < profile.oldest_ts:
                    profile.oldest_ts = dt
                if profile.newest_ts is None or dt > profile.newest_ts:
                    profile.newest_ts = dt
                profile.dates_with_data.add(dt.date())
                iso = dt.isocalendar()
                profile.weeks_with_data.add((iso[0], iso[1]))

        if query_field is not None and not is_blank(row.get(query_field)):
            profile.query_known_n += 1
        if source_field is not None:
            sv = row.get(source_field)
            if not is_blank(sv):
                profile.source_known_n += 1
                if len(profile.source_values_seen) < 20:
                    profile.source_values_seen.add(str(sv).strip().lower())

        cv = row.get("collector_version")
        if not is_blank(cv):
            profile.collector_version_values.add(str(cv).strip())

    # A "source" column that only ever holds a platform name (e.g. every
    # value is literally "youtube") is not real source/provenance evidence
    # -- it is just an echo of the platform column under a different name.
    # Downgrade it rather than reporting a source_known_pct that implies
    # real per-record provenance was captured.
    all_platform_tokens = {p for aliases in PLATFORM_ALIASES.values() for p in aliases}
    if (
        source_field is not None
        and source_field.strip().lower() == "source"
        and profile.source_values_seen
        and profile.source_values_seen.issubset(all_platform_tokens)
    ):
        profile.source_field_downgraded = True
        profile.source_known_n = None

    # platform match decision
    if platform_field is not None:
        if platform_values_seen == {target_platform}:
            profile.platform_detect_method = "field:platform"
        elif platform_values_seen:
            return SkipInfo(
                path,
                f"platform field present but values={sorted(platform_values_seen)} "
                f"do not match requested platform={target_platform}",
            )
        else:
            path_plat = None
            toks = path_tokens(path)
            for plat, aliases in PLATFORM_ALIASES.items():
                if toks & aliases:
                    path_plat = plat
                    break
            if path_plat == target_platform:
                profile.platform_detect_method = "filename (platform field present but unpopulated)"
            else:
                return SkipInfo(path, "platform field present but empty on every row, and filename does not match")
    else:
        toks = path_tokens(path)
        path_plat = None
        for plat, aliases in PLATFORM_ALIASES.items():
            if toks & aliases:
                path_plat = plat
                break
        if path_plat != target_platform:
            return SkipInfo(path, f"no 'platform' field, and filename/path does not identify it as {target_platform}")
        profile.platform_detect_method = "filename"

    if id_field is not None:
        profile.unique_id_n = len(set(profile.all_id_values))
        profile.duplicate_id_n = len(profile.all_id_values) - profile.unique_id_n

    if raw_schema_columns:
        header_lower = {h.strip().lower() for h in src.header_keys}
        required_lower = {c.lower() for c in raw_schema_columns}
        if required_lower.issubset(header_lower):
            profile.schema_matches_raw_schema_v03 = True

    if registry_query_ids is not None and query_field is not None and profile.query_known_n:
        seen_query_ids = set()
        # second cheap pass avoided: reuse sample if raw_n small, else approximate is not acceptable
        # -> re-open and scan just the query column for exactness
        src2 = open_record_source(path)
        if src2.records is not None:
            for row in src2.records:
                v = row.get(query_field)
                if not is_blank(v):
                    seen_query_ids.add(str(v).strip())
        if seen_query_ids and seen_query_ids.issubset(registry_query_ids):
            profile.notes_registry_match = registry_version

    profile.secret_hit_types = scan_for_secrets(src.header_keys, sample_rows, path.name)
    profile.contains_secrets = bool(profile.secret_hit_types)

    return profile


# ---------------------------------------------------------------------------
# discovery
# ---------------------------------------------------------------------------

def discover_candidate_files(raw_dir: Path) -> list[Path]:
    if not raw_dir.exists():
        return []
    out = []
    for p in sorted(raw_dir.rglob("*")):
        if not p.is_file():
            continue
        if p.suffix.lower() not in RECORD_EXTENSIONS:
            continue
        if p.name == ".gitkeep":
            continue
        out.append(p)
    return out


def load_raw_schema_columns() -> list[str] | None:
    path = REPO_ROOT / "config" / "raw_schema_columns.py"
    if not path.exists():
        return None
    try:
        spec = importlib.util.spec_from_file_location("raw_schema_columns", path)
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        return list(mod.RAW_SCHEMA_COLUMNS)
    except Exception:
        return None


def load_query_registry() -> tuple[set[str] | None, str | None]:
    path = REPO_ROOT / "config" / "query_registry.yaml"
    if not path.exists():
        return None, None
    try:
        import yaml  # local import: optional dependency already in requirements.txt
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        return None, None
    if not isinstance(data, dict):
        return None, None
    version = data.get("registry_version")
    ids: set[str] = set()
    for value in data.values():
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict) and "query_id" in item:
                    ids.add(str(item["query_id"]))
    return (ids or None), (str(version) if version is not None else None)


def companion_files_available(dirs: set[Path]) -> tuple[bool, bool]:
    """Best-effort structural check for a run log / config file sitting next
    to the raw files we profiled. Returns (run_log_available, config_available)
    as True/False only when positive evidence is found; callers must treat
    "not found" as unknown, not as a confirmed absence (the log/config could
    live outside data/raw/, e.g. a handoff run_logs/ folder that was never
    delivered into this repo).
    """
    run_log_found = False
    config_found = False
    for d in dirs:
        if not d.exists():
            continue
        for p in d.iterdir():
            if not p.is_file():
                continue
            if p.suffix.lower() == ".csv":
                try:
                    with p.open("r", encoding="utf-8-sig", errors="replace", newline="") as fh:
                        header = next(csv.reader(fh), [])
                except OSError:
                    header = []
                if RUN_LOG_MARKER_COLUMNS.issubset({h.strip() for h in header}):
                    run_log_found = True
            elif p.suffix.lower() == ".json":
                try:
                    obj = json.loads(p.read_text(encoding="utf-8", errors="replace"))
                except (OSError, json.JSONDecodeError):
                    obj = None
                if isinstance(obj, dict):
                    config_found = True
    return run_log_found, config_found


# ---------------------------------------------------------------------------
# manifest / coverage writers
# ---------------------------------------------------------------------------

def read_csv_rows(path: Path) -> tuple[list[str], list[dict]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        fieldnames = reader.fieldnames or []
        rows = list(reader)
    return fieldnames, rows


def next_handoff_id(existing_rows: list[dict]) -> Iterator[str]:
    max_n = 0
    for r in existing_rows:
        m = re.match(r"HF0*(\d+)$", (r.get("handoff_id") or "").strip())
        if m:
            max_n = max(max_n, int(m.group(1)))
    n = max_n
    while True:
        n += 1
        yield f"HF{n:03d}"


def build_manifest_row(
    profile: FileProfile, platform: str,
    run_log_available: bool, config_available: bool,
    registry_version: str | None, handoff_id: str,
) -> dict:
    notes_bits = [
        f"text_field={profile.text_field}",
        f"id_field={profile.id_field or UNKNOWN}",
        f"ts_field={profile.ts_field or UNKNOWN}",
        f"platform_detected_via={profile.platform_detect_method}",
        f"file_mtime_utc={profile.mtime_utc} (unverified proxy, not received_at_utc)",
    ]
    if profile.source_field_downgraded:
        notes_bits.append(
            f"source_field='{profile.source_field}' ignored for provenance: only ever holds a "
            "platform-name value, not a real source id"
        )
    if profile.parse_error_lines:
        notes_bits.append(f"unparseable_records={profile.parse_error_lines}")
    if profile.decode_replacement_chars:
        notes_bits.append(f"utf8_decode_replacement_chars={profile.decode_replacement_chars}")
    if profile.ts_no_tz_marker_n:
        notes_bits.append(
            f"timestamps_without_explicit_timezone={profile.ts_no_tz_marker_n} "
            "(excluded from oldest/newest per plan section 5)"
        )
    if profile.notes_registry_match:
        notes_bits.append(f"query_ids_all_found_in_local_registry(v{registry_version})")
    if profile.contains_secrets:
        notes_bits.append(f"secret_scan_hits={','.join(profile.secret_hit_types)}")
    else:
        notes_bits.append(f"secret_scan=clean(header+first {SECRET_SCAN_ROW_SAMPLE} rows)")

    collector_version = (
        ";".join(sorted(profile.collector_version_values))
        if profile.collector_version_values else UNKNOWN
    )

    return {
        "handoff_id": handoff_id,
        "platform": platform,
        "provided_by": UNKNOWN,
        "received_at_utc": UNKNOWN,
        "original_file_name": profile.path.name,
        "relative_path": profile.relative_path,
        "file_role": "raw",
        "file_format": profile.file_format,
        "file_size_bytes": str(profile.file_size_bytes),
        "sha256": profile.sha256,
        "source_schema_version": "raw_schema_v03" if profile.schema_matches_raw_schema_v03 else UNKNOWN,
        "source_query_registry_version": (registry_version if profile.notes_registry_match else UNKNOWN),
        "collector_name": UNKNOWN,
        "collector_version": collector_version,
        "run_log_available": "true" if run_log_available else UNKNOWN,
        "config_available": "true" if config_available else UNKNOWN,
        "contains_secrets": "true" if profile.contains_secrets else "false",
        "notes": "; ".join(notes_bits),
    }


def update_manifest(manifest_path: Path, new_rows: list[dict], dry_run: bool) -> list[dict]:
    fieldnames, existing_rows = read_csv_rows(manifest_path)
    if fieldnames != MANIFEST_COLUMNS:
        print(
            f"WARNING: {manifest_path} header does not exactly match the expected "
            f"template columns; appending using the file's own header order.",
            file=sys.stderr,
        )
        fieldnames = fieldnames or MANIFEST_COLUMNS

    already = {
        (r.get("platform", "").strip(), r.get("relative_path", "").strip())
        for r in existing_rows
    }
    id_gen = next_handoff_id(existing_rows)

    to_append = []
    skipped_duplicates = []
    for row in new_rows:
        key = (row["platform"], row["relative_path"])
        if key in already:
            skipped_duplicates.append(row["relative_path"])
            continue
        row["handoff_id"] = next(id_gen)
        to_append.append(row)
        already.add(key)

    if skipped_duplicates:
        print(
            f"manifest: {len(skipped_duplicates)} file(s) already recorded, not re-appended: "
            + ", ".join(skipped_duplicates)
        )

    if to_append and not dry_run:
        with manifest_path.open("a", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            for row in to_append:
                writer.writerow({k: row.get(k, "") for k in fieldnames})

    print(f"manifest: {len(to_append)} new row(s) {'would be ' if dry_run else ''}appended to {manifest_path}")
    return to_append


def aggregate_platform(profiles: list[FileProfile]) -> dict:
    raw_n = sum(p.raw_n for p in profiles)
    source_files = ";".join(p.relative_path for p in profiles) if profiles else ""

    def agg_int(attr: str) -> str:
        vals = [getattr(p, attr) for p in profiles]
        if not profiles or any(v is None for v in vals):
            return UNKNOWN
        return str(sum(vals))

    missing_id_n = agg_int("missing_id_n")
    missing_ts_n = agg_int("missing_ts_n")
    parseable_n = agg_int("parseable_n")

    missing_text_n = str(sum(p.missing_text_n for p in profiles)) if profiles else "0"

    # global id uniqueness/duplicates across all included files combined
    if profiles and all(p.id_field is not None for p in profiles):
        all_ids = [v for p in profiles for v in p.all_id_values]
        unique_id_n = len(set(all_ids))
        duplicate_id_n = str(len(all_ids) - unique_id_n)
        unique_id_n = str(unique_id_n)
    else:
        unique_id_n = UNKNOWN
        duplicate_id_n = UNKNOWN

    oldest = min((p.oldest_ts for p in profiles if p.oldest_ts), default=None)
    newest = max((p.newest_ts for p in profiles if p.newest_ts), default=None)
    oldest_s = oldest.strftime("%Y-%m-%dT%H:%M:%SZ") if oldest else UNKNOWN
    newest_s = newest.strftime("%Y-%m-%dT%H:%M:%SZ") if newest else UNKNOWN

    all_dates: set = set()
    all_weeks: set = set()
    for p in profiles:
        all_dates |= p.dates_with_data
        all_weeks |= p.weeks_with_data
    days_with_data = str(len(all_dates)) if profiles else "0"
    weeks_with_data = str(len(all_weeks)) if profiles else "0"

    if profiles and all(p.query_field is not None for p in profiles):
        known = sum(p.query_known_n or 0 for p in profiles)
        query_known_pct = f"{round(100 * known / raw_n, 1)}" if raw_n else UNKNOWN
    else:
        query_known_pct = UNKNOWN

    if profiles and all(p.source_known_n is not None for p in profiles):
        known = sum(p.source_known_n or 0 for p in profiles)
        source_known_pct = f"{round(100 * known / raw_n, 1)}" if raw_n else UNKNOWN
    else:
        source_known_pct = UNKNOWN

    notes_bits = []
    if not profiles:
        notes_bits.append("no raw content files found under data/raw/ for this platform as of this scan")
    if len(profiles) > 1:
        notes_bits.append(
            f"{len(profiles)} raw files aggregated (sum may double-count overlapping/backup "
            "snapshots -- see manifest for per-file detail, not deduplicated by content)"
        )
    notes_bits.append("quality_grade left as 'pending': section 7 grading needs manual provenance review")

    return {
        "platform": None,  # filled by caller
        "source_file": source_files,
        "quality_grade": "pending",
        "raw_n": str(raw_n),
        "parseable_n": parseable_n,
        "unique_platform_id_n": unique_id_n,
        "missing_id_n": missing_id_n,
        "missing_timestamp_n": missing_ts_n,
        "missing_text_n": missing_text_n,
        "oldest_created_at_utc": oldest_s,
        "newest_created_at_utc": newest_s,
        "days_with_data": days_with_data,
        "weeks_with_data": weeks_with_data,
        "duplicate_id_n": duplicate_id_n,
        "query_known_pct": query_known_pct,
        "source_known_pct": source_known_pct,
        "notes": "; ".join(notes_bits),
    }


def update_coverage(coverage_path: Path, platform: str, agg: dict, dry_run: bool, regrade: bool = False) -> None:
    """Refreshes the numeric profile columns for `platform`'s row.

    quality_grade (docs/checklist.md item 8) is deliberately NOT overwritten
    by this function's own aggregate_platform() output (which always says
    "pending" -- it never computes a grade) when the row already carries a
    real grade from a separate, reasoned pass (src/intake/quality_grade.py,
    run manually/reviewed by the team). Without this, every re-run of
    profile_platform.py (e.g. after new raw files land) would silently reset
    a team-reviewed A-D grade back to "pending". Pass regrade=True to allow
    it (the caller is then responsible for re-running quality_grade.py
    afterward -- see --regrade)."""
    fieldnames, rows = read_csv_rows(coverage_path)
    if fieldnames != COVERAGE_COLUMNS:
        print(
            f"WARNING: {coverage_path} header does not exactly match the expected "
            f"template columns; updating using the file's own header order.",
            file=sys.stderr,
        )
        fieldnames = fieldnames or COVERAGE_COLUMNS

    agg = dict(agg)
    agg["platform"] = platform
    found = False
    for row in rows:
        if row.get("platform", "").strip() == platform:
            existing_grade = (row.get("quality_grade") or "").strip()
            existing_notes = row.get("notes") or ""
            row.update({k: agg.get(k, row.get(k, "")) for k in fieldnames})
            if not regrade and existing_grade and existing_grade != "pending":
                row["quality_grade"] = existing_grade
                grade_note = next(
                    (part for part in existing_notes.split(" || ") if part.startswith("quality_grade.py:")),
                    None,
                )
                if grade_note:
                    row["notes"] = f"{row['notes']} || {grade_note}" if row.get("notes") else grade_note
                print(
                    f"  preserved existing quality_grade={existing_grade!r} for platform={platform} "
                    "(pass --regrade to reset to 'pending' and re-run src/intake/quality_grade.py)."
                )
            found = True
            break
    if not found:
        rows.append({k: agg.get(k, "") for k in fieldnames})

    if not dry_run:
        with coverage_path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow({k: row.get(k, "") for k in fieldnames})

    print(f"coverage: platform={platform} row {'would be ' if dry_run else ''}updated in {coverage_path}")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--platform", required=True, choices=PLATFORMS)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--coverage", type=Path, default=DEFAULT_COVERAGE)
    parser.add_argument("--dry-run", action="store_true", help="Print what would change; write nothing.")
    parser.add_argument(
        "--regrade", action="store_true",
        help="Allow this run to reset an existing quality_grade back to 'pending' instead of "
             "preserving it (see update_coverage()). Re-run src/intake/quality_grade.py afterward.",
    )
    args = parser.parse_args(argv)

    candidates = discover_candidate_files(args.raw_dir)
    print(f"scanning {args.raw_dir} : {len(candidates)} candidate file(s) with extension in {sorted(RECORD_EXTENSIONS)}")

    raw_schema_columns = load_raw_schema_columns()
    registry_query_ids, registry_version = load_query_registry()

    profiles: list[FileProfile] = []
    skips: list[SkipInfo] = []
    for path in candidates:
        result = profile_file(path, args.platform, raw_schema_columns, registry_query_ids, registry_version)
        if isinstance(result, SkipInfo):
            skips.append(result)
        else:
            profiles.append(result)

    print(f"\nmatched {len(profiles)} raw content file(s) for platform={args.platform}:")
    for p in profiles:
        oldest = p.oldest_ts.strftime("%Y-%m-%dT%H:%M:%SZ") if p.oldest_ts else UNKNOWN
        newest = p.newest_ts.strftime("%Y-%m-%dT%H:%M:%SZ") if p.newest_ts else UNKNOWN
        print(
            f"  - {p.relative_path}\n"
            f"      raw_n={p.raw_n}  oldest={oldest}  newest={newest}  "
            f"missing_id={p.missing_id_n if p.missing_id_n is not None else UNKNOWN}  "
            f"missing_ts={p.missing_ts_n if p.missing_ts_n is not None else UNKNOWN}  "
            f"missing_text={p.missing_text_n}  sha256={p.sha256[:12]}..."
        )

    if skips:
        print(f"\nskipped {len(skips)} candidate file(s) (not matched as {args.platform} raw content):")
        for s in skips:
            try:
                rel = s.path.resolve().relative_to(REPO_ROOT).as_posix()
            except ValueError:
                rel = str(s.path)
            print(f"  - {rel}: {s.reason}")

    if not profiles:
        print(
            f"\nNo raw content files found for platform={args.platform} under {args.raw_dir}. "
            "Manifest will get no new rows; coverage row will be updated to raw_n=0."
        )

    parent_dirs = {p.path.parent for p in profiles}
    run_log_available, config_available = companion_files_available(parent_dirs) if parent_dirs else (False, False)

    manifest_rows = [
        build_manifest_row(p, args.platform, run_log_available, config_available, registry_version, handoff_id="PENDING")
        for p in profiles
    ]
    update_manifest(args.manifest, manifest_rows, args.dry_run)

    agg = aggregate_platform(profiles)
    update_coverage(args.coverage, args.platform, agg, args.dry_run, regrade=args.regrade)

    print(
        "\nNothing under data/raw/ was modified, renamed, or deleted by this script "
        "(plan section 1, rule 1)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
