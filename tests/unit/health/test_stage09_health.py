from __future__ import annotations

import unittest

from katarina.contracts.runtime import RuntimeMode
from katarina.core.readiness import ReadinessGate, ReadinessSignal
from katarina.health.engine import HealthSafetyEngine, HealthState


NOW = 2_000_000_000_000_000_000


class Stage09HealthSafetyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = HealthSafetyEngine()
        self.readiness = ReadinessGate(RuntimeMode.LIVE)

    def health(self, state: int = 1):
        return {
            "data_health": state,
            "transport_health": state,
            "execution_health": state,
            "reconciliation_health": state,
            "journal_health": state,
            "clock_health": state,
            "snapshot_health": state,
            "health_flags": 0,
            "reason_code": 0,
            "critical_queue_depth": 0,
            "market_queue_depth": 0,
            "last_tick_time_ns": NOW,
            "last_broker_observation_ns": NOW,
            "last_reconciliation_ns": NOW,
            "latest_execution_cursor": 1,
        }

    def heartbeat(self, *, critical=0, market=0, broker_ns=NOW):
        return {
            "uptime_ms": 1000,
            "latest_produced_sequence": 10,
            "latest_consumed_command_sequence": 10,
            "critical_queue_depth": critical,
            "market_queue_depth": market,
            "last_broker_observation_ns": broker_ns,
            "transport_state": 1,
        }

    def session(
        self,
        *,
        connected=1,
        session_open=1,
        fresh_tick=1,
        trade_allowed=1,
        ping=10_000,
        server_time=NOW,
    ):
        return {
            "instrument_id": 1,
            "spec_revision": 1,
            "state_revision": 1,
            "last_tick_time_ns": NOW,
            "server_time_ns": server_time,
            "scheduled_open": session_open,
            "terminal_connected": connected,
            "terminal_trade_allowed": trade_allowed,
            "mql_trade_allowed": trade_allowed,
            "symbol_trade_allowed": trade_allowed,
            "fresh_tick": fresh_tick,
            "session_open": session_open,
            "terminal_ping_us": ping,
        }

    def metrics(self, *, rtt=10_000, decode_errors=0):
        return {
            "frames_sent": 10,
            "frames_received": 10,
            "bytes_sent": 1000,
            "bytes_received": 1000,
            "dropped_advisory_frames": 0,
            "decode_errors": decode_errors,
            "rtt_us_p50": rtt // 2,
            "rtt_us_p99": rtt,
            "send_queue_depth": 0,
            "receive_queue_depth": 0,
        }

    def prime_ok(self, *, health_events=2):
        self.engine.observe_data_fresh(True)
        self.engine.observe_heartbeat(self.heartbeat(), observed_at_ns=NOW)
        self.engine.observe_session_state(self.session())
        self.engine.observe_transport_metrics(self.metrics(), observed_at_ns=NOW)
        for _ in range(health_events):
            self.engine.observe_health_event(self.health(), observed_at_ns=NOW)

    def test_initial_state_is_not_health_ready(self):
        snapshot = self.engine.apply_readiness(self.readiness, now_ns=NOW)
        self.assertNotEqual(snapshot.overall, HealthState.OK)
        self.assertFalse(self.readiness.is_set(ReadinessSignal.HEALTH))

    def test_two_healthy_events_make_health_ready(self):
        self.prime_ok()
        snapshot = self.engine.apply_readiness(self.readiness, now_ns=NOW)
        self.assertEqual(snapshot.overall, HealthState.OK)
        self.assertTrue(self.readiness.is_set(ReadinessSignal.HEALTH))

    def test_one_healthy_event_is_not_enough(self):
        self.prime_ok(health_events=1)
        snapshot = self.engine.apply_readiness(self.readiness, now_ns=NOW)
        self.assertEqual(snapshot.overall, HealthState.OK)
        self.assertFalse(self.readiness.is_set(ReadinessSignal.HEALTH))

    def test_health_readiness_does_not_arm_execution(self):
        self.prime_ok()
        self.engine.apply_readiness(self.readiness, now_ns=NOW)
        self.assertTrue(self.readiness.is_set(ReadinessSignal.HEALTH))
        self.assertFalse(self.readiness.is_set(ReadinessSignal.RISK))
        self.assertFalse(self.readiness.is_set(ReadinessSignal.EXECUTION_ARMED))
        self.assertFalse(self.readiness.live_execution_ready)

    def test_blocked_explicit_dimension_blocks(self):
        self.prime_ok()
        payload = self.health()
        payload["journal_health"] = 3
        self.engine.observe_health_event(payload, observed_at_ns=NOW)
        snapshot = self.engine.apply_readiness(self.readiness, now_ns=NOW)
        self.assertEqual(snapshot.journal, HealthState.BLOCKED)
        self.assertFalse(self.readiness.is_set(ReadinessSignal.HEALTH))

    def test_stale_heartbeat_blocks(self):
        self.prime_ok()
        snapshot = self.engine.apply_readiness(
            self.readiness,
            now_ns=NOW + 6_000_000_000,
        )
        self.assertEqual(snapshot.transport, HealthState.BLOCKED)

    def test_critical_queue_capacity_blocks(self):
        self.prime_ok()
        self.engine.observe_heartbeat(
            self.heartbeat(critical=2048),
            observed_at_ns=NOW,
        )
        snapshot = self.engine.apply_readiness(self.readiness, now_ns=NOW)
        self.assertEqual(snapshot.transport, HealthState.BLOCKED)
        self.assertIn("CRITICAL_QUEUE_FULL", {r.code for r in snapshot.reasons})

    def test_critical_queue_pressure_degrades(self):
        self.prime_ok()
        self.engine.observe_heartbeat(
            self.heartbeat(critical=1536),
            observed_at_ns=NOW,
        )
        snapshot = self.engine.apply_readiness(self.readiness, now_ns=NOW)
        self.assertEqual(snapshot.transport, HealthState.DEGRADED)

    def test_market_queue_pressure_degrades(self):
        self.prime_ok()
        self.engine.observe_heartbeat(
            self.heartbeat(market=4096),
            observed_at_ns=NOW,
        )
        snapshot = self.engine.apply_readiness(self.readiness, now_ns=NOW)
        self.assertEqual(snapshot.transport, HealthState.DEGRADED)

    def test_stale_broker_observation_blocks_data(self):
        self.prime_ok()
        self.engine.observe_heartbeat(
            self.heartbeat(broker_ns=NOW - 6_000_000_000),
            observed_at_ns=NOW,
        )
        snapshot = self.engine.apply_readiness(self.readiness, now_ns=NOW)
        self.assertEqual(snapshot.data, HealthState.BLOCKED)

    def test_terminal_disconnect_blocks(self):
        self.prime_ok()
        self.engine.observe_session_state(self.session(connected=0))
        snapshot = self.engine.apply_readiness(self.readiness, now_ns=NOW)
        self.assertEqual(snapshot.transport, HealthState.BLOCKED)
        self.assertEqual(snapshot.execution, HealthState.BLOCKED)

    def test_open_session_without_fresh_tick_degrades_data(self):
        self.prime_ok()
        self.engine.observe_session_state(self.session(fresh_tick=0))
        snapshot = self.engine.apply_readiness(self.readiness, now_ns=NOW)
        self.assertEqual(snapshot.data, HealthState.DEGRADED)

    def test_closed_session_trade_permission_false_does_not_block(self):
        self.prime_ok()
        self.engine.observe_session_state(
            self.session(session_open=0, fresh_tick=0, trade_allowed=0)
        )
        snapshot = self.engine.apply_readiness(self.readiness, now_ns=NOW)
        self.assertEqual(snapshot.execution, HealthState.OK)

    def test_open_session_trade_permission_false_blocks(self):
        self.prime_ok()
        self.engine.observe_session_state(self.session(trade_allowed=0))
        snapshot = self.engine.apply_readiness(self.readiness, now_ns=NOW)
        self.assertEqual(snapshot.execution, HealthState.BLOCKED)

    def test_clock_skew_degrades_and_blocks(self):
        self.prime_ok()
        self.engine.observe_session_state(
            self.session(server_time=NOW - 3_000_000_000)
        )
        snapshot = self.engine.apply_readiness(self.readiness, now_ns=NOW)
        self.assertEqual(snapshot.clock, HealthState.DEGRADED)

        self.engine.observe_session_state(
            self.session(server_time=NOW - 11_000_000_000)
        )
        snapshot = self.engine.apply_readiness(self.readiness, now_ns=NOW)
        self.assertEqual(snapshot.clock, HealthState.BLOCKED)

    def test_high_ping_degrades_and_blocks(self):
        self.prime_ok()
        self.engine.observe_session_state(self.session(ping=300_000))
        self.assertEqual(
            self.engine.evaluate(now_ns=NOW).transport,
            HealthState.DEGRADED,
        )
        self.engine.observe_session_state(self.session(ping=1_100_000))
        self.assertEqual(
            self.engine.evaluate(now_ns=NOW).transport,
            HealthState.BLOCKED,
        )

    def test_high_rtt_degrades_and_blocks(self):
        self.prime_ok()
        self.engine.observe_transport_metrics(
            self.metrics(rtt=300_000),
            observed_at_ns=NOW,
        )
        self.assertEqual(
            self.engine.evaluate(now_ns=NOW).transport,
            HealthState.DEGRADED,
        )
        self.engine.observe_transport_metrics(
            self.metrics(rtt=1_100_000),
            observed_at_ns=NOW,
        )
        self.assertEqual(
            self.engine.evaluate(now_ns=NOW).transport,
            HealthState.BLOCKED,
        )

    def test_recent_decode_error_degrades_then_clears(self):
        self.prime_ok()
        self.engine.observe_transport_metrics(
            self.metrics(decode_errors=1),
            observed_at_ns=NOW + 1,
        )
        self.assertEqual(
            self.engine.evaluate(now_ns=NOW + 1).transport,
            HealthState.DEGRADED,
        )
        self.engine.observe_heartbeat(
            self.heartbeat(broker_ns=NOW + 11_000_000_001),
            observed_at_ns=NOW + 11_000_000_001,
        )
        self.engine.observe_health_event(
            self.health(),
            observed_at_ns=NOW + 11_000_000_001,
        )
        self.engine.observe_session_state(
            self.session(server_time=NOW + 11_000_000_001)
        )
        self.assertEqual(
            self.engine.evaluate(now_ns=NOW + 11_000_000_001).transport,
            HealthState.OK,
        )

    def test_stage08_data_not_fresh_blocks(self):
        self.prime_ok()
        self.engine.observe_data_fresh(False)
        snapshot = self.engine.apply_readiness(self.readiness, now_ns=NOW)
        self.assertEqual(snapshot.data, HealthState.BLOCKED)


if __name__ == "__main__":
    unittest.main()
