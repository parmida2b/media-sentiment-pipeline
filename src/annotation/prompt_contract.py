"""
prompt_contract.py — versioned annotation prompt (Parmida)

Implements §22 of the assignment doc: every prompt must be versioned and
cover classification goal, label definitions, Target, accepted-case rules,
satire/quotation rules, input language, JSON output shape, confidence, and
prompt/model version. Bump PROMPT_VERSION on any wording change to a label
definition or rule — it gets stamped onto every annotation record so a
model-evaluation run can be tied back to the exact prompt that produced it.
"""

from __future__ import annotations

from src.annotation.schema import (
    CONTENT_TYPE_LABELS,
    EMOTION_LABELS,
    SENTIMENT_LABELS,
    STANCE_LABELS,
    TARGETS,
)

PROMPT_VERSION = "2026-08-07.v1"

_LABEL_DEFINITIONS = f"""
LABEL DEFINITIONS (these are 4 SEPARATE axes — never merge them):

1. sentiment — the text's own emotional tone, independent of any Target:
   one of {SENTIMENT_LABELS}
   - "mixed": clearly contains both positive and negative tone.
   - "unclear": tone cannot be determined from the text.

2. stance — whether the text is FOR or AGAINST the single Target given below
   (not the topic in general): one of {STANCE_LABELS}
   - "neutral_or_balanced": explicitly discusses the Target without taking a side.
   - "unrelated": the text does not actually address the Target.
   - "unclear": addresses the Target but the position can't be determined.
   Example (from the assignment doc): "This war is very dangerous, but the
   US government's decision is defensible" → sentiment=negative,
   stance=support (toward Target=T05, "سیاست یا اقدامات دولت آمریکا"). Sentiment
   and stance can legitimately point in different directions — do not force
   them to agree.

3. emotion — the dominant emotion expressed, if any: one of {EMOTION_LABELS}

4. content_type — what kind of text this is: one of {CONTENT_TYPE_LABELS}
   - "quotation": text is reporting/quoting someone else's words or a news
     headline, not the author's own voice.
   - "satire": text is ironic/sarcastic — its literal words do not reflect
     the author's real sentiment. When you detect satire, set content_type
     to "satire" and set sentiment/stance to what the author actually MEANS,
     not the literal surface reading.
   - "spam": unrelated advertising, bot-like, or repeated boilerplate text.
"""

_JSON_CONTRACT = """
Respond with ONLY a single JSON object, no other text, no markdown fences:
{
  "sentiment": "<one of the sentiment labels>",
  "stance": "<one of the stance labels>",
  "emotion": "<one of the emotion labels>",
  "content_type": "<one of the content_type labels>",
  "confidence": <float 0.0-1.0, your own confidence in this whole annotation>,
  "reason_code": "<short lowercase_snake_case tag, <=4 words, e.g. explicit_support_phrase, sarcastic_tone, quotes_news_headline>"
}
"""


def build_prompt(text: str, target_id: str) -> str:
    """Build the versioned annotation prompt for one text against one Target.

    target_id must be a key of schema.TARGETS — the Target is always named
    explicitly in the prompt per §18 ("Target باید صریح باشد").
    """
    if target_id not in TARGETS:
        raise KeyError(f"Unknown target_id {target_id!r}. Known: {list(TARGETS)}")
    target_label_fa = TARGETS[target_id]

    return f"""You are annotating one social-media comment (Persian, English, or
occasionally Arabic) about the Iran-US conflict for a social-science research
project. Follow the label definitions exactly; do not invent new labels.
{_LABEL_DEFINITIONS}
TARGET for the "stance" field: {target_id} ("{target_label_fa}")

INPUT LANGUAGE: the comment may be in Persian, English, or Arabic — annotate
in whatever language it is written, do not translate it first.

{_JSON_CONTRACT}

Comment:
\"\"\"{text}\"\"\"
"""
