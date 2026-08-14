"""
config_loader.py — reads config/config.yaml, validates it, and hands
everyone else a resolved PipelineConfig (Parmida; coordinate with the team
since this lives in config/ alongside schema.py).

Version: v1 - Day 2
"""
import os
import re
from dataclasses import dataclass, field
from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = ROOT / "config" / "config.yaml"


@dataclass
class DateRange:
    start: date
    end: datetime  # always resolved to a concrete, tz-aware UTC datetime
    end_is_auto: bool = False  # True when config.yaml set end: "auto" (open-ended "up to now")


@dataclass
class PipelineConfig:
    topic: str
    topic_id: str
    keywords_fa: list[str]
    keywords_en: list[str]
    keywords_ar: list[str]
    date_range: DateRange
    platforms: list[str]
    youtube: dict[str, Any] = field(default_factory=dict)
    x: dict[str, Any] = field(default_factory=dict)


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", text.strip()).strip("_").lower()
    return slug or "topic"


def load_config(path: Path | str = DEFAULT_CONFIG_PATH) -> PipelineConfig:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"config file not found: {path} — create config/config.yaml "
            "(see roadmap_pipeline.md for the expected shape)"
        )

    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    topic = raw.get("topic")
    if not topic:
        raise ValueError("config.yaml: 'topic' is required")

    date_range_raw = raw.get("date_range") or {}
    start_raw = date_range_raw.get("start")
    if not start_raw:
        raise ValueError("config.yaml: 'date_range.start' is required")
    start = date.fromisoformat(str(start_raw))

    end_raw = date_range_raw.get("end", "auto")
    end_is_auto = end_raw in (None, "auto")
    if end_is_auto:
        end = datetime.now(timezone.utc)
    else:
        end_date = date.fromisoformat(str(end_raw))
        end = datetime.combine(end_date, time.max, tzinfo=timezone.utc)

    start_dt = datetime(start.year, start.month, start.day, tzinfo=timezone.utc)
    if end <= start_dt:
        raise ValueError(
            f"config.yaml: date_range.end ({end.date()}) must be after "
            f"date_range.start ({start})"
        )
    custom_topic = os.getenv("SCRAPER_CUSTOM_TOPIC")
    custom_start = os.getenv("SCRAPER_START_DATE")
    custom_end = os.getenv("SCRAPER_END_DATE")

    keywords_fa = raw.get("keywords_fa") or []
    keywords_en = raw.get("keywords_en") or []
    keywords_ar = raw.get("keywords_ar") or []

    if custom_topic:
        topic = custom_topic
        keywords_fa = [custom_topic]
        keywords_en = [custom_topic]
        keywords_ar = []

    if custom_start:
        start = date.fromisoformat(custom_start)
    if custom_end:
        end_date = date.fromisoformat(custom_end)
        end = datetime.combine(end_date, time.max, tzinfo=timezone.utc)
        end_is_auto = False

    return PipelineConfig(
        topic=topic,
        topic_id=raw.get("topic_id") or _slugify(topic),
        keywords_fa=raw.get("keywords_fa") or [],
        keywords_en=raw.get("keywords_en") or [],
        keywords_ar=raw.get("keywords_ar") or [],
        date_range=DateRange(start=start, end=end, end_is_auto=end_is_auto),
        platforms=raw.get("platforms") or [],
        youtube=raw.get("youtube") or {},
        x=raw.get("x") or {},
    )


if __name__ == "__main__":
    cfg = load_config()
    print(f"topic: {cfg.topic!r} (topic_id={cfg.topic_id!r})")
    print(f"date_range: {cfg.date_range.start} -> {cfg.date_range.end}")
    print(f"keywords: fa={cfg.keywords_fa} en={cfg.keywords_en} ar={cfg.keywords_ar}")
    print(f"platforms: {cfg.platforms}")
    print(f"youtube: {cfg.youtube}")
    print(f"x: {cfg.x}")
