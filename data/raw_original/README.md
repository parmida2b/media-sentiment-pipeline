# Frozen original-data layout

This directory contains **read-only copies** of the delivered/collected raw
files found under `data/raw/` at freeze time (2026-08-14). Every file here
was **copied, not moved** — the source files under `data/raw/` are untouched
and remain the working copies that collectors/bridges keep appending to.
Cleaning, harmonization, and any further processing happen on derived
copies (`data/raw_harmonized/`, `data/interim/`, …), never in place here.

This freeze supersedes the previous version of this README, which was
written when `data/raw/iran_us_war/` (YouTube's delivery) did not yet exist
in the inspected workspace and described a different X/Reddit file set than
what is currently under `data/raw/`. See "What changed since the last
freeze" below.

`data/raw_original/{x,reddit,youtube}/` is gitignored except for this
README (see `.gitignore`) — the copied files stay local only.

## How "raw" was decided (not guessed)

`data/raw/reddit/` and `data/raw/x/` look like raw-data folders by name, but
they are not: per their producing scripts' own docstrings
(`src/ingestion/reddit_to_record.py`, `src/ingestion/x_to_record.py`,
`src/ingestion/handoff_csv_to_record.py`), `reddit_comments_v1.jsonl`,
`reddit_raw_export.csv`, `x_comments_v1.jsonl`, and `x_raw_export.csv` are
all **generated output** of a schema-bridging step — the shared `Record`
JSONL/CSV pair every collector bridge produces, already PII-hashed and
schema-mapped. They are **not frozen here**; they stay where they are as a
derived layer, one step downstream of the true raw handoff.

The actual raw inputs those bridge scripts read (and that this freeze
copies) are declared in the same docstrings:

```
python src/ingestion/handoff_csv_to_record.py --input data/raw/iran_us_war/X_Scraper_v4_7_Target20K_Current.xlsx --sheet Raw_Tweets --platform x
python src/ingestion/handoff_csv_to_record.py --input data/raw/iran_us_war/reddit_raw_schema.csv --platform reddit
```

For YouTube, `youtube_extract.py` writes its primary output directly to
`data/raw/{topic_id}/youtube_comments_v2.jsonl` /
`youtube_raw_export.csv` and its own comments (lines ~578–585, ~754–757)
explicitly call this pair the project's `raw_original` role — no separate
handoff/bridge script exists for YouTube because the collector already
writes there.

## X

| Subdirectory | Contents | Classification |
|---|---|---|
| `x/records/` | `X_Scraper_v4_7_Target20K_Current.xlsx` (copy of `data/raw/iran_us_war/...`, 9,565,277 bytes, SHA-256 `e1f0903b9e405986b811185d982720d8bb4e7cad72ca0583642e313f691709d6`) | Delivered raw handoff — the "Raw_Tweets" sheet is the input `handoff_csv_to_record.py` bridges into `data/raw/x/x_comments_v1.jsonl`/`x_raw_export.csv` |

No native `x_scraper.py` SQLite database or its own `exports/x_raw.csv` was
found under `data/raw/` (only the xlsx handoff is present there). If that
database still exists on the collector's machine, it should be added under
`x/database/` in a future pass — not fabricated here.

## Reddit

| Subdirectory | Contents | Classification |
|---|---|---|
| `reddit/records/` | `reddit_raw_schema.csv` (copy of `data/raw/iran_us_war/...`, 119,493,485 bytes, SHA-256 `4044edaf9054b3008a1e364e5f1cf963961e2a7f1360cad5a888fb19dfc19a64`) | Delivered raw handoff — already shaped like `config/raw_schema_columns.py` per `handoff_csv_to_record.py`'s docstring; this is the input the bridge reads, not its output |

No per-submission `raw_reddit_json/` response files (referenced by an
earlier freeze attempt) or `reddit_raw_json_pipeline.py` fetch/parse logs
were found under `data/raw/` — only the already-mapped `reddit_raw_schema.csv`
handoff is present there today. **This is coarser provenance than the
per-response JSON would give** (one CSV row per record vs. one platform
response file per submission) and should be flagged in the coverage/
provenance grade (checklist §8) rather than assumed equivalent.

## YouTube

`data/raw/iran_us_war/` did not exist when the previous version of this
README was written; it now contains the YouTube delivery plus the two
stray X/Reddit handoff files documented above.

| Subdirectory | Contents | Classification |
|---|---|---|
| `youtube/records/` | `youtube_comments_v2.jsonl` (145,206,765 bytes, SHA-256 `162fff7f3e5173d96c2fc5019f74c5db064348fe07076182c363c2781a2679e9`), `youtube_raw_export.csv` (78,291,708 bytes, SHA-256 `da4e7c4d7b795331171d7a0b1894b5085e9f7d94b36c4f824c5405f4710b8660`) | Current primary raw records — the collector's own `OUTPUT_JSONL_PATH`/`OUTPUT_CSV_PATH`, appended-to in place, never rewritten (`youtube_extract.py` calls this its `raw_original` output) |
| `youtube/records_needs_review/` | `youtube_comments_1404-12-09_to_ongoing.jsonl` (45,219,060 bytes) | **Flagged, not silently merged.** Same first record as `youtube_comments_v2.jsonl` but from an older schema (unredacted `author_display_name`, no `author_hash`) and a different, smaller size — looks like a superseded/earlier-round file under the pre-`_v2` naming convention, not an independent dataset. Must be checked against the collection manifest / run log before being treated as additional records, per checklist §1 ("different exports are not concatenated without review") |
| `youtube/logs/` | `youtube_runs.csv` (collection run log, one row per run×week bucket — **not raw records**), `youtube_skipped_videos.csv` (Quota-Triage pre-filter skip log), `checkpoint.json` (collector resumability state), `resolved_channels.json` (channel-name → channel-ID resolution cache) | Collector bookkeeping, not content records |
| `youtube/derived_cache/` | `video_geo_metadata.jsonl` | Tier-0 geo/relevance enrichment cache written by `geo_tagger.py`, keyed by `video_id` and joined in at analysis time — not a raw content record itself |
| `youtube/backups/backup_2026-07-25/` | `checkpoint.json`, `video_geo_metadata.jsonl`, `youtube_comments_1404-12-09_to_1405-05-03.jsonl` | Historical backup, pre-dates `iran_us_war/` topic-scoping. **Not current raw** |
| `youtube/backups/archive_before_reset_2026-07-26/` | `checkpoint.json`, `resolved_channels.json`, `youtube_comments.jsonl`, `youtube_comments_1404-12-09_to_1405-05-02.jsonl`, `youtube_comments_1404-12-09_to_1405-05-03.jsonl` (0 bytes), `youtube_comments_1404-12-09_to_1405-05-04.jsonl` (0 bytes) | Snapshot taken before a collector reset on 2026-07-26. **Not current raw** — two files are empty placeholders from that reset, not missing data |
| `youtube/backups/archive_before_author_hash_v05_backfill_2026-08-12/` | `youtube_comments_v2.jsonl`, `youtube_raw_export.csv` (same byte sizes as the current `records/` pair) | Pre-backfill snapshot of the same two files, taken before the 2026-08-12 `author_hash_v05` backfill rewrote them in place. **Not current raw** — kept only so the backfill is auditable/reversible |

## What changed since the last freeze

* YouTube's delivery (`data/raw/iran_us_war/`) now exists and is frozen for
  the first time in this pass.
* The X and Reddit files this freeze copies (`X_Scraper_v4_7_Target20K_Current.xlsx`,
  `reddit_raw_schema.csv`) are different files from what the previous
  README described (`X_Twitter_Collection (1).xlsx`, a `twitter_data_v4.db`
  database, a `raw_reddit_json/` folder of 3,571 per-submission JSON files).
  None of those previously-described files were found under `data/raw/` in
  this pass — only the xlsx/CSV handoffs above were present. This may mean
  they live elsewhere (a collector machine, `data_backup/` — see below) and
  were never copied into this repo's `data/raw/`, or that the handoff shape
  changed between freezes. Not resolved by inference here.

## Note on `data_backup/`

A separate, gitignored `data_backup/` directory exists at the project root
(sibling of `data/`) and appears to hold a fuller/older snapshot, including
a `raw_reddit_json/` folder and a `submissions_from_raw_json.csv` under
`data_backup/interim/reddit/raw_json_audit/` that would match the previous
README's description. It was **not used as a source for this freeze** —
the task scope was "the current `data/raw/` folder," `data_backup/` is not
tracked by git, and its relationship to the current `data/raw/` delivery
(same collection round vs. an older one) has not been verified. Worth a
follow-up decision-log entry if it turns out to be the true source of the
per-submission JSON responses.

## Use rule

* Do not write to `data/raw_original/` from collectors, preprocessing, or
  notebooks. Verified: `grep -rn "raw_original" src/` only matches
  docstring/comment references to the *concept* (`youtube_extract.py`
  lines 580, 757) — no script opens a path under `data/raw_original/` for
  writing.
* Use a single declared record source per platform
  (`x/records/`, `reddit/records/`, `youtube/records/`) and retain the
  other files for provenance, audit, or cross-checking only.
* `youtube/records_needs_review/` is explicitly excluded from that single
  source until reviewed — do not concatenate it with `youtube/records/`.
* Do not infer or fill missing provenance values (e.g. the missing native
  X database, the missing per-submission Reddit JSON — see above).
* File hashes recorded above should be carried into the project handoff
  manifest (checklist §2, `data_handoff_manifest.csv`) before analysis;
  that manifest is a separate, not-yet-built deliverable.

## Financial data

`docs/checklist.md`'s proposed `data/raw_original/financial/` freeze is out
of scope for this pass (this pass covers X/Reddit/YouTube only) and no such
directory exists yet. The financial workstream already has its own frozen
inputs under `data/interim/financial/frozen_inputs/` and audit trail under
`outputs/audits/financial/` — see those directly rather than assuming a
`raw_original/financial/` layout that hasn't been built.
