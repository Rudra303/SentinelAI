"""Metrics collection for chaos experiments."""

import statistics
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class MetricPoint:
    """A single metric data point."""

    name: str
    value: float
    timestamp: float
    labels: dict[str, str] = field(default_factory=dict)


class MetricSeries:
    """A time series of metric values."""

    def __init__(self, name: str):
        self.name = name
        self.points: list[MetricPoint] = []
        self._lock = threading.Lock()

    def add(self, value: float, labels: Optional[dict[str, str]] = None):
        """Add a data point."""
        point = MetricPoint(
            name=self.name,
            value=value,
            timestamp=time.time(),
            labels=labels or {},
        )
        with self._lock:
            self.points.append(point)

    @property
    def values(self) -> list[float]:
        with self._lock:
            return [p.value for p in self.points]

    @property
    def count(self) -> int:
        with self._lock:
            return len(self.points)

    def mean(self) -> float:
        with self._lock:
            if not self.points:
                return 0.0
            return statistics.mean([p.value for p in self.points])

    def median(self) -> float:
        with self._lock:
            if not self.points:
                return 0.0
            return statistics.median([p.value for p in self.points])

    def std_dev(self) -> float:
        with self._lock:
            if len(self.points) < 2:
                return 0.0
            return statistics.stdev([p.value for p in self.points])

    def percentile(self, p: float) -> float:
        """Get the p-th percentile (0-100)."""
        with self._lock:
            if not self.points:
                return 0.0
            sorted_values = sorted([p.value for p in self.points])
            idx = int(len(sorted_values) * p / 100)
            return sorted_values[min(idx, len(sorted_values) - 1)]

    def min(self) -> float:
        with self._lock:
            if not self.points:
                return 0.0
            return min([p.value for p in self.points])

    def max(self) -> float:
        with self._lock:
            if not self.points:
                return 0.0
            return max([p.value for p in self.points])

    def rate(self, window_seconds: float = 60.0) -> float:
        """Calculate rate per second over the window."""
        with self._lock:
            if len(self.points) < 2:
                return 0.0

            now = time.time()
            window_start = now - window_seconds
            window_points = [p for p in self.points if p.timestamp >= window_start]

            if len(window_points) < 2:
                return 0.0

            duration = window_points[-1].timestamp - window_points[0].timestamp
            if duration == 0:
                return 0.0

            return len(window_points) / duration

    def summary(self) -> dict[str, float]:
        """Get a summary of the metric."""
        # Calculate within a single lock to ensure consistent snapshot
        with self._lock:
            if not self.points:
                return {
                    "count": 0,
                    "mean": 0.0,
                    "median": 0.0,
                    "std_dev": 0.0,
                    "min": 0.0,
                    "max": 0.0,
                    "p50": 0.0,
                    "p90": 0.0,
                    "p95": 0.0,
                    "p99": 0.0,
                }
            vals = [p.value for p in self.points]
            count = len(vals)
            sorted_vals = sorted(vals)

            def get_p(p):
                idx = int(count * p / 100)
                return sorted_vals[min(idx, count - 1)]

            return {
                "count": count,
                "mean": statistics.mean(vals),
                "median": statistics.median(vals),
                "std_dev": statistics.stdev(vals) if count > 1 else 0.0,
                "min": min(vals),
                "max": max(vals),
                "p50": get_p(50),
                "p90": get_p(90),
                "p95": get_p(95),
                "p99": get_p(99),
            }


