"""
compare_llm_sentiment.py — Day 1 sentiment model scouting (Parmida)
Runs a small sample of extracted comments (mixed fa/en) through Gemini Flash
and a Groq-hosted Llama model, side by side, so we can eyeball which one
handles Persian/English sentiment better before committing to one for the
Day 3 batch pipeline.

This is NOT the Day 2 accuracy benchmark (that needs a hand-labeled sample);
it's a quick qualitative scouting pass.

Usage:
    python src/annotation/compare_llm_sentiment.py
"""

import json
import os
import random
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()

ROOT = Path(__file__).resolve().parent.parent.parent
INPUT_PATH = ROOT / "data" / "raw" / "youtube_comments.jsonl"
OUTPUT_PATH = ROOT / "outputs" / "model_evaluation" / "sentiment_model_comparison.jsonl"

SAMPLE_SIZE = 20
RANDOM_SEED = 42

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

PROMPT_TEMPLATE = """Classify the sentiment of the following social-media comment as
exactly one of: positive, negative, neutral.
The comment may be in Persian or English.
Respond with ONLY a JSON object, no other text: {{"label": "...", "reason": "<= 15 words"}}

Comment:
\"\"\"{text}\"\"\"
"""


def load_sample(n: int) -> list[dict]:
    records = []
    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    random.seed(RANDOM_SEED)
    # Try to keep a mix of fa/en in the sample
    fa = [r for r in records if r.get("language") == "fa"]
    en = [r for r in records if r.get("language") == "en"]
    random.shuffle(fa)
    random.shuffle(en)
    half = n // 2
    sample = fa[:half] + en[:n - half]
    random.shuffle(sample)
    return sample


def parse_label(raw_text: str) -> dict:
    raw_text = raw_text.strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        raw_text = raw_text.replace("json\n", "", 1)
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        return {"label": "PARSE_ERROR", "reason": raw_text[:100]}


def call_gemini(model, text: str) -> dict:
    try:
        response = model.generate_content(PROMPT_TEMPLATE.format(text=text))
        return parse_label(response.text)
    except Exception as e:
        return {"label": "ERROR", "reason": str(e)[:100]}


def call_groq(client, text: str) -> dict:
    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": PROMPT_TEMPLATE.format(text=text)}],
            temperature=0,
        )
        return parse_label(response.choices[0].message.content)
    except Exception as e:
        return {"label": "ERROR", "reason": str(e)[:100]}


def main():
    if not INPUT_PATH.exists():
        print(f"{INPUT_PATH} not found — run src/ingestion/youtube_extract.py first.")
        return

    gemini_key = os.getenv("GEMINI_API_KEY")
    groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key:
        print("GROQ_API_KEY is empty in .env.")
        return

    from groq import Groq
    groq_client = Groq(api_key=groq_key)

    gemini_model = None
    if gemini_key:
        import google.generativeai as genai
        genai.configure(api_key=gemini_key)
        gemini_model = genai.GenerativeModel(GEMINI_MODEL)
    else:
        print("GEMINI_API_KEY is empty in .env — skipping Gemini, running Groq-only for now.\n")

    sample = load_sample(SAMPLE_SIZE)
    label = f"Gemini: {GEMINI_MODEL}, Groq: {GROQ_MODEL}" if gemini_model else f"Groq only: {GROQ_MODEL}"
    print(f"Comparing on {len(sample)} comments ({label})\n")

    results = []
    agree = 0
    for i, record in enumerate(sample, 1):
        text = record["text"]
        lang = record.get("language")

        if gemini_model:
            gemini_result = call_gemini(gemini_model, text)
            time.sleep(0.5)
        else:
            gemini_result = {"label": "SKIPPED", "reason": "no GEMINI_API_KEY"}

        groq_result = call_groq(groq_client, text)
        time.sleep(0.2)

        match = gemini_model is not None and gemini_result.get("label") == groq_result.get("label")
        agree += match

        print(f"[{i}/{len(sample)}] ({lang}) {text[:60]!r}")
        if gemini_model:
            print(f"   Gemini: {gemini_result.get('label')} — {gemini_result.get('reason')}")
            print(f"   {'MATCH' if match else 'DIFFER'}")
        print(f"   Groq:   {groq_result.get('label')} — {groq_result.get('reason')}\n")

        results.append({
            "text": text,
            "language": lang,
            "gemini": gemini_result,
            "groq": groq_result,
            "agree": match,
        })

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    if gemini_model:
        print(f"Agreement: {agree}/{len(sample)} ({agree / len(sample):.0%})")
    print(f"Full results written to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
