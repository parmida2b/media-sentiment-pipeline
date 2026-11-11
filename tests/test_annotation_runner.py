"""Tests for annotation resume, cumulative cost cap, cache cost and worker errors."""

import json
from pathlib import Path

import pytest

from src.annotation import build_annotated_dataset as bad
from src.annotation import llm_client
from src.annotation import run_full_annotation as rfa
from src.annotation.model_routes import ModelRoute

ROUTE = ModelRoute(
    route_name="test_route", model_name="test-model", provider="openrouter", max_batch_size=1,
    confidence_threshold=0.5, estimated_input_cost_per_million_tokens=1.0,
    estimated_output_cost_per_million_tokens=1.0,
)


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def _row(cid: str, status: str, at: str, cost: float = 0.0, **extra) -> dict:
    return {
        "content_id": cid, "target_id": "T01", "sentiment": "neutral", "stance": None,
        "emotion": None, "content_type": None, "confidence": 0.5, "reason_code": None,
        "annotation_status": status, "model_version": "m", "prompt_version": "p",
        "cost_usd": cost, "latency_ms": 1.0, "annotated_at_utc": at, **extra,
    }


def test_load_annotations_keeps_latest_ok_attempt(tmp_path):
    # The newer attempt is written first, so file order alone would pick the older one.
    newer = _row("c1", "ok", "2026-08-15T00:00:00+00:00")
    newer["sentiment"] = "positive"
    older = _row("c1", "ok", "2026-08-14T00:00:00+00:00")
    older["sentiment"] = "negative"
    failed = _row("c1", "api_failure", "2026-08-16T00:00:00+00:00")
    _write_jsonl(tmp_path / "shard_0of1.jsonl", [newer, failed, older])

    out = bad.load_annotations(str(tmp_path / "shard_*.jsonl"))

    assert len(out) == 1
    assert out.iloc[0]["sentiment"] == "positive"


def test_prior_state_reads_every_shard_file(tmp_path):
    _write_jsonl(tmp_path / "shard_0of2.jsonl", [
        _row("a", "ok", "t", cost=10.0),
        _row("b", "api_failure", "t", cost=5.0),
    ])
    _write_jsonl(tmp_path / "shard_1of2.jsonl", [
        _row("c", "ok", "t", cost=20.0),
        _row("d", "ok", "t", cost=7.0, from_cache=True),
    ])
    (tmp_path / "shard_0of1.jsonl").write_text(json.dumps(_row("e", "ok", "t", cost=1.0)) + "\n{broken", encoding="utf-8")

    done, cost = rfa.load_prior_state(tmp_path)

    assert done == {("a", "T01"), ("c", "T01"), ("d", "T01"), ("e", "T01")}
    assert cost == pytest.approx(36.0)


def _fake_result(cost: float, ok: bool = True) -> llm_client.AnnotationResult:
    return llm_client.AnnotationResult(
        route_name="r", model_name="m", provider="p", prompt_version="v",
        payload={"sentiment": "neutral"} if ok else None, confidence=0.5, latency_ms=1.0,
        input_tokens=1, output_tokens=1, cost_usd=cost, from_cache=False,
        call_error=None if ok else "HTTP 500", parse_error=None, validation_error=None,
    )


class _NullCache:
    def save(self) -> None:
        pass


def test_cost_cap_includes_prior_spend(tmp_path, monkeypatch):
    calls = []

    def fake_annotate(**kwargs):
        calls.append(kwargs["content_id"])
        return _fake_result(cost=1.0)

    monkeypatch.setattr(rfa, "annotate", fake_annotate)
    tasks = [(f"c{i}", "text", "x", "T01") for i in range(10)]

    summary = rfa.run_tasks(
        tasks, route=ROUTE, api_keys={}, cache=_NullCache(), run_id="r",
        output_path=tmp_path / "shard_0of1.jsonl", cost_cap=100.0, prior_cost_usd=98.5, workers=1,
    )

    # 98.5 already spent: the second new call crosses 100 and stops the run.
    assert len(calls) == 2
    assert summary["cost_usd"] == pytest.approx(2.0)
    assert summary["total_cost_usd"] == pytest.approx(100.5)
    assert summary["cap_reached"] is True


