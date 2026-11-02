"""
Network Fault Injection Engine
------------------------------
Simulates real-world network transmission degradations between the
teleoperation operator and the robot:
  • Artificial latency (0–2000 ms)
  • Jitter variation (0–500 ms)
  • Packet loss / command dropping (0–50%)

Note: This is simulated application-layer network impairment, clearly
distinguished from actual host operating-system network configuration.
"""
from __future__ import annotations

import asyncio
import logging
import random
import time
from typing import Optional, Tuple

logger = logging.getLogger("network.fault")


class NetworkFaultInjector:
    """Configurable network fault injection service."""

    def __init__(
        self,
        latency_ms: float = 0.0,
        jitter_ms: float = 0.0,
        packet_loss_pct: float = 0.0,
        seed: Optional[int] = None,
    ):
        self.latency_ms = max(0.0, min(2000.0, latency_ms))
        self.jitter_ms = max(0.0, min(500.0, jitter_ms))
        self.packet_loss_pct = max(0.0, min(50.0, packet_loss_pct))
        self._rng = random.Random(seed) if seed is not None else random.Random()

        # Telemetry metrics
        self.total_packets_sent: int = 0
        self.total_packets_dropped: int = 0
        self.total_delay_ms_applied: float = 0.0

    def configure(self, latency_ms: float, jitter_ms: float, packet_loss_pct: float) -> None:
        """Update network fault parameters at runtime."""
        self.latency_ms = max(0.0, min(2000.0, latency_ms))
        self.jitter_ms = max(0.0, min(500.0, jitter_ms))
        self.packet_loss_pct = max(0.0, min(50.0, packet_loss_pct))
        logger.info(
            "Fault injector updated: Latency=%.1fms, Jitter=%.1fms, Loss=%.1f%%",
            self.latency_ms,
            self.jitter_ms,
            self.packet_loss_pct,
        )

    def get_conditions(self) -> dict:
        return {
            "latency_ms": self.latency_ms,
            "jitter_ms": self.jitter_ms,
            "packet_loss_pct": self.packet_loss_pct,
            "total_packets_sent": self.total_packets_sent,
            "total_packets_dropped": self.total_packets_dropped,
            "measured_packet_loss_pct": round(
                (self.total_packets_dropped / max(1, self.total_packets_sent)) * 100.0, 2
            ),
        }

    async def inject_fault(self) -> Tuple[bool, float]:
        """
        Simulate transmission through the impaired channel.
        Returns (is_dropped: bool, delay_ms: float).
        If dropped, delay is not experienced by the server (dropped in transit).
        If delivered, applies asyncio.sleep(delay_ms / 1000.0).
        """
        self.total_packets_sent += 1

        # Check packet drop probability
        if self.packet_loss_pct > 0.0:
            roll = self._rng.uniform(0.0, 100.0)
            if roll < self.packet_loss_pct:
                self.total_packets_dropped += 1
                logger.warning(
                    "PACKET DROP: Packet #%d dropped (Loss setting: %.1f%%)",
                    self.total_packets_sent,
                    self.packet_loss_pct,
                )
                return True, 0.0

        # Calculate latency with random jitter
        jitter_offset = 0.0
        if self.jitter_ms > 0.0:
            jitter_offset = self._rng.uniform(-self.jitter_ms, self.jitter_ms)

        effective_delay_ms = max(0.0, self.latency_ms + jitter_offset)
        self.total_delay_ms_applied += effective_delay_ms

        if effective_delay_ms > 0.0:
            logger.debug("Simulating delay: %.1f ms", effective_delay_ms)
            await asyncio.sleep(effective_delay_ms / 1000.0)

        return False, effective_delay_ms


# Application-level fault injector singleton
_fault_injector = NetworkFaultInjector()


def get_fault_injector() -> NetworkFaultInjector:
    return _fault_injector
