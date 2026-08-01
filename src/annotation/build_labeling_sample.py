"""
build_labeling_sample.py — Day 2 accuracy benchmark, step 1 (Parmida)
Samples real comments from data/raw/{topic_id}/youtube_comments*.jsonl into a CSV with an
empty human_label column, so a human can hand-label ~50-100 of them. That
labeled file is later scored against the LLM in evaluate_sentiment_accuracy.py.

Usage:
    python src/annotation/build_labeling_sample.py
"""

import csv
import glob
import json
import random
from pathlib import Path

SAMPLE_SIZE = 90  # split across en/fa/ar -> 30 each, adjusted to what's available
RANDOM_SEED = 42
MIN_TEXT_LEN = 3
LANGUAGES = ["en", "fa", "ar"]

ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_PATH = ROOT / "data" / "annotated" / "sample_sentiment_labels.csv"


def load_records() -> list[dict]:
    seen = set()
    records = []
    for fp in sorted(glob.glob(str(ROOT / "data" / "raw" / "*" / "youtube_comments*.jsonl"))):
        with open(fp, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                text = r.get("text", "").strip()
                if len(text) < MIN_TEXT_LEN:
                    continue
                key = (r.get("post_id"), text)
                if key in seen:
                    continue
                seen.add(key)
                records.append(r)
    return records


def stratified_sample(records: list[dict], n: int) -> list[dict]:
    random.seed(RANDOM_SEED)
    by_lang = {lang: [r for r in records if r.get("language") == lang] for lang in LANGUAGES}
    for group in by_lang.values():
        random.shuffle(group)

    target_each = n // len(LANGUAGES)
    sample = []
    leftover = 0
    for lang in LANGUAGES:
        take = min(target_each, len(by_lang[lang]))
        sample.extend(by_lang[lang][:take])
        by_lang[lang] = by_lang[lang][take:]
        leftover += target_each - take

    # redistribute leftover slots to languages that still have unused records
    for lang in LANGUAGES:
        if leftover <= 0:
            break
        take = min(leftover, len(by_lang[lang]))
        sample.extend(by_lang[lang][:take])
        leftover -= take

    random.shuffle(sample)
    return sample


def main():
    records = load_records()
    if not records:
        print("No records found under data/raw/*/youtube_comments*.jsonl — run extraction first.")
        return

    sample = stratified_sample(records, SAMPLE_SIZE)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["sample_id", "post_id", "language", "text", "human_label", "notes"])
        for i, r in enumerate(sample, 1):
            writer.writerow([i, r.get("post_id", ""), r.get("language", ""), r.get("text", ""), "", ""])

    from collections import Counter
    lang_counts = Counter(r.get("language") for r in sample)
    print(f"Wrote {len(sample)} comments to {OUTPUT_PATH}")
    print(f"By language: {dict(lang_counts)}")
    print(
        "\nNext step: open the CSV in Excel and fill the 'human_label' column for each row "
        "with exactly one of: positive / negative / neutral (Persian ok too: مثبت / منفی / خنثی). "
        "Leave a row blank to skip it. Then run src/validation/evaluate_sentiment_accuracy.py."
    )


if __name__ == "__main__":
    main()