def test_run_tasks_stops_before_start_when_cap_already_spent(tmp_path, monkeypatch):
    monkeypatch.setattr(rfa, "annotate", lambda **kw: pytest.fail("no call expected"))
    summary = rfa.run_tasks(
        [("c1", "t", "x", "T01")], route=ROUTE, api_keys={}, cache=_NullCache(), run_id="r",
        output_path=tmp_path / "out.jsonl", cost_cap=100.0, prior_cost_usd=100.0, workers=1,
    )
    assert summary["completed"] == 0
    assert summary["cap_reached"] is True


def test_worker_exception_is_counted(tmp_path, monkeypatch, capsys):
    def fake_annotate(**kwargs):
        if kwargs["content_id"] == "bad":
            raise RuntimeError("boom")
        return _fake_result(cost=0.1)

    monkeypatch.setattr(rfa, "annotate", fake_annotate)
    tasks = [("good", "t", "x", "T01"), ("bad", "t", "x", "T01")]

    summary = rfa.run_tasks(
        tasks, route=ROUTE, api_keys={}, cache=_NullCache(), run_id="r",
        output_path=tmp_path / "out.jsonl", cost_cap=100.0, prior_cost_usd=0.0, workers=2,
    )

    assert summary["completed"] == 1
    assert summary["errors"] == 1
    assert "boom" in capsys.readouterr().out


def test_output_row_records_cache_flag(tmp_path, monkeypatch):
    cached = _fake_result(cost=0.0)
    cached.from_cache = True
    monkeypatch.setattr(rfa, "annotate", lambda **kw: cached)
    out = tmp_path / "out.jsonl"
    rfa.run_tasks(
        [("c1", "t", "x", "T01")], route=ROUTE, api_keys={}, cache=_NullCache(), run_id="r",
        output_path=out, cost_cap=100.0, prior_cost_usd=0.0, workers=1,
    )
    assert json.loads(out.read_text(encoding="utf-8"))["from_cache"] is True


def test_cache_hit_costs_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr(llm_client, "USAGE_LOG_PATH", tmp_path / "usage.jsonl")
    raw = llm_client.RawCallResult(
        raw_text=json.dumps({"x": 1}), latency_ms=5.0, input_tokens=1000, output_tokens=1000, call_error=None,
    )
    calls = []
    monkeypatch.setattr(llm_client, "_call_provider", lambda *a, **k: calls.append(1) or raw)
    monkeypatch.setattr(llm_client, "validate_annotation_output", lambda parsed: None)
    monkeypatch.setattr(llm_client, "_parse_json_response", lambda text: ({"confidence": 0.9}, None))
    cache = llm_client.AnnotationCache(path=tmp_path / "cache.json")

    first = llm_client.annotate("hello", "T01", ROUTE, {}, cache)
    second = llm_client.annotate("hello", "T01", ROUTE, {}, cache)

    assert len(calls) == 1
    assert first.cost_usd > 0
    assert second.from_cache is True
    assert second.cost_usd == 0.0
    assert second.original_cost_usd == pytest.approx(first.cost_usd)


def test_cache_save_tolerates_concurrent_set(tmp_path, monkeypatch):
    cache = llm_client.AnnotationCache(path=tmp_path / "cache.json")
    for i in range(5):
        cache.set(f"k{i}", {"v": i})
    real_dumps = json.dumps

    def dumps_with_concurrent_set(obj, **kwargs):
        # Simulates another worker thread inserting while save() serializes.
        for _ in obj:
            cache.set("late", {"v": -1})
        return real_dumps(obj, **kwargs)

    monkeypatch.setattr(llm_client.json, "dumps", dumps_with_concurrent_set)
    cache.save()
    monkeypatch.setattr(llm_client.json, "dumps", real_dumps)

    assert json.loads((tmp_path / "cache.json").read_text(encoding="utf-8"))["k0"] == {"v": 0}


def test_groq_client_error_is_returned_not_raised(monkeypatch):
    import sys
    import types

    class FakeRateLimitError(Exception):
        pass

    def broken_client(api_key):
        raise ValueError("bad key format")

    fake = types.SimpleNamespace(Groq=broken_client, RateLimitError=FakeRateLimitError)
    monkeypatch.setitem(sys.modules, "groq", fake)
    monkeypatch.setattr(llm_client, "_groq_exhausted_keys", set())

    result = llm_client._call_groq({"GROQ_API_KEY": "k"}, ROUTE, "prompt")

    assert result.call_error is not None
    assert "bad key format" in result.call_error

