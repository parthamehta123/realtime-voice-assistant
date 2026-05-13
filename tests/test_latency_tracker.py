"""Tests for latency tracking and budget analysis."""

import json

from src.latency_tracker import LATENCY_BUDGET, LatencyStore, RequestLatency


def test_request_latency_compute_total():
    r = RequestLatency(
        request_id="test-1",
        asr_latency_ms=200,
        llm_ttft_ms=400,
        tts_ttfb_ms=150,
        overhead_ms=50,
    )
    r.compute_total()
    assert r.total_ms == 800


def test_request_latency_to_dict():
    r = RequestLatency(request_id="test-1", asr_latency_ms=100.123)
    d = r.to_dict()
    assert d["request_id"] == "test-1"
    assert d["asr_latency_ms"] == 100.12


def test_latency_store_empty():
    store = LatencyStore()
    assert store.get_percentiles() == {}
    assert store.check_budget() == {}


def test_latency_store_record_and_percentiles():
    store = LatencyStore()
    for i in range(10):
        r = RequestLatency(
            request_id=f"r-{i}",
            asr_latency_ms=100 + i * 10,
            llm_ttft_ms=200 + i * 20,
            tts_ttfb_ms=50 + i * 5,
            overhead_ms=20,
        )
        store.record(r)

    p = store.get_percentiles()
    assert "asr_latency_ms" in p
    assert "llm_ttft_ms" in p
    assert "total_ms" in p
    assert p["asr_latency_ms"]["p50"] <= p["asr_latency_ms"]["p95"]


def test_latency_store_within_budget():
    store = LatencyStore()
    r = RequestLatency(
        request_id="ok",
        asr_latency_ms=200,
        llm_ttft_ms=400,
        tts_ttfb_ms=150,
        overhead_ms=50,
    )
    store.record(r)
    budget = store.check_budget()
    assert all(v["within_budget"] for v in budget.values())


def test_latency_store_over_budget():
    store = LatencyStore()
    r = RequestLatency(
        request_id="slow",
        asr_latency_ms=500,
        llm_ttft_ms=800,
        tts_ttfb_ms=400,
        overhead_ms=200,
    )
    store.record(r)
    budget = store.check_budget()
    assert not budget["asr"]["within_budget"]
    assert not budget["total"]["within_budget"]


def test_latency_store_save(tmp_path):
    store = LatencyStore()
    store.record(
        RequestLatency(
            request_id="t", asr_latency_ms=100, llm_ttft_ms=200, tts_ttfb_ms=80
        )
    )
    path = str(tmp_path / "report.json")
    store.save(path)
    with open(path) as f:
        data = json.load(f)
    assert data["total_requests"] == 1
    assert "percentiles" in data
    assert "budget_check" in data


def test_latency_budget_targets():
    assert LATENCY_BUDGET["asr"] == 300
    assert LATENCY_BUDGET["llm_ttft"] == 500
    assert LATENCY_BUDGET["tts_ttfb"] == 200
    assert LATENCY_BUDGET["total"] == 1200
