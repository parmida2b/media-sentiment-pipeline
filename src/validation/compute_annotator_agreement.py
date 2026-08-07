"""
compute_annotator_agreement.py — inter-annotator agreement (Parmida)

Implements the §19 requirement to measure agreement between at least two
annotators on part of the Gold Sample, using Cohen's Kappa (the doc's
preferred metric; Percent Agreement is reported too but only as a
supplementary number, never the primary one — §19).

Reads:
  data/annotated/sample_sentiment_labels.csv                (annotator 1, full sample)
  data/annotated/sample_sentiment_labels_agreement_subset.csv (annotator 2, subset)
Matches rows by content_id.

Usage:
    python src/validation/compute_annotator_agreement.py
"""

import csv
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from src.annotation.schema import (  # noqa: E402
    CONTENT_TYPE_LABELS,
    EMOTION_LABELS,
    SENTIMENT_LABELS,
    STANCE_LABELS,
)

MAIN_PATH = ROOT / "data" / "annotated" / "sample_sentiment_labels.csv"
SUBSET_PATH = ROOT / "data" / "annotated" / "sample_sentiment_labels_agreement_subset.csv"
OUTPUT_PATH = ROOT / "outputs" / "audits" / "annotator_agreement.json"

LABEL_AXES = {
    "sentiment_label": SENTIMENT_LABELS,
    "stance_label": STANCE_LABELS,
    "emotion_label": EMOTION_LABELS,
    "content_type_label": CONTENT_TYPE_LABELS,
}


def load_rows(path: Path) -> dict[str, dict]:
    """content_id -> row, keeping only rows with a non-blank content_id."""
    rows = {}
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            content_id = (row.get("content_id") or "").strip()
            if content_id:
                rows[content_id] = row
    return rows


def cohen_kappa(labels_a: list[str], labels_b: list[str]) -> float:
    """Cohen's Kappa for two equal-length lists of categorical labels.
    Standard closed-form: kappa = (p_o - p_e) / (1 - p_e)."""
    n = len(labels_a)
    if n == 0:
        return float("nan")

    agree = sum(1 for a, b in zip(labels_a, labels_b) if a == b)
    p_o = agree / n

    categories = sorted(set(labels_a) | set(labels_b))
    p_e = 0.0
    for cat in categories:
        p_a = labels_a.count(cat) / n
        p_b = labels_b.count(cat) / n
        p_e += p_a * p_b

    if p_e == 1.0:
        return 1.0  # both annotators used exactly one, identical category — perfect agreement by definition
    return (p_o - p_e) / (1 - p_e)


def score_axis(main_rows: dict, subset_rows: dict, column: str, allowed_labels: list[str]) -> dict:
    labels_a, labels_b, skipped = [], [], 0
    for content_id, row_b in subset_rows.items():
        row_a = main_rows.get(content_id)
        if row_a is None:
            skipped += 1
            continue
        label_a = (row_a.get(column) or "").strip()
        label_b = (row_b.get(column) or "").strip()
        if not label_a or not label_b:
            skipped += 1
            continue
        if label_a not in allowed_labels or label_b not in allowed_labels:
            skipped += 1
            continue
        labels_a.append(label_a)
        labels_b.append(label_b)

    n = len(labels_a)
    percent_agreement = sum(1 for a, b in zip(labels_a, labels_b) if a == b) / n if n else float("nan")
    return {
        "n_compared": n,
        "n_skipped_incomplete": skipped,
        "cohens_kappa": cohen_kappa(labels_a, labels_b) if n else float("nan"),
        "percent_agreement": percent_agreement,
    }


def main():
    if not MAIN_PATH.exists() or not SUBSET_PATH.exists():
        print(f"Need both {MAIN_PATH} and {SUBSET_PATH} — run "
              "src/annotation/build_labeling_sample.py first, then have two annotators fill them.")
        return

    main_rows = load_rows(MAIN_PATH)
    subset_rows = load_rows(SUBSET_PATH)

    results = {axis: score_axis(main_rows, subset_rows, axis, labels) for axis, labels in LABEL_AXES.items()}

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"=== Inter-annotator agreement (n rows in subset file = {len(subset_rows)}) ===")
    for axis, r in results.items():
        if r["n_compared"] == 0:
            print(f"{axis}: no comparable rows yet (n_skipped_incomplete={r['n_skipped_incomplete']}) "
                  "— both CSVs need this column filled for the same content_id rows.")
            continue
        kappa = r["cohens_kappa"]
        quality = (
            "poor" if kappa < 0.20 else
            "fair" if kappa < 0.40 else
            "moderate" if kappa < 0.60 else
            "substantial" if kappa < 0.80 else
            "almost perfect"
        )
        print(f"{axis}: kappa={kappa:.3f} ({quality}), percent_agreement={r['percent_agreement']:.1%}, "
              f"n={r['n_compared']} (skipped {r['n_skipped_incomplete']})")

    print(f"\nFull results: {OUTPUT_PATH}")
    print(
        "\nReminder (§19 of the assignment doc): if kappa is low, the raw hand labels "
        "themselves aren't reliable yet — resolve disagreements (adjudication) before "
        "trusting this sample as ground truth for model evaluation."
    )


if __name__ == "__main__":
    main()
