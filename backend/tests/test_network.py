"""
Tests for Network Fault Injector and Latency Tracking
"""
import asyncio
import pytest
from app.network.fault_injector import NetworkFaultInjector
from app.network.latency import LatencyTracker

def test_fault_injector_latency():
    async def _test():
        # Deterministic test: 50ms latency, 0 jitter, 0 loss
        injector = NetworkFaultInjector(latency_ms=50.0, jitter_ms=0.0, packet_loss_pct=0.0)
        t0 = asyncio.get_event_loop().time()
        dropped, delay = await injector.inject_fault()
        t1 = asyncio.get_event_loop().time()
        
        assert not dropped
        assert delay == 50.0
        assert (t1 - t0) >= 0.045  # allowed ~50ms sleep
    asyncio.run(_test())

def test_fault_injector_packet_loss():
    async def _test():
        # Seeded deterministic test: 50% loss over 30 packets
        injector = NetworkFaultInjector(latency_ms=0.0, jitter_ms=0.0, packet_loss_pct=50.0, seed=42)
        dropped_count = 0
        for _ in range(30):
            dropped, _ = await injector.inject_fault()
            if dropped:
                dropped_count += 1
        assert dropped_count > 0
    asyncio.run(_test())

def test_latency_tracker_stats():
    tracker = LatencyTracker(history_len=10)
    tracker.record_rtt(20.0)
    tracker.record_rtt(30.0)
    tracker.record_rtt(40.0)
    
    stats = tracker.get_stats()
    assert stats["latest_rtt_ms"] == 40.0
    assert stats["min_latency_ms"] == 20.0
    assert stats["max_latency_ms"] == 40.0
    assert stats["avg_latency_ms"] == 30.0
    assert stats["samples_count"] == 3
