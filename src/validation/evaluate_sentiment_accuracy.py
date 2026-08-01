"""
evaluate_sentiment_accuracy.py — Day 2 accuracy benchmark, step 2 (Parmida)
Reads the hand-labeled CSV produced by build_labeling_sample.py and scores the
LLM sentiment classifier(s) against those human labels: accuracy, confusion
matrix, and a per-language breakdown.

Usage:
    python src/validation/evaluate_sentiment_accuracy.py
"""

import csv
import json
import os
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()

ROOT = Path(__file__).resolve().parent.parent.parent
INPUT_PATH = ROOT / "data" / "annotated" / "sample_sentiment_labels.csv"
RESULTS_PATH = ROOT / "outputs" / "model_evaluation" / "sentiment_accuracy_results.jsonl"
SUMMARY_PATH = ROOT / "outputs" / "model_evaluation" / "sentiment_accuracy_summary.json"

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

LABELS = ["positive", "negative", "neutral"]
LABEL_ALIASES = {
    "positive": "positive", "pos": "positive", "مثبت": "positive",
    "negative": "negative", "neg": "negative", "منفی": "negative",
    "neutral": "neutral", "neu": "neutral", "خنثی": "neutral", "خنثي": "neutral",
}

PROMPT_TEMPLATE = """Classify the sentiment of the following social-media comment as
exactly one of: positive, negative, neutral.
The comment may be in Persian, English, or Arabic.
Respond with ONLY a JSON object, no other text: {{"label": "...", "reason": "<= 15 words"}}

Comment:
\"\"\"{text}\"\"\"
"""


def normalize_label(raw: str) -> str | None:
    if not raw:
        return None
    return LABEL_ALIASES.get(raw.strip().lower())


def load_labeled_rows() -> list[dict]:
    rows = []
    skipped = 0
    with open(INPUT_PATH, "r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            label = normalize_label(row.get("human_label", ""))
            if label is None:
                skipped += 1
                continue
            row["human_label"] = label
            rows.append(row)
    print(f"Loaded {len(rows)} hand-labeled rows ({skipped} left blank/unrecognized, skipped).")
    return rows


def parse_prediction(raw_text: str) -> dict:
    raw_text = raw_text.strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        raw_text = raw_text.replace("json\n", "", 1)
    try:
        parsed = json.loads(raw_text)
        label = normalize_label(parsed.get("label", ""))
        return {"label": label or "PARSE_ERROR", "reason": parsed.get("reason", "")}
    except json.JSONDecodeError:
        return {"label": "PARSE_ERROR", "reason": raw_text[:100]}


def call_gemini(model, text: str) -> dict:
    try:
        response = model.generate_content(PROMPT_TEMPLATE.format(text=text))
        return parse_prediction(response.text)
    except Exception as e:
        return {"label": "ERROR", "reason": str(e)[:100]}


def call_groq(client, text: str) -> dict:
    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": PROMPT_TEMPLATE.format(text=text)}],
            temperature=0,
        )
        return parse_prediction(response.choices[0].message.content)
    except Exception as e:
        return {"label": "ERROR", "reason": str(e)[:100]}


def score(rows: list[dict], model_key: str) -> dict:
    """rows must each have 'human_label' and rows[model_key] = {'label': ...}"""
    total = len(rows)
    correct = sum(1 for r in rows if r[model_key]["label"] == r["human_label"])
    confusion = Counter((r["human_label"], r[model_key]["label"]) for r in rows)

    by_lang = defaultdict(lambda: {"correct": 0, "total": 0})
    for r in rows:
        lang = r.get("language") or "unknown"
        by_lang[lang]["total"] += 1
        if r[model_key]["label"] == r["human_label"]:
            by_lang[lang]["correct"] += 1

    return {
        "accuracy": correct / total if total else 0.0,
        "correct": correct,
        "total": total,
        "confusion_matrix": {f"human={h}|pred={p}": c for (h, p), c in confusion.items()},
        "by_language": {
            lang: {"accuracy": v["correct"] / v["total"] if v["total"] else 0.0, **v}
            for lang, v in by_lang.items()
        },
    }


def main():
    if not INPUT_PATH.exists():
        print(f"{INPUT_PATH} not found — run src/annotation/build_labeling_sample.py first.")
        return

    rows = load_labeled_rows()
    if not rows:
        print("No labeled rows to evaluate. Fill in the 'human_label' column and re-run.")
        return

    groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key:
        print("GROQ_API_KEY is empty in .env.")
        return
    from groq import Groq
    groq_client = Groq(api_key=groq_key)

    gemini_key = os.getenv("GEMINI_API_KEY")
    gemini_model = None
    if gemini_key:
        import google.generativeai as genai
        genai.configure(api_key=gemini_key)
        gemini_model = genai.GenerativeModel(GEMINI_MODEL)
    else:
        print("GEMINI_API_KEY is empty in .env — evaluating Groq only.\n")

    for i, row in enumerate(rows, 1):
        text = row["text"]
        row["groq"] = call_groq(groq_client, text)
        time.sleep(0.2)
        if gemini_model:
            row["gemini"] = call_gemini(gemini_model, text)
            time.sleep(0.5)
        print(f"[{i}/{len(rows)}] human={row['human_label']:8s} groq={row['groq']['label']}"
              + (f" gemini={row['gemini']['label']}" if gemini_model else ""))

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    summary = {"n_labeled": len(rows), "groq_model": GROQ_MODEL, "groq": score(rows, "groq")}
    if gemini_model:
        summary["gemini_model"] = GEMINI_MODEL
        summary["gemini"] = score(rows, "gemini")

    with open(SUMMARY_PATH, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"\n=== Results (n={len(rows)}) ===")
    print(f"Groq ({GROQ_MODEL}): accuracy = {summary['groq']['accuracy']:.1%} "
          f"({summary['groq']['correct']}/{summary['groq']['total']})")
    for lang, v in summary["groq"]["by_language"].items():
        print(f"   {lang}: {v['accuracy']:.1%} ({v['correct']}/{v['total']})")
    if gemini_model:
        print(f"Gemini ({GEMINI_MODEL}): accuracy = {summary['gemini']['accuracy']:.1%} "
              f"({summary['gemini']['correct']}/{summary['gemini']['total']})")
        for lang, v in summary["gemini"]["by_language"].items():
            print(f"   {lang}: {v['accuracy']:.1%} ({v['correct']}/{v['total']})")

    print(f"\nDetailed results: {RESULTS_PATH}")
    print(f"Summary: {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
