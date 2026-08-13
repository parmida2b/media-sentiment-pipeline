# Frozen original-data layout

This directory contains read-only copies of the delivered source files. The
source files were copied, not moved, and must not be cleaned or overwritten in
place. Cleaning and harmonization belong in derived data layers.

## X

| Subdirectory | Contents | Classification |
|---|---|---|
| `x/records/` | `x_raw.csv` | Primary record export |
| `x/logs/` | `x_runs.csv`, `x_subruns.csv` | Collection run logs |
| `x/database/` | `twitter_data_v4.db` | Collection database and provenance source; not a second raw-record file to concatenate |
| `x/exports/` | `X_Twitter_Collection (1).xlsx` | Human-readable export of the collected data; not an independent dataset |
| `x/temporary/` | `~$X_Twitter_Collection (1).xlsx` | Office lock/temporary file; excluded from analysis |

## Reddit

| Subdirectory | Contents | Classification |
|---|---|---|
| `reddit/records/raw_reddit_json/` | One public JSON response file per discovered parent submission (3571 files) | Closest available original platform-response records |
| `reddit/logs/` | `raw_json_fetch_log.csv`, `parse_errors.csv` | Fetch and parse logs |
| `reddit/exports/` | `reddit_raw_schema.csv`, `interactions.csv`, `posts.csv`, `users.csv`, `master_parent_posts_dedup.csv` | Parsed or collection-stage exports; they are not concatenated with the JSON responses as additional observations |
| `reddit/code/` | `parse_reddit_json_raw_schema_v02.ipynb` | Historical parsing code; not data |

## YouTube

No `data/raw/iran_us_war` directory or YouTube source files were present in the
repository or the inspected workspace when this freeze was created. The
`youtube/{records,logs,exports,backups}` structure is reserved for the missing
handoff. No placeholder dataset was generated.

`youtube_runs.csv`, when supplied, belongs in `youtube/logs/`, not in
`youtube/records/`. Any `archive_before_*` directory belongs in
`youtube/backups/` and must be documented as a historical backup rather than
treated as the current raw dataset. No such archive was found in the inspected
workspace.

The file `youtube_comments.jsonl` found at the project parent directory
(`../youtube_comments.jsonl`, 1668 lines, 1.0 MB, last modified 2026-07-25)
was not included in this freeze because its provenance, collection run, and
query context are undocumented. It may be an early or test collection. It must
be reviewed against the collection manifest before being placed under
`youtube/records/`.

## Use rule

- Do not write to `data/raw_original/` from collectors, preprocessing, or
  notebooks.
- Use a single declared record source per platform and retain the other files
  for provenance, audit, or cross-checking.
- Do not infer or fill missing provenance values.
- File hashes and handoff metadata should be recorded in the project handoff
  manifest before analysis.
