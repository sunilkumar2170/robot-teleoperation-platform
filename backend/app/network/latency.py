"""
Latency Monitoring & RTT Telemetry Service
-------------------------------------------
Maintains running metrics on:
  • Round-trip time (RTT)
  • Average, minimum, and maximum latency
  • Command transmission counters
  • Jitter distribution
"""
from __future__ import annotations

import collections
import time
from typing import Dict, List, Optional


class LatencyTracker:
    """Tracks network round-trip time and command delivery statistics."""

    def __init__(self, history_len: int = 100):
        self.rtt_history: collections.deque = collections.deque(maxlen=history_len)
        self.commands_sent: int = 0
        self.commands_acknowledged: int = 0
        self.commands_rejected: int = 0

    def record_rtt(self, rtt_ms: float) -> None:
        """Record a single measured round-trip time in milliseconds."""
        self.rtt_history.append((time.time(), rtt_ms))

    def get_stats(self) -> Dict:
        """Calculate statistical metrics over recent history."""
        if not self.rtt_history:
            return {
                "latest_rtt_ms": 0.0,
                "avg_latency_ms": 0.0,
                "min_latency_ms": 0.0,
                "max_latency_ms": 0.0,
                "samples_count": 0,
                "commands_sent": self.commands_sent,
                "commands_acknowledged": self.commands_acknowledged,
                "commands_rejected": self.commands_rejected,
            }

        latencies = [lat for _, lat in self.rtt_history]
        return {
            "latest_rtt_ms": round(latencies[-1], 2),
            "avg_latency_ms": round(sum(latencies) / len(latencies), 2),
            "min_latency_ms": round(min(latencies), 2),
            "max_latency_ms": round(max(latencies), 2),
            "samples_count": len(latencies),
            "commands_sent": self.commands_sent,
            "commands_acknowledged": self.commands_acknowledged,
            "commands_rejected": self.commands_rejected,
        }

    def get_recent_history(self) -> List[Dict]:
        return [{"timestamp": t, "rtt_ms": round(r, 2)} for t, r in self.rtt_history]


_latency_tracker = LatencyTracker()


def get_latency_tracker() -> LatencyTracker:
    return _latency_tracker
