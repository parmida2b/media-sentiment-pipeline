"""
duplicate_analysis.py -- docs/checklist.md, Phase 5, item 12 (Duplicate
check).

apply_eligibility.py's stage_dedup() already handles case 1 (Exact-ID
duplicate -- same platform+platform_content_id, oldest record kept, the
rest routed to quarantine with primary_exclusion_reason=duplicate_exact_id).
This script covers the two remaining checklist cases on the SURVIVING,
already-Exact-ID-deduped content (opinion_main/opinion_limited/
opinion_untimed/context_only):

  case 2: identical text_normalized, different platform_content_id
          -> kept, flagged (duplicate_text_diff_id + duplicate_text_group_id)
  case 3: near-duplicate text (not byte-identical, but highly similar)
          -> kept, flagged with a cluster id (near_duplicate_cluster_id),
             via MinHash/LSH (datasketch) on 3-word shingles of
             text_normalized, scoped per (platform, project_week) cell for
             tractability. Untimed rows (opinion_untimed, project_week is
             null/"OUT") are excluded from near-duplicate clustering -- only
             6 rows as of 2026-08-14, never going to form a meaningful week
             cell.

Depends on src/preprocessing/normalize_text.py having already run (needs
text_normalized). Adds columns in place to the same four parquet files (row
count never changes); writes data/audits/duplicate_analysis_report.md with
the checklist item 12 statistics (exact-duplicate rate, unique-text rate,
near-duplicate cluster count/largest cluster, by platform/week).

Usage:
    python src/preprocessing/duplicate_analysis.py
    python src/preprocessing/duplicate_analysis.py --dry-run
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd
from datasketch import MinHash, MinHashLSH

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent.parent
INTERIM_DIR = ROOT / "data" / "interim"
AUDITS_DIR = ROOT / "data" / "audits"

KEPT_TARGETS = ["opinion_main", "opinion_limited", "opinion_untimed", "context_only"]
NEAR_DUP_ELIGIBLE_TARGETS = ["opinion_main", "opinion_limited", "context_only"]  # excludes opinion_untimed (no usable project_week)

MIN_TEXT_LEN_FOR_DUP_CHECK = 10  # shorter text ("lol", "yes") matching by
# coincidence is not meaningful repost/duplicate evidence -- flagged
# separately in the report, not silently included or excluded.

SHINGLE_SIZE = 3
NUM_PERM = 64
LSH_THRESHOLD = 0.8


def _load_kept() -> pd.DataFrame:
    frames = []
    for target in KEPT_TARGETS:
        path = INTERIM_DIR / f"{target}.parquet"
        if not path.exists():
            print(f"skip {target}: {path} not found")
            continue
        df = pd.read_parquet(path, columns=["platform_content_id", "platform", "project_week", "text_normalized"])
        if not len(df):
            continue
        df = df.rename(columns={"platform_content_id": "content_id"})
        df["dataset_target"] = target
        frames.append(df)
    if not frames:
        raise SystemExit("No kept-target rows found -- run normalize_text.py (and apply_eligibility.py) first.")
    return pd.concat(frames, ignore_index=True)


def _text_key(text: str) -> str:
    return hashlib.sha1(text.strip().lower().encode("utf-8")).hexdigest()[:16]


def flag_exact_text_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """case 2: identical text_normalized, different content_id."""
    df = df.copy()
    eligible = df["text_normalized"].fillna("").str.len() >= MIN_TEXT_LEN_FOR_DUP_CHECK
    keys = df["text_normalized"].fillna("").map(_text_key)

    group_sizes: dict[str, int] = defaultdict(int)
    for k, elig in zip(keys, eligible):
        if elig:
            group_sizes[k] += 1

    df["duplicate_text_diff_id"] = [
        bool(elig and group_sizes.get(k, 0) > 1) for k, elig in zip(keys, eligible)
    ]
    df["duplicate_text_group_id"] = [
        (f"txt_{k}" if (elig and group_sizes.get(k, 0) > 1) else None)
        for k, elig in zip(keys, eligible)
    ]
    df["_dup_check_eligible"] = eligible
    return df


def _shingles(text: str, k: int = SHINGLE_SIZE) -> set[str]:
    words = text.lower().split()
    if len(words) < k:
        return {" ".join(words)} if words else set()
    return {" ".join(words[i:i + k]) for i in range(len(words) - k + 1)}


def _minhash_for(text: str) -> MinHash:
    m = MinHash(num_perm=NUM_PERM)
    for sh in _shingles(text):
        m.update(sh.encode("utf-8"))
    return m


class _UnionFind:
    def __init__(self):
        self.parent: dict[str, str] = {}

    def find(self, x: str) -> str:
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[ra] = rb


def cluster_near_duplicates(cell_df: pd.DataFrame, cell_key: str) -> dict[str, str]:
    """Returns {content_id: near_duplicate_cluster_id} for content_ids that
    belong to a cluster of size >= 2 within this (platform, project_week)
    cell. Rows below MIN_TEXT_LEN_FOR_DUP_CHECK are skipped (same rationale
    as flag_exact_text_duplicates)."""
    rows = [
        (cid, text) for cid, text in zip(cell_df["content_id"], cell_df["text_normalized"].fillna(""))
        if len(text) >= MIN_TEXT_LEN_FOR_DUP_CHECK
    ]
    if len(rows) < 2:
        return {}

    lsh = MinHashLSH(threshold=LSH_THRESHOLD, num_perm=NUM_PERM)
    minhashes: dict[str, MinHash] = {}
    for cid, text in rows:
        mh = _minhash_for(text)
        minhashes[cid] = mh
        lsh.insert(cid, mh)

    uf = _UnionFind()
    for cid, mh in minhashes.items():
        for match in lsh.query(mh):
            if match != cid:
                uf.union(cid, match)

    cluster_members: dict[str, list[str]] = defaultdict(list)
    for cid in minhashes:
        cluster_members[uf.find(cid)].append(cid)

    result: dict[str, str] = {}
    cluster_n = 0
    for members in cluster_members.values():
        if len(members) < 2:
            continue
        cluster_n += 1
        cluster_id = f"nd_{cell_key}_{cluster_n:03d}"
        for cid in members:
            result[cid] = cluster_id
    return result


def run(dry_run: bool) -> None:
    df = _load_kept()
    print(f"Loaded {len(df):,} kept rows (opinion_main/opinion_limited/opinion_untimed/context_only).")

    df = flag_exact_text_duplicates(df)
    n_exact_text_dup = int(df["duplicate_text_diff_id"].sum())
    n_too_short = int((~df["_dup_check_eligible"]).sum())
    print(f"case 2 (identical text, different id): {n_exact_text_dup:,} row(s) flagged "
          f"({n_too_short:,} row(s) below MIN_TEXT_LEN_FOR_DUP_CHECK={MIN_TEXT_LEN_FOR_DUP_CHECK} skipped).")

    near_dup_map: dict[str, str] = {}
    cell_stats = []
    near_df = df[df["dataset_target"].isin(NEAR_DUP_ELIGIBLE_TARGETS) & df["project_week"].notna() & (df["project_week"] != "OUT")]
    for (platform, week), cell in near_df.groupby(["platform", "project_week"]):
        cell_key = f"{platform}_{week}"
        mapping = cluster_near_duplicates(cell, cell_key)
        near_dup_map.update(mapping)
        n_clustered = len(mapping)
        n_clusters = len(set(mapping.values()))
        cell_stats.append({
            "platform": platform, "project_week": week, "n": len(cell),
            "near_dup_clusters": n_clusters, "near_dup_rows": n_clustered,
        })

    df["near_duplicate_cluster_id"] = df["content_id"].map(near_dup_map)
    n_near_dup_rows = int(df["near_duplicate_cluster_id"].notna().sum())
    n_near_dup_clusters = df["near_duplicate_cluster_id"].nunique()
    largest_cluster = (
        df["near_duplicate_cluster_id"].value_counts().max() if n_near_dup_clusters else 0
    )
    print(f"case 3 (near-duplicate): {n_near_dup_rows:,} row(s) in {n_near_dup_clusters:,} cluster(s), "
          f"largest cluster={largest_cluster}.")

    df = df.drop(columns=["_dup_check_eligible"])

    # write columns back into each source parquet (row count unchanged)
    for target in KEPT_TARGETS:
        path = INTERIM_DIR / f"{target}.parquet"
        if not path.exists():
            continue
        base = pd.read_parquet(path)
        n_before = len(base)
        merge_cols = df[df["dataset_target"] == target][
            ["content_id", "duplicate_text_diff_id", "duplicate_text_group_id", "near_duplicate_cluster_id"]
        ].rename(columns={"content_id": "platform_content_id"})
        merged = base.drop(
            columns=[c for c in ("duplicate_text_diff_id", "duplicate_text_group_id", "near_duplicate_cluster_id") if c in base.columns]
        ).merge(merge_cols, on="platform_content_id", how="left")
        merged["duplicate_text_diff_id"] = merged["duplicate_text_diff_id"].fillna(False)
        assert len(merged) == n_before, f"row count changed for {target}: {n_before} -> {len(merged)}"
        print(f"  {target:16s} rows={n_before:8d}  duplicate_text_diff_id={int(merged['duplicate_text_diff_id'].sum()):6d}  "
              f"near_dup={int(merged['near_duplicate_cluster_id'].notna().sum()):6d}")
        if not dry_run:
            merged.to_parquet(path, index=False)

    # ---- report ----
    exact_id_dup_n = _exact_id_duplicate_count()
    total_kept = len(df)
    lines = [
        "# Duplicate Analysis Report",
        "",
        f"تاریخ: 2026-08-14 -- منبع: src/preprocessing/duplicate_analysis.py "
        f"(checklist.md فاز پنجم، آیتم ۱۲)",
        "",
        "## آمار کلی",
        "",
        f"- تعداد Exact-ID duplicate (حذف‌شده در apply_eligibility.py's stage_dedup، قبل از این مرحله): "
        f"{exact_id_dup_n:,}",
        f"- تعداد رکورد کل (kept: opinion_main+opinion_limited+opinion_untimed+context_only): {total_kept:,}",
        f"- متن یکسان با ID متفاوت (case 2): {n_exact_text_dup:,} رکورد "
        f"({100 * n_exact_text_dup / total_kept:.2f}%)",
        f"- Unique text rate: {100 * (total_kept - n_exact_text_dup) / total_kept:.2f}%",
        f"- Near-duplicate (case 3): {n_near_dup_rows:,} رکورد در {n_near_dup_clusters:,} Cluster "
        f"(بزرگ‌ترین Cluster: {largest_cluster} رکورد)",
        f"- رکوردهای زیر آستانه‌ی طول متن (MIN_TEXT_LEN_FOR_DUP_CHECK={MIN_TEXT_LEN_FOR_DUP_CHECK}، "
        "بررسی Duplicate روی آن‌ها انجام نشد چون تطابق تصادفی متن کوتاه معنادار نیست): "
        f"{n_too_short:,}",
        "",
        "## تفکیک هفته/پلتفرم (Near-duplicate)",
        "",
        "| platform | project_week | n | near_dup_clusters | near_dup_rows |",
        "|---|---|---:|---:|---:|",
    ]
    for row in sorted(cell_stats, key=lambda r: (r["platform"], r["project_week"])):
        lines.append(f"| {row['platform']} | {row['project_week']} | {row['n']} | {row['near_dup_clusters']} | {row['near_dup_rows']} |")

    lines += [
        "",
        "## روش",
        "",
        f"- Case 2 (متن یکسان، ID متفاوت): هش SHA-1 روی `text_normalized.strip().lower()`.",
        f"- Case 3 (Near-duplicate): MinHash (num_perm={NUM_PERM}) روی Shingleهای {SHINGLE_SIZE}-کلمه‌ای "
        f"`text_normalized.lower()`، LSH با threshold={LSH_THRESHOLD} (تخمین Jaccard similarity)، "
        "به‌ازای هر سلول (platform, project_week) جداگانه (برای مقیاس‌پذیری روی ~۲۳۳K رکورد؛ "
        "opinion_untimed چون project_week ندارد از این تحلیل کنار گذاشته شده، فقط ۶ رکورد).",
    ]

    if not dry_run:
        AUDITS_DIR.mkdir(parents=True, exist_ok=True)
        report_path = AUDITS_DIR / "duplicate_analysis_report.md"
        report_path.write_text("\n".join(lines), encoding="utf-8")
        print(f"\nWrote {report_path}")
    else:
        print("\n--dry-run: nothing written.")


def _exact_id_duplicate_count() -> int:
    audit_path = ROOT / "data" / "audits" / "eligibility_audit.parquet"
    if not audit_path.exists():
        return -1
    audit = pd.read_parquet(audit_path, columns=["primary_exclusion_reason"])
    return int((audit["primary_exclusion_reason"] == "duplicate_exact_id").sum())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
