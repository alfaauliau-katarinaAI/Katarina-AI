"""WP12 Tahap 0: MT5 server-time ticks become verified causal UTC; no orders."""
from datetime import datetime, timedelta, timezone
import unittest

from katarina.intelligence.broker.causal_broker_quotes import (
    last_past_quote, due_window_quote, server_epoch_to_utc,
    utc_to_server_datetime,
)

UTC = timezone.utc
NOW = datetime(2026, 10, 20, 12, 0, 10, tzinfo=UTC)


class ServerTickBroker:
    COPY_TICKS_INFO = 1

    def __init__(self, rows):
        self.rows, self.windows = rows, []

    def copy_ticks_range(self, symbol, start, end, flags):
        self.windows.append((start, end))
        return self.rows


def server_tick(utc_epoch, shift=3, bid=2000.0):
    return {"time_msc": int((utc_epoch + shift * 3600) * 1000),
            "bid": bid, "ask": bid + 0.1}


class VerifiedServerUtcTests(unittest.TestCase):
    def test_shift_three_converts_bidask_and_queries_server_clock(self):
        t = NOW.timestamp()
        broker = ServerTickBroker([server_tick(t-1), server_tick(t+1)])
        result = last_past_quote(broker, "EURUSD.vx", NOW, server_shift_hours=3)
        self.assertEqual(result, (2000.0, 2000.1, t-1))
        self.assertEqual(broker.windows[0][0], NOW + timedelta(hours=3, seconds=-90))
        self.assertEqual(broker.windows[0][1], NOW + timedelta(hours=3))
        self.assertEqual(utc_to_server_datetime(NOW, 3), NOW+timedelta(hours=3))
        self.assertEqual(server_epoch_to_utc(t+10800, 3), t)

    def test_due_window_uses_converted_utc_and_no_future_tick(self):
        t = NOW.timestamp()
        due = t - 30
        broker = ServerTickBroker([server_tick(due-1), server_tick(due+1), server_tick(t+1)])
        quote = due_window_quote(broker, "EURUSD.vx", due, t, server_shift_hours=3)
        self.assertEqual(quote[2], due+1)
        self.assertEqual(broker.windows[0][0].timestamp(), due+10800)

    def test_missing_or_invalid_shift_fails_closed(self):
        broker = ServerTickBroker([])
        with self.assertRaises(TypeError):
            last_past_quote(broker, "EURUSD.vx", NOW)
        for shift in (None, 1.5, -13, 15, True):
            with self.subTest(shift=shift), self.assertRaises(ValueError):
                last_past_quote(broker, "EURUSD.vx", NOW, server_shift_hours=shift)
        with self.assertRaises(ValueError):
            utc_to_server_datetime(NOW.replace(tzinfo=None), 3)
        with self.assertRaises(ValueError):
            server_epoch_to_utc(float("nan"), 3)


if __name__ == "__main__":
    unittest.main()