class MetricsCollector:
    """
    Collects and aggregates metrics from chaos experiments.

    Tracks:
    - Operation latencies
    - Failure rates
    - Recovery times
    - Retry counts
    - Fault injection rates
    """

    def __init__(self):
        self._series: dict[str, MetricSeries] = {}
        self._counters: dict[str, int] = {}
        self._start_time = time.time()
        self._lock = threading.Lock()

        # Initialize standard metrics
        self._init_standard_metrics()

    def _init_standard_metrics(self):
        """Initialize standard metric series."""
        standard_metrics = [
            "operation_latency_ms",
            "recovery_time_ms",
            "retry_count",
            "fault_injection_rate",
            "success_rate",
            "error_rate",
        ]
        with self._lock:
            for name in standard_metrics:
                self._series[name] = MetricSeries(name=name)

    def record(
        self,
        name: str,
        value: float,
        labels: Optional[dict[str, str]] = None,
    ):
        """Record a metric value."""
        with self._lock:
            if name not in self._series:
                self._series[name] = MetricSeries(name=name)
            series = self._series[name]
        
        # Add point outside collector lock, since MetricSeries has its own lock
        series.add(value, labels)

    def increment(self, name: str, amount: int = 1):
        """Increment a counter."""
        with self._lock:
            self._counters[name] = self._counters.get(name, 0) + amount

    def get_counter(self, name: str) -> int:
        """Get a counter value."""
        with self._lock:
            return self._counters.get(name, 0)

    def get_series(self, name: str) -> Optional[MetricSeries]:
        """Get a metric series."""
        with self._lock:
            return self._series.get(name)

    def record_operation(
        self,
        operation_name: str,
        latency_ms: float,
        success: bool,
        retries: int = 0,
        fault_type: Optional[str] = None,
    ):
        """Record an operation with all its metrics."""
        labels = {"operation": operation_name}
        if fault_type:
            labels["fault_type"] = fault_type

        self.record("operation_latency_ms", latency_ms, labels)
        self.record("retry_count", retries, labels)

        if success:
            self.increment("operations_successful")
            self.record("success_rate", 1.0, labels)
        else:
            self.increment("operations_failed")
            self.record("success_rate", 0.0, labels)
            self.record("error_rate", 1.0, labels)

        self.increment("operations_total")

        if fault_type:
            self.increment(f"faults_{fault_type}")
            self.increment("faults_total")

    def record_recovery(
        self,
        operation_name: str,
        recovery_time_ms: float,
        recovery_method: str = "retry",
    ):
        """Record a recovery event."""
        self.record(
            "recovery_time_ms",
            recovery_time_ms,
            {
                "operation": operation_name,
                "method": recovery_method,
            },
        )
        self.increment("recoveries_total")

    def record_fault_injection(self, fault_type: str, target: str):
        """Record a fault injection event."""
        self.increment(f"injections_{fault_type}")
        self.increment("injections_total")
        self.record(
            "fault_injection_rate",
            1.0,
            {
                "fault_type": fault_type,
                "target": target,
            },
        )

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of all collected metrics."""
        with self._lock:
            elapsed = time.time() - self._start_time
            total_ops = self._counters.get("operations_total", 0)
            successful_ops = self._counters.get("operations_successful", 0)
            failed_ops = self._counters.get("operations_failed", 0)
            recoveries_total = self._counters.get("recoveries_total", 0)
            faults_total = self._counters.get("faults_total", 0)
            
            fault_types = [
                "tool_failure",
                "delay",
                "hallucination",
                "context_corruption",
                "budget_exhaustion",
            ]
            faults_by_type = {ft: self._counters.get(f"faults_{ft}", 0) for ft in fault_types}
            
            latency_series = self._series.get("operation_latency_ms")
            recovery_series = self._series.get("recovery_time_ms")

        summary = {
            "duration_seconds": elapsed,
            "operations": {
                "total": total_ops,
                "successful": successful_ops,
                "failed": failed_ops,
                "success_rate": successful_ops / total_ops if total_ops > 0 else 0,
            },
            "recoveries": {
                "total": recoveries_total,
            },
            "faults": {
                "total": faults_total,
            },
            "latency": {},
            "recovery_time": {},
            "faults_by_type": faults_by_type,
        }

        # Calculate series summaries outside collector lock to avoid deadlock/blocking
        if latency_series and latency_series.count > 0:
            summary["latency"] = latency_series.summary()

        if recovery_series and recovery_series.count > 0:
            summary["recovery_time"] = recovery_series.summary()

        return summary

    def reset(self):
        """Reset all metrics."""
        with self._lock:
            self._series.clear()
            self._counters.clear()
            self._start_time = time.time()
        self._init_standard_metrics()

    def export_prometheus(self) -> str:
        """Export metrics in Prometheus format."""
        with self._lock:
            counters = dict(self._counters)
            series = dict(self._series)
            
        lines = []

        # Export counters
        for name, value in counters.items():
            lines.append(f"sentinelai_{name} {value}")

        # Export series summaries
        for name, s in series.items():
            if s.count > 0:
                lines.append(f"sentinelai_{name}_count {s.count}")
                lines.append(f"sentinelai_{name}_mean {s.mean()}")
                lines.append(f"sentinelai_{name}_p50 {s.percentile(50)}")
                lines.append(f"sentinelai_{name}_p90 {s.percentile(90)}")
                lines.append(f"sentinelai_{name}_p99 {s.percentile(99)}")

        return "\n".join(lines)

    def export_json(self) -> dict[str, Any]:
        """Export metrics as JSON-serializable dict."""
        with self._lock:
            counters = dict(self._counters)
            series = dict(self._series)
            
        return {
            "counters": counters,
            "series": {
                name: {
                    "count": s.count,
                    "summary": s.summary(),
                    "recent_values": s.values[-100:],  # Last 100 values
                }
                for name, s in series.items()
            },
            "summary": self.get_summary(),
        }
