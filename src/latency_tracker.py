"""Latency tracking and budget analysis for voice pipeline components."""

import json
import time
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class RequestLatency:
    """Latency breakdown for a single voice assistant request."""
    request_id: str
    asr_latency_ms: float = 0
    llm_ttft_ms: float = 0
    llm_total_ms: float = 0
    tts_ttfb_ms: float = 0
    tts_total_ms: float = 0
    overhead_ms: float = 0
    total_ms: float = 0
    timestamp: float = field(default_factory=time.time)

    def compute_total(self):
        self.total_ms = self.asr_latency_ms + self.llm_ttft_ms + self.tts_ttfb_ms + self.overhead_ms

    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "asr_latency_ms": round(self.asr_latency_ms, 2),
            "llm_ttft_ms": round(self.llm_ttft_ms, 2),
            "llm_total_ms": round(self.llm_total_ms, 2),
            "tts_ttfb_ms": round(self.tts_ttfb_ms, 2),
            "tts_total_ms": round(self.tts_total_ms, 2),
            "overhead_ms": round(self.overhead_ms, 2),
            "total_ms": round(self.total_ms, 2),
        }


# Latency budget targets (ms)
LATENCY_BUDGET = {
    "asr": 300,
    "llm_ttft": 500,
    "tts_ttfb": 200,
    "overhead": 100,
    "total": 1200,
}


class LatencyStore:
    """Stores and analyzes latency data across requests."""

    def __init__(self):
        self.requests: list[RequestLatency] = []

    def record(self, latency: RequestLatency):
        latency.compute_total()
        self.requests.append(latency)

    def get_percentiles(self) -> dict:
        if not self.requests:
            return {}

        def percentile(values, p):
            sorted_v = sorted(values)
            idx = int(len(sorted_v) * p / 100)
            return round(sorted_v[min(idx, len(sorted_v) - 1)], 2)

        fields = ["asr_latency_ms", "llm_ttft_ms", "tts_ttfb_ms", "total_ms"]
        result = {}
        for f in fields:
            values = [getattr(r, f) for r in self.requests]
            result[f] = {
                "p50": percentile(values, 50),
                "p95": percentile(values, 95),
                "mean": round(sum(values) / len(values), 2),
            }
        return result

    def check_budget(self) -> dict:
        """Check if latencies are within budget targets."""
        percentiles = self.get_percentiles()
        checks = {}
        mapping = {
            "asr_latency_ms": "asr",
            "llm_ttft_ms": "llm_ttft",
            "tts_ttfb_ms": "tts_ttfb",
            "total_ms": "total",
        }
        for metric, budget_key in mapping.items():
            if metric in percentiles:
                p95 = percentiles[metric]["p95"]
                target = LATENCY_BUDGET[budget_key]
                checks[budget_key] = {
                    "p95": p95,
                    "target": target,
                    "within_budget": p95 <= target,
                }
        return checks

    def save(self, path: str = "reports/latency_report.json"):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        report = {
            "total_requests": len(self.requests),
            "percentiles": self.get_percentiles(),
            "budget_check": self.check_budget(),
            "requests": [r.to_dict() for r in self.requests[-100:]],
        }
        with open(path, "w") as f:
            json.dump(report, f, indent=2)
