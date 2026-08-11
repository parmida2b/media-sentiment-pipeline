"""
schema.py — canonical Annotation Schema (Parmida)

Single source of truth for the 4-layer annotation contract required by
global_public_opinion_iran_us_assignment.md §18 (Sentiment / Stance / Emotion /
Content Type) and §22 (structured LLM output contract). Every other file in
src/annotation/ and src/validation/ imports label sets and Target IDs from
here instead of re-declaring its own strings, so the four layers can't drift
out of sync between the gold-sample builder, the prompt, and the scorer.

Per §2 of the doc: Sentiment ("is the text positive/negative/neutral") and
Stance ("is the text for/against a specific Target") are DIFFERENT axes and
must stay in separate columns/fields — never collapse one into the other.
"""

from __future__ import annotations

SCHEMA_VERSION = "1.0"

# --- §18 label sets --------------------------------------------------------

SENTIMENT_LABELS = ["positive", "negative", "neutral", "mixed", "unclear"]

STANCE_LABELS = ["support", "oppose", "neutral_or_balanced", "unrelated", "unclear"]

EMOTION_LABELS = [
    "anger", "fear", "sadness", "hope", "joy", "disgust", "surprise", "none_or_unclear",
]

CONTENT_TYPE_LABELS = [
    "personal_opinion", "news_or_report", "quotation", "satire", "spam", "unclear",
]

# --- §18 Stance targets ------------------------------------------------------
# Explicit, closed list — Stance is only meaningful against a named Target
# (doc §2's worked example: a comment can be Sentiment-negative about a war
# while being Stance-supportive of a specific government's decision). Keep
# this in sync with docs/decision_log.md if the team changes it; it is a
# graded decision (§7 "Target‌های Stance" row in the mandatory decisions
# table), not something to edit silently.
TARGETS = {
    "iran_government_policy": "سیاست دولت ایران",
    "us_government_policy": "سیاست دولت آمریکا",
    "military_action": "اقدام نظامی مشخص",
    "negotiation_diplomacy": "مذاکره یا دیپلماسی",
    "human_economic_impact": "اثر انسانی یا اقتصادی",
}
TARGET_IDS = list(TARGETS.keys())

# --- §22 structured output contract ----------------------------------------
# Every LLM annotation call must return exactly these fields. confidence is
# the model's own self-reported confidence — per §24 this is a UI/coverage
# signal, never an accepted substitute for real accuracy evaluation.
REQUIRED_ANNOTATION_OUTPUT_FIELDS = {
    "sentiment",
    "stance",
    "emotion",
    "content_type",
    "confidence",
    "reason_code",
}


class AnnotationValidationError(ValueError):
    """Raised when a structured LLM annotation payload violates the §22 contract."""


def validate_annotation_output(payload: dict[str, object]) -> None:
    """Validate the minimum structured-output contract for one annotation.

    Raises AnnotationValidationError with the specific violation instead of
    letting a malformed payload silently enter downstream analysis (§22:
    "خروجی LLM بدون Schema validation نباید مستقیماً وارد تحلیل شود").
    """
    missing_fields = sorted(REQUIRED_ANNOTATION_OUTPUT_FIELDS.difference(payload))
    if missing_fields:
        raise AnnotationValidationError(
            "Annotation output is missing fields: " + ", ".join(missing_fields)
        )

    checks = [
        ("sentiment", SENTIMENT_LABELS),
        ("stance", STANCE_LABELS),
        ("emotion", EMOTION_LABELS),
        ("content_type", CONTENT_TYPE_LABELS),
    ]
    for field_name, allowed in checks:
        value = payload[field_name]
        if value not in allowed:
            raise AnnotationValidationError(
                f"{field_name}={value!r} is not one of {allowed}"
            )

    confidence = payload["confidence"]
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
        raise AnnotationValidationError("confidence must be numeric.")
    if not 0 <= float(confidence) <= 1:
        raise AnnotationValidationError("confidence must be between 0 and 1.")

    reason_code = payload["reason_code"]
    if not isinstance(reason_code, str) or not reason_code.strip():
        raise AnnotationValidationError("reason_code must be a non-empty string.")


# --- §19 Gold Sample columns -------------------------------------------------
# Minimum columns per §19's code stub. build_labeling_sample.py writes these
# empty for humans to fill; evaluate_sentiment_accuracy.py reads them back.
GOLD_SAMPLE_COLUMNS = [
    "sample_id",
    "content_id",
    "language",
    "text",
    "target",
    "annotator_id",
    "sentiment_label",
    "stance_label",
    "emotion_label",
    "content_type_label",
    "confidence",
    "notes",
]
