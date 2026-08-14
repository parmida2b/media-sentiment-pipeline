"""
quality_grade.py — docs/checklist.md فاز سوم، آیتم ۸: درجه‌بندی A-D قابلیت‌استفاده.

اسکریپت‌ها (profile_platform.py) و انسان (تحلیل دستی موجود در
docs/collection_coverage.csv) هر دو تا امروز برای این آیتم "pending" یا یک
قضاوت مکتوب‌شده‌ی توضیح‌دار (بدون قاعده‌ی رسمی) تولید کرده بودند. این ماژول
یک قاعده‌ی صریح و مستدل کدگذاری می‌کند تا (۱) قابل تکرار/rerun باشد، (۲) هر
تغییر داده (fix شدن یک باگ، تکمیل یک run log) خودکار در گرید منعکس شود، (۳)
نتیجه با قضاوت دستی موجود (هر سه پلتفرم B) مقایسه و اختلاف‌ها صریح گزارش شود
— نه این‌که قضاوت قبلی کورکورانه بازتولید یا کورکورانه دور ریخته شود.

قاعده (بر پایه‌ی docs/eligibility_rules_v03.md's provenance_quality tiers +
تعریف دقیق خودِ چک‌لیست برای هر درجه: A=«همه تحلیل‌ها مجاز»، B=«تحلیل اصلی
با گزارش Provenance ناقص»، C=«تحلیل توصیفی یا محدود»، D=«قرنطینه». نکته‌ی
کلیدی: چیزی که فقط "گزارش Provenance را ناقص می‌کند" (Run Log مستقل نبودن،
PII خام که باید قبل از انتشار حذف شود، Duplicate که توسط Exact-ID dedup
پایین‌دستی به‌طور verify‌شده حل می‌شود) به B می‌رود، نه C — C فقط برای
چیزی که واقعاً دامنه‌ی تحلیل‌های مجاز را محدود می‌کند (حجم زیاد متن/Timestamp
غیرقابل‌استفاده) رزرو شده):

  D (قرنطینه)   اگر: raw_n صفر یا فایل‌ها غیرقابل‌خواندن، یا
                 missing_id_pct > 20% (شناسه غیرقابل‌اعتماد -> Provenance
                 اصلاً قابل بازسازی نیست).
  C (محدود)     اگر: missing_text_pct > 20% یا missing_timestamp_pct > 20%
                 (حجمی که واقعاً تحلیل روند زمانی/متن را محدود می‌کند).
  B (تحلیل اصلی با Provenance ناقص)  اگر: هیچ‌کدام از شرایط C/D برقرار
                 نیست، اما حداقل یکی از این‌ها هست: هر مقدار Missingness
                 غیرصفر در متن/شناسه/Timestamp، عدم وجود Run Log مستقل
                 (KNOWN_NO_RUN_LOG_PLATFORMS)، duplicate_id_pct غیرصفرِ
                 شناخته‌شده (حتی اگر توسط dedup پایین‌دستی حل شود)، یا PII
                 خام مستند و بدون Remediation.
  A (همه تحلیل‌ها مجاز)  فقط اگر هیچ‌کدام از موارد بالا صادق نباشد — یعنی
                 Missingness=۰، Run Log کامل، بدون PII خام مستند، بدون
                 Duplicate شناخته‌شده.

ورودی: همان ردیف‌های docs/collection_coverage.csv (خروجی profile_platform.py's
aggregate_platform(), با یک ستون افزوده‌ی اختیاری duplicate_id_pct/pii_flag که
دستی یا از یادداشت‌های موجود خوانده می‌شود چون profile_platform.py این دو را
مستقیماً حساب نمی‌کند).

Usage:
    python src/intake/quality_grade.py           # چاپ گرید هر پلتفرم + دلیل
    python src/intake/quality_grade.py --apply    # docs/collection_coverage.csv را با گرید/دلیل جدید به‌روزرسانی می‌کند
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")  # Persian reasons/notes below

REPO_ROOT = Path(__file__).resolve().parents[2]
COVERAGE_PATH = REPO_ROOT / "docs" / "collection_coverage.csv"

# docs/decision_log.md 2026-08-04/2026-08-07: HF007 (YouTube v1,
# youtube_comments_1404-12-09_to_ongoing.jsonl) still carries raw
# author_display_name; not remediated as of 2026-08-14. Kept as an explicit,
# reviewable list (not auto-detected -- a false negative here would silently
# certify a PII-bearing file as clean) rather than scanning file contents.
KNOWN_UNREMEDIATED_PII_PLATFORMS = {"youtube"}

# Manual duplicate_id_pct evidence already on disk (docs/collection_coverage.csv's
# notes column, YouTube row: "73837/157474=46.9% record-level duplicates
# between v1 and v2"). profile_platform.py does not compute a *record-level*
# (as opposed to unique-id) duplicate rate, so this is read from the existing
# analysis rather than re-derived here -- update this dict, with a decision_log
# reference, if that number changes. This is a B-tier signal, not C: it is a
# known, EXPECTED v1/v2 collector-overlap that apply_eligibility.py's
# Exact-ID dedup stage already resolves cleanly (verified reconciliation
# equation, docs/decision_log.md 2026-08-14) -- not an unexplained data
# defect that limits which analyses are valid.
KNOWN_DUPLICATE_ID_PCT = {"youtube": 46.9}

# docs/reference_file_determination.md: platforms with no independent,
# structured per-query Run Log on disk (Query/Sort/Cap/Pagination reconstructed
# from raw records or a delivered handoff's audit sheet, not a dedicated log
# the collector itself wrote). NOT the same question as "does every row have
# a query_id/source_id populated" (query_known_pct/source_known_pct) --
# Reddit's rows are 100% populated on both but there is still no separate
# run-log file, hence this explicit list rather than deriving it from those
# two percentages.
KNOWN_NO_RUN_LOG_PLATFORMS = {"reddit"}


@dataclass
class Grade:
    platform: str
    grade: str
    reasons: list[str]


def _pct(numerator_str: str, denominator_str: str) -> float | None:
    try:
        num, den = int(numerator_str), int(denominator_str)
    except (TypeError, ValueError):
        return None
    if den <= 0:
        return None
    return 100.0 * num / den


def grade_row(row: dict) -> Grade:
    platform = row["platform"]
    raw_n = row.get("raw_n", "0")
    reasons: list[str] = []

    if not raw_n or raw_n in ("0", "unknown"):
        return Grade(platform, "D", ["raw_n=0/unknown — هیچ محتوایی برای ارزیابی موجود نیست"])

    missing_id_pct = _pct(row.get("missing_id_n", ""), raw_n)
    missing_text_pct = _pct(row.get("missing_text_n", ""), raw_n)
    missing_ts_pct = _pct(row.get("missing_timestamp_n", ""), raw_n)
    duplicate_id_pct = KNOWN_DUPLICATE_ID_PCT.get(platform)
    no_run_log = platform in KNOWN_NO_RUN_LOG_PLATFORMS
    pii_unremediated = platform in KNOWN_UNREMEDIATED_PII_PLATFORMS

    # --- D ---
    if missing_id_pct is not None and missing_id_pct > 20:
        return Grade(platform, "D", [f"missing_id_pct={missing_id_pct:.1f}% > 20% — Provenance/شناسه قابل بازسازی نیست"])

    # --- C: فقط چیزی که واقعاً دامنه‌ی تحلیل مجاز را محدود می‌کند ---
    c_reasons = []
    if missing_text_pct is not None and missing_text_pct > 20:
        c_reasons.append(f"missing_text_pct={missing_text_pct:.1f}% > 20% — تحلیل متن روی بخش زیادی از داده ممکن نیست")
    if missing_ts_pct is not None and missing_ts_pct > 20:
        c_reasons.append(f"missing_timestamp_pct={missing_ts_pct:.1f}% > 20% — تحلیل روند زمانی روی بخش زیادی از داده ممکن نیست")
    if c_reasons:
        return Grade(platform, "C", c_reasons)

    # --- B vs A: چیزی که فقط گزارش Provenance را ناقص می‌کند، نه دامنه‌ی تحلیل را ---
    b_reasons = []
    if missing_text_pct is not None and missing_text_pct > 0:
        b_reasons.append(f"missing_text_pct={missing_text_pct:.2f}% (غیرصفر، زیر آستانه‌ی C)")
    if missing_ts_pct is not None and missing_ts_pct > 0:
        b_reasons.append(f"missing_timestamp_pct={missing_ts_pct:.2f}% (غیرصفر، زیر آستانه‌ی C)")
    if no_run_log:
        b_reasons.append("Run Log مستقل موجود نیست (docs/reference_file_determination.md) — Audit از رکورد خام بازسازی شده")
    if duplicate_id_pct is not None and duplicate_id_pct > 0:
        b_reasons.append(
            f"duplicate_id_pct={duplicate_id_pct:.1f}% (شناخته‌شده و توسط Exact-ID dedup پایین‌دستی حل می‌شود؛ "
            "دامنه‌ی تحلیل را محدود نمی‌کند، فقط باید در گزارش Provenance افشا شود)"
        )
    if pii_unremediated:
        b_reasons.append(
            "PII خام (author_display_name) در فایل مرجع فعال، بدون Remediation — docs/decision_log.md ۲۰۲۶-۰۸-۰۴/۰۷ "
            "(باید قبل از انتشار/دمو حذف یا هش شود؛ تحلیل آماری خودش را محدود نمی‌کند)"
        )

    if b_reasons:
        return Grade(platform, "B", b_reasons)
    return Grade(platform, "A", ["Missingness=۰، Run Log کامل، بدون PII/Duplicate شناخته‌شده"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="docs/collection_coverage.csv را با گرید/دلیل جدید بازنویسی کن")
    args = parser.parse_args()

    with COVERAGE_PATH.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    print(f"{'platform':10s} {'manual_grade':13s} {'rule_grade':11s} reasons")
    print("-" * 90)
    changed = 0
    for row in rows:
        g = grade_row(row)
        manual = row.get("quality_grade", "unknown")
        match = "OK " if manual == g.grade else "DIFF"
        print(f"{g.platform:10s} {manual:13s} {g.grade:11s} [{match}] " + " | ".join(g.reasons))
        if manual != g.grade:
            changed += 1
        if args.apply:
            row["quality_grade"] = g.grade
            rule_note = "quality_grade.py: " + "; ".join(g.reasons)
            existing_notes = row.get("notes", "")
            if "quality_grade.py:" not in existing_notes:
                row["notes"] = (existing_notes + " || " if existing_notes else "") + rule_note

    if changed:
        print(f"\n{changed} platform(s) where the codified rule DIFFERS from the manual grade on disk — "
              "review before trusting the automated grade over the manual one.")
    else:
        print("\nRule reproduces the existing manual grade for every platform.")

    if args.apply:
        with COVERAGE_PATH.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow({k: row.get(k, "") for k in fieldnames})
        print(f"\nWrote updated grades/reasons to {COVERAGE_PATH}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
