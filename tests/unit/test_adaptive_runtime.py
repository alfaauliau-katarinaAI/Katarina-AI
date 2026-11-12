"""Deterministic adaptive research budget tests; no MT5 or external API access."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from katarina.host import MiB, detect_capacity
from katarina.intelligence.lab.adaptive_runtime import (
    AdaptiveResearchLimiter, ResourceSnapshot, decide_allowance,
)


GiB = 1024 * MiB


def snapshot(*, cpus=4, total=8 * GiB, available=4 * GiB,
             disk=5 * GiB, load=0.1):
    return ResourceSnapshot(cpus, total, available, disk, load)


class AdaptiveResearchBudgetTests(unittest.TestCase):
    def test_two_gigabyte_host_uses_one_job_and_reserves_observer_memory(self):
        result = decide_allowance(snapshot(cpus=2, total=2 * GiB,
                                            available=728 * MiB))
        self.assertEqual(result.slots, 1)
        self.assertEqual(result.status, "READY")
        self.assertFalse(result.live_authorized)
        result = decide_allowance(snapshot(cpus=2, total=2 * GiB,
                                            available=500 * MiB))
        self.assertEqual(result.slots, 0)
        self.assertEqual(result.status, "PAUSED_MEMORY_PRESSURE")

    def test_large_machine_scales_then_cpu_pressure_throttles(self):
        rich = snapshot(cpus=16, total=32 * GiB, available=16 * GiB)
        self.assertEqual(decide_allowance(rich).slots, 9)
        high_load = snapshot(cpus=16, total=32 * GiB,
                             available=16 * GiB, load=0.8)
        self.assertEqual(decide_allowance(high_load).slots, 1)
        critical = snapshot(cpus=16, total=32 * GiB,
                            available=16 * GiB, load=0.97)
        self.assertEqual(decide_allowance(critical).status, "PAUSED_CPU_PRESSURE")
        self.assertEqual(decide_allowance(critical).slots, 0)

    def test_missing_resource_proof_fails_closed(self):
        for item in (snapshot(total=None), snapshot(available=None),
                     snapshot(disk=None), snapshot(cpus=0),
                     snapshot(load=float("nan")), snapshot(load=1.5)):
            with self.subTest(item=item):
                result = decide_allowance(item)
                self.assertEqual(result.slots, 0)
                self.assertEqual(result.status, "PAUSED_RESOURCE_UNVERIFIED")
        self.assertEqual(
            decide_allowance(snapshot(disk=2 * GiB)).status,
            "PAUSED_LOW_DISK")

    def test_cpu_metric_unknown_limits_parallelism(self):
        result = decide_allowance(snapshot(cpus=16, total=32 * GiB,
                                            available=16 * GiB, load=None))
        self.assertEqual(result.slots, 2)

    def test_windows_host_total_ram_can_scale_without_psutil(self):
        with patch("katarina.host.platform.system", return_value="Windows"), \
             patch("katarina.host.windows_memory",
                   return_value=(16 * GiB, 12 * GiB)), \
             patch("katarina.host.os.cpu_count", return_value=8):
            cpu, total = detect_capacity()
            self.assertEqual(cpu, 8)
            self.assertEqual(total, 16 * GiB)

    def test_limiter_releases_and_recovers_without_restart(self):
        clock = [0.0]
        measurements = [
            snapshot(cpus=2, total=2 * GiB, available=728 * MiB),
            snapshot(cpus=2, total=2 * GiB, available=400 * MiB),
            snapshot(cpus=8, total=16 * GiB, available=9 * GiB),
        ]
        calls = []
        def measure(_root):
            calls.append(True)
            return measurements[min(len(calls)-1, len(measurements)-1)]
        with tempfile.TemporaryDirectory() as directory:
            limiter = AdaptiveResearchLimiter(directory, measure=measure,
                                              clock=lambda: clock[0])
            self.assertTrue(limiter.try_acquire())
            self.assertFalse(limiter.try_acquire())  # One slot held
            self.assertEqual(limiter.telemetry()["active_jobs"], 1)
            clock[0] = 6.0
            self.assertFalse(limiter.try_acquire())  # Reduced capacity
            limiter.release()
            self.assertFalse(limiter.try_acquire())  # Still paused
            clock[0] = 12.0
            self.assertTrue(limiter.try_acquire())   # Recovery, no restart
            self.assertGreater(limiter.telemetry()["slots"], 1)
            limiter.release()
            self.assertEqual(limiter.telemetry()["active_jobs"], 0)
            self.assertEqual(len(calls), 3)

    def test_sensor_error_pauses_instead_of_starting_research(self):
        with tempfile.TemporaryDirectory() as directory:
            limiter = AdaptiveResearchLimiter(
                Path(directory), measure=lambda _: (_ for _ in ()).throw(OSError()))
            self.assertFalse(limiter.try_acquire())
            self.assertEqual(limiter.telemetry()["status"],
                             "PAUSED_RESOURCE_UNVERIFIED")


if __name__ == "__main__":
    unittest.main()
