"""Generate latency analysis visualizations from collected data."""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def load_report(path: str = "reports/latency_report.json") -> dict:
    with open(path) as f:
        return json.load(f)


def plot_latency_breakdown(report: dict, output_path: str = "reports/latency_breakdown.png"):
    """Create stacked bar chart showing latency breakdown per request."""
    requests = report.get("requests", [])
    if not requests:
        print("No request data to visualize.")
        return

    df = pd.DataFrame(requests)
    components = ["asr_latency_ms", "llm_ttft_ms", "tts_ttfb_ms", "overhead_ms"]
    labels = ["ASR", "LLM TTFT", "TTS TTFB", "Overhead"]

    fig, ax = plt.subplots(figsize=(12, 6))
    bottom = [0] * len(df)
    for comp, label in zip(components, labels):
        if comp in df.columns:
            values = df[comp].tolist()
            ax.bar(range(len(df)), values, bottom=bottom, label=label)
            bottom = [b + v for b, v in zip(bottom, values)]

    ax.axhline(y=1200, color="red", linestyle="--", label="Target (1200ms)")
    ax.set_xlabel("Request")
    ax.set_ylabel("Latency (ms)")
    ax.set_title("End-to-End Latency Breakdown per Request")
    ax.legend()
    plt.tight_layout()

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150)
    print(f"Saved latency breakdown to {output_path}")


def plot_percentile_comparison(report: dict, output_path: str = "reports/percentile_comparison.png"):
    """Bar chart comparing P50 vs P95 for each component."""
    percentiles = report.get("percentiles", {})
    if not percentiles:
        print("No percentile data to visualize.")
        return

    components = list(percentiles.keys())
    p50s = [percentiles[c]["p50"] for c in components]
    p95s = [percentiles[c]["p95"] for c in components]

    x = range(len(components))
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar([i - 0.2 for i in x], p50s, 0.4, label="P50")
    ax.bar([i + 0.2 for i in x], p95s, 0.4, label="P95")
    ax.set_xticks(list(x))
    ax.set_xticklabels([c.replace("_ms", "").replace("_", " ").title() for c in components])
    ax.set_ylabel("Latency (ms)")
    ax.set_title("P50 vs P95 Latency by Component")
    ax.legend()
    plt.tight_layout()

    plt.savefig(output_path, dpi=150)
    print(f"Saved percentile comparison to {output_path}")


def main():
    report = load_report()
    print(f"Analyzing {report['total_requests']} requests...")
    print(json.dumps(report["budget_check"], indent=2))
    plot_latency_breakdown(report)
    plot_percentile_comparison(report)


if __name__ == "__main__":
    main()
