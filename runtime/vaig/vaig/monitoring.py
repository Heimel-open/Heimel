"""VAIG monitoring and metrics collection.

Prometheus-compatible metrics for production observability.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class LatencyStats:
    """Running latency statistics for a component."""
    values: deque = field(default_factory=lambda: deque(maxlen=1000))

    def add(self, ms: float) -> None:
        self.values.append(ms)

    @property
    def count(self) -> int:
        return len(self.values)

    @property
    def p50(self) -> float:
        if not self.values:
            return 0.0
        return sorted(self.values)[int(len(self.values) * 0.50)]

    @property
    def p95(self) -> float:
        if not self.values:
            return 0.0
        return sorted(self.values)[int(len(self.values) * 0.95)]

    @property
    def p99(self) -> float:
        if not self.values:
            return 0.0
        return sorted(self.values)[int(len(self.values) * 0.99)]

    @property
    def avg(self) -> float:
        if not self.values:
            return 0.0
        return sum(self.values) / len(self.values)


@dataclass
class MetricsCollector:
    """Collects and exposes VAIG runtime metrics."""

    evaluations_total: int = 0
    evaluations_by_level: Dict[str, int] = field(default_factory=dict)
    evaluation_latency: LatencyStats = field(default_factory=LatencyStats)
    instrument_latency: Dict[str, LatencyStats] = field(default_factory=dict)
    instrument_calls: Dict[str, int] = field(default_factory=dict)
    instrument_failures: Dict[str, int] = field(default_factory=dict)
    instrument_scores: Dict[str, List[float]] = field(default_factory=dict)
    _start_time: float = field(default_factory=time.time)

    def record_evaluation(self, result) -> None:
        self.evaluations_total += 1
        level_name = result.level.name if hasattr(result.level, "name") else str(result.level)
        self.evaluations_by_level[level_name] = self.evaluations_by_level.get(level_name, 0) + 1
        self.evaluation_latency.add(result.latency_ms)

    def record_instrument(self, slot: str, score: float, latency_ms: float, failed: bool = False) -> None:
        self.instrument_calls[slot] = self.instrument_calls.get(slot, 0) + 1
        if slot not in self.instrument_latency:
            self.instrument_latency[slot] = LatencyStats()
        self.instrument_latency[slot].add(latency_ms)
        if failed:
            self.instrument_failures[slot] = self.instrument_failures.get(slot, 0) + 1
        if slot not in self.instrument_scores:
            self.instrument_scores[slot] = []
        self.instrument_scores[slot].append(score)

    @property
    def uptime_seconds(self) -> float:
        return time.time() - self._start_time

    @property
    def failure_rate(self) -> float:
        total_calls = sum(self.instrument_calls.values())
        total_failures = sum(self.instrument_failures.values())
        if total_calls == 0:
            return 0.0
        return total_failures / total_calls

    def to_prometheus(self) -> str:
        lines = [
            "# TYPE vaig_evaluations_total counter",
            f"vaig_evaluations_total {self.evaluations_total}",
            "",
            "# TYPE vaig_evaluations_by_level counter",
        ]
        for level, count in self.evaluations_by_level.items():
            lines.append(f"vaig_evaluations_by_level{{level=\"{level}\"}} {count}")
        lines.extend([
            "",
            "# TYPE vaig_evaluation_latency_ms summary",
            f"vaig_evaluation_latency_ms{{quantile=\"0.50\"}} {self.evaluation_latency.p50:.2f}",
            f"vaig_evaluation_latency_ms{{quantile=\"0.95\"}} {self.evaluation_latency.p95:.2f}",
            f"vaig_evaluation_latency_ms{{quantile=\"0.99\"}} {self.evaluation_latency.p99:.2f}",
            f"vaig_evaluation_latency_ms_count {self.evaluation_latency.count}",
            "",
            "# TYPE vaig_instrument_calls_total counter",
        ])
        for slot, count in self.instrument_calls.items():
            lines.append(f"vaig_instrument_calls_total{{slot=\"{slot}\"}} {count}")
        lines.append("")
        lines.append("# TYPE vaig_instrument_failures_total counter")
        for slot, count in self.instrument_failures.items():
            lines.append(f"vaig_instrument_failures_total{{slot=\"{slot}\"}} {count}")
        lines.extend([
            "",
            "# TYPE vaig_instrument_latency_ms summary",
        ])
        for slot, stats in self.instrument_latency.items():
            lines.append(f"vaig_instrument_latency_ms{{slot=\"{slot}\",quantile=\"0.99\"}} {stats.p99:.2f}")
        lines.extend([
            "",
            f"# TYPE vaig_uptime_seconds gauge",
            f"vaig_uptime_seconds {self.uptime_seconds:.0f}",
            "",
            f"# TYPE vaig_failure_rate gauge",
            f"vaig_failure_rate {self.failure_rate:.4f}",
        ])
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "evaluations_total": self.evaluations_total,
            "evaluations_by_level": dict(self.evaluations_by_level),
            "evaluation_latency": {
                "p50": self.evaluation_latency.p50,
                "p95": self.evaluation_latency.p95,
                "p99": self.evaluation_latency.p99,
                "avg": self.evaluation_latency.avg,
                "count": self.evaluation_latency.count,
            },
            "instrument_calls": dict(self.instrument_calls),
            "instrument_failures": dict(self.instrument_failures),
            "instrument_latency": {
                slot: {"p99": stats.p99, "avg": stats.avg, "count": stats.count}
                for slot, stats in self.instrument_latency.items()
            },
            "uptime_seconds": self.uptime_seconds,
            "failure_rate": self.failure_rate,
        }
