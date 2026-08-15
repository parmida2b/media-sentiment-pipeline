"""
tests/test_config_loader.py — unit tests for config/config_loader.py.

Covers roadmap_pipeline.md's own §3 unit-test ask: "تست config_loader:
تاریخ نامعتبر (end < start) باید error بده، نه سکوت" (an invalid date range
must raise, not silently pass) -- plus a regression test locking in the
2026-08-14 fix for config.yaml's `x:` block (it used to be nested one level
too deep under `youtube:`, so config_loader.load_config().x silently
resolved to {} and x_scraper.py's own `if not X_CONFIG: raise ValueError`
would fire on any real run -- see docs/decision_log.md).
"""

import textwrap

import pytest
import yaml

from config.config_loader import DEFAULT_CONFIG_PATH, load_config

# -- fixtures: minimal valid config.yaml content, as a string -----------------

_MINIMAL_VALID = """
topic: "test topic"
topic_id: "test_topic"
keywords_fa: ["kw fa"]
keywords_en: ["kw en"]
date_range:
  start: "2026-01-01"
  end: "2026-02-01"
platforms: ["youtube"]
youtube:
  max_videos_per_query: 10
"""


def _write(tmp_path, content: str):
    p = tmp_path / "config.yaml"
    p.write_text(textwrap.dedent(content), encoding="utf-8")
    return p


def test_load_config_valid_minimal(tmp_path):
    cfg = load_config(_write(tmp_path, _MINIMAL_VALID))
    assert cfg.topic == "test topic"
    assert cfg.platforms == ["youtube"]
    assert cfg.date_range.start.isoformat() == "2026-01-01"


def test_load_config_end_before_start_raises(tmp_path):
    bad = _MINIMAL_VALID.replace('end: "2026-02-01"', 'end: "2025-12-31"')
    with pytest.raises(ValueError, match="date_range.end"):
        load_config(_write(tmp_path, bad))


def test_load_config_end_same_calendar_day_as_start_does_not_raise(tmp_path):
    # load_config() resolves date_range.end to that date's 23:59:59.999999
    # UTC (datetime.combine(..., time.max)) before comparing against start's
    # midnight -- so an end date equal to the start date is a valid same-day
    # window, not a validation error. Only a genuinely earlier end date (see
    # test_load_config_end_before_start_raises above) must raise.
    same_day = _MINIMAL_VALID.replace('end: "2026-02-01"', 'end: "2026-01-01"')
    cfg = load_config(_write(tmp_path, same_day))
    assert cfg.date_range.end.date().isoformat() == "2026-01-01"


def test_load_config_missing_topic_raises(tmp_path):
    bad = _MINIMAL_VALID.replace('topic: "test topic"\n', "")
    with pytest.raises(ValueError, match="topic"):
        load_config(_write(tmp_path, bad))


def test_load_config_missing_start_raises(tmp_path):
    bad = _MINIMAL_VALID.replace('  start: "2026-01-01"\n', "")
    with pytest.raises(ValueError, match="date_range.start"):
        load_config(_write(tmp_path, bad))


def test_load_config_missing_file_raises_filenotfound(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_config(tmp_path / "does_not_exist.yaml")


def test_load_config_end_auto_does_not_raise(tmp_path):
    # "auto" means "up to now" -- must resolve, not error, and must always
    # be after a start date in the past.
    auto = _MINIMAL_VALID.replace('end: "2026-02-01"', 'end: "auto"')
    cfg = load_config(_write(tmp_path, auto))
    assert cfg.date_range.end_is_auto is True


# -- regression test: config.yaml's x: block (2026-08-14 fix) ---------------

def test_real_config_yaml_x_block_is_top_level_not_nested():
    """Locks in the 2026-08-14 fix: config/config.yaml's `x:` collector
    block must be a top-level sibling of `youtube:` (matching how
    `platforms: [...]` already lists them as siblings), not nested inside
    `youtube:`. Reads the real project config.yaml, not a fixture, because
    the whole point of this bug was that it lived in checked-in content."""
    cfg = load_config(DEFAULT_CONFIG_PATH)
    assert cfg.x, (
        "config.yaml's 'x:' block resolved to {} -- this is exactly the "
        "2026-08-14 nesting bug (x: was indented one level too deep, under "
        "youtube:). x_scraper.py raises ValueError on an empty X_CONFIG."
    )
    assert "x" not in cfg.youtube, (
        "config.yaml's 'x:' block is still nested inside 'youtube:' -- "
        "should be a top-level key."
    )
    for required_key in ("collector_version", "query_version", "runtime", "navigation"):
        assert required_key in cfg.x, f"config.yaml's x: block is missing '{required_key}'"


def test_real_config_yaml_x_block_is_valid_yaml_top_level_key():
    # Belt-and-suspenders check directly against the raw YAML (not through
    # PipelineConfig), so this fails even if config_loader.py itself ever
    # stops surfacing raw['x'] as-is.
    raw = yaml.safe_load(DEFAULT_CONFIG_PATH.read_text(encoding="utf-8"))
    assert "x" in raw, "config.yaml has no top-level 'x:' key"
    assert isinstance(raw["x"], dict) and raw["x"], "config.yaml's top-level 'x:' key is empty"
