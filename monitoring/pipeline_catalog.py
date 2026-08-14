from __future__ import annotations
import ast
import json
import os
from pathlib import Path
import yaml
from settings import PIPELINE_ROOT
from config_store import get_json, get_value


def _assignment_literal(path: Path, name: str):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets = node.targets
            value = node.value
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
            value = node.value
        else:
            continue
        if any(isinstance(t, ast.Name) and t.id == name for t in targets):
            return ast.literal_eval(value)
    raise KeyError(name)


def reddit_native_sources():
    path = PIPELINE_ROOT / "src/ingestion/reddit_parent_post_collector.py"
    return _assignment_literal(path, "SOURCE_REGISTRY")


def reddit_native_queries():
    path = PIPELINE_ROOT / "src/ingestion/reddit_parent_post_collector.py"
    return _assignment_literal(path, "QUERY_REGISTRY")


def reddit_effective_sources():
    override = get_json("REDDIT_SOURCES_JSON", None)
    return override if isinstance(override, dict) else reddit_native_sources()


def reddit_effective_queries():
    custom_topic = os.getenv("SCRAPER_CUSTOM_TOPIC")
    if custom_topic:
        return [{
                "query_id": "RQ-CUSTOM-001",
                "family": "Custom User Run",
                "lang": os.getenv("SCRAPER_LANG", "en"),
                "logical_query": custom_topic,
                "risk": "low",
                "entity_anchor": "",
                "discovery_route": "query_search",
                "source_ids": ["RD-001"],
                "search_terms": [custom_topic],
                "enabled": True
            }]
    override = get_json("REDDIT_QUERIES_JSON", None)
    return override if isinstance(override, list) else reddit_native_queries()


def query_registry_raw():
    path = PIPELINE_ROOT / "config/query_registry.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def youtube_queries():
    raw = query_registry_raw()
    return [q for q in raw.get("queries", []) if q.get("language") != "ar"]


def x_queries():
    return query_registry_raw().get("x_queries", []) or []


def pipeline_config_raw():
    path = PIPELINE_ROOT / "config/config.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def youtube_native_regions():
    return pipeline_config_raw().get("youtube", {}).get("regions", []) or []


def youtube_native_explicit_video_ids():
    return pipeline_config_raw().get("youtube", {}).get("explicit_video_ids", []) or []


def finance_assets():
    """Parse native Asset(...) registry without importing/running the collector."""
    path = PIPELINE_ROOT / "src/ingestion/finance_market_extract.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    assets = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not (isinstance(node.func, ast.Name) and node.func.id == "Asset"):
            continue
        vals = []
        for arg in node.args[:14]:
            try:
                vals.append(ast.literal_eval(arg))
            except Exception:
                vals.append(None)
        if len(vals) < 13 or not isinstance(vals[0], str):
            continue
        assets.append({
            "asset_id": vals[0], "name": vals[1], "category": vals[2],
            "instrument_type": vals[3], "unit": vals[4], "currency": vals[5],
            "transform": vals[6], "role": vals[7], "market": vals[8],
            "tier": vals[9], "price_type": vals[10], "source": vals[11],
            "source_series_id": vals[12], "endpoint": vals[13] if len(vals) > 13 else None,
        })
    # de-duplicate (VERIFY calls are included too and intentionally shown)
    out = {}
    for a in assets:
        out[a["asset_id"]] = a
    return list(out.values())


def effective_youtube_query_ids():
    all_ids = [q.get("query_id") for q in youtube_queries() if q.get("query_id")]
    raw = (get_value("YOUTUBE_ACTIVE_QUERY_IDS") or "").strip()
    if not raw:
        return all_ids
    selected = [x.strip() for x in raw.split(",") if x.strip()]
    return [x for x in selected if x in set(all_ids)]


def effective_reddit_query_ids():
    all_ids = [q.get("query_id") for q in reddit_effective_queries() if q.get("query_id")]
    raw = (get_value("REDDIT_ACTIVE_QUERY_IDS") or "").strip()
    if not raw:
        return all_ids
    selected = [x.strip() for x in raw.split(",") if x.strip()]
    return [x for x in selected if x in set(all_ids)]
