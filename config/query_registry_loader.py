"""
query_registry_loader.py — reads config/query_registry.yaml (Parmida)

Standalone and additive: does NOT touch config_loader.py or schema.py, so
the v1 pipeline (youtube_extract.py), which still reads config.yaml's flat
keywords_fa/en/ar, is unaffected either way. See docs/decision_log.md.
"""
import os
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import yaml

DEFAULT_REGISTRY_PATH = Path(__file__).resolve().parent / "query_registry.yaml"


@dataclass(frozen=True)
class YouTubeQueryEntry:
    query_id: str
    query_text: str
    language: str
    purpose: str
    active_from: date
    active_to: date | None
    version: str


@dataclass(frozen=True)
class XQueryEntry:
    query_id: str
    platform: str
    query_text: str
    language: str
    family: str
    risk: str
    entity_anchor: str | None
    discovery_route: str
    active_from: date
    active_to: date | None
    version: str


def _load_raw(path: Path | str) -> dict:
    path = Path(path)
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_registry_version(path: Path | str = DEFAULT_REGISTRY_PATH) -> str:
    return str(_load_raw(path).get("registry_version", "unknown"))


def get_x_registry_version(
    path: Path | str = DEFAULT_REGISTRY_PATH,
) -> str:
    return str(_load_raw(path).get("x_registry_version", "unknown"))


def load_all_queries(path: Path | str = DEFAULT_REGISTRY_PATH) -> list[YouTubeQueryEntry]:
    raw = _load_raw(path)
    entries = []
    for item in raw.get("queries", []):
        entries.append(YouTubeQueryEntry(
            query_id=item["query_id"],
            query_text=item["query_text"],
            language=item["language"],
            purpose=item["purpose"],
            active_from=date.fromisoformat(item["active_from"]),
            active_to=date.fromisoformat(item["active_to"]) if item.get("active_to") else None,
            version=str(item.get("version", "0.1")),
        ))
    return entries


def load_all_x_queries(
    path: Path | str = DEFAULT_REGISTRY_PATH,
) -> list[XQueryEntry]:
    custom_topic = os.getenv("SCRAPER_CUSTOM_TOPIC")
    if custom_topic:
        from config import config_loader
        cfg = config_loader.load_config()
        lang = os.getenv("SCRAPER_LANG", "fa")
        if lang not in {"en", "fa"}:
            lang = "fa"

        return [
            XQueryEntry(
                query_id="XQ-001",
                platform="x",
                query_text=custom_topic,
                language=lang,
                family="Custom User Run",
                risk="low",
                entity_anchor=None,
                discovery_route="query_search",
                active_from=cfg.date_range.start,
                active_to=cfg.date_range.end.date(),
                version="v3.0",
            )
        ]

    raw = _load_raw(path)
    entries = []
    for item in raw.get("x_queries", []):
        entries.append(
            XQueryEntry(
                query_id=item["query_id"],
                platform=item["platform"],
                query_text=item["query_text"],
                language=item["language"],
                family=item["family"],
                risk=item["risk"],
                entity_anchor=item.get("entity_anchor"),
                discovery_route=item["discovery_route"],
                active_from=date.fromisoformat(item["active_from"]),
                active_to=(
                    date.fromisoformat(item["active_to"])
                    if item.get("active_to")
                    else None
                ),
                version=str(item.get("version", "unknown")),
            )
        )
    return entries


def load_active_queries(as_of: date | None = None, path: Path | str = DEFAULT_REGISTRY_PATH) -> list[YouTubeQueryEntry]:
    custom_topic = os.getenv("SCRAPER_CUSTOM_TOPIC")
    if custom_topic:
        return [
                YouTubeQueryEntry(
                    query_id="q_custom_user",
                    query_text=custom_topic,
                    language=os.getenv("SCRAPER_LANG", "fa"),
                    purpose="custom_run",
                    active_from=date(2020, 1, 1),
                    active_to=None,
                    version="custom_v1",
                )
            ]
    as_of = as_of or date.today()
    return [
        q for q in load_all_queries(path)
        if q.active_from <= as_of and (q.active_to is None or as_of <= q.active_to)
    ]


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    active = load_active_queries()
    print(f"registry_version: {get_registry_version()!r}")
    print(f"{len(active)} active quer(y/ies):")
    for q in active:
        print(f"  {q.query_id} [{q.language}/{q.purpose}]: {q.query_text!r}")
