"""Fail-closed tests for broker session evidence acquisition.

These are synthetic CSV fixtures; passing them does not certify broker hours.
"""
import csv
import io
import unittest

from scripts.research.build_stage0_session_candidate import build_candidate, FIELDS


def fixture():
    result = io.StringIO()
    writer = csv.DictWriter(result, fieldnames=FIELDS, delimiter=";", lineterminator="\r\n")
    writer.writeheader()
    common = {
        "broker_server": "ResearchServer-1",
        "captured_host_utc": "2026.11.12 12:00:00",
        "broker_wall_time": "2026.11.12 14:00:00",
    }
    writer.writerow({**common, "record_type": "META", "status": "HOST_CLOCK_UNVERIFIED"})
    for day in range(7):
        for kind in ("quote", "trade"):
            if day == 0:
                writer.writerow({
                    **common, "record_type": "SESSION",
                    "symbol": "XAUUSD.vx", "weekday_mon0": day, "kind": kind,
                    "session_index": 0, "from_seconds": 3600, "to_seconds": 86400,
                    "status": "REPORTED",
                })
            else:
                writer.writerow({
                    **common, "record_type": "NO_SESSION_OR_UNAVAILABLE",
                    "symbol": "XAUUSD.vx", "weekday_mon0": day, "kind": kind,
                    "session_index": 0, "status": "UNVERIFIED",
                })
    return result.getvalue().encode("utf-8")


class Stage0SessionCaptureTests(unittest.TestCase):
    def test_candidate_never_claims_history_or_holidays_verified(self):
        candidate = build_candidate(fixture(), ["XAUUSD.vx"])
        self.assertIsNone(candidate["valid_from_utc"])
        self.assertIsNone(candidate["valid_until_utc"])
        self.assertEqual(candidate["verified_broker_dates"], [])
        monday = candidate["symbols"]["XAUUSD.vx"]["quote"]["0"]
        self.assertEqual(monday, [[3600, 86400]])
        self.assertIsNone(candidate["symbols"]["XAUUSD.vx"]["quote"]["6"])
        self.assertEqual(len(candidate["broker_server_sha256"]), 64)
        self.assertEqual(len(candidate["source_sha256"]), 64)

    def test_missing_row_never_counted_as_closed(self):
        rows = fixture().decode("utf-8").splitlines(keepends=True)
        with self.assertRaisesRegex(ValueError, "UNIVERSE_INCOMPLETE"):
            build_candidate("".join(rows[:-1]).encode(), ["XAUUSD.vx"])

    def test_duplicate_session_is_blocked(self):
        rows = fixture().decode("utf-8").splitlines(keepends=True)
        rows.append(rows[2])
        with self.assertRaisesRegex(ValueError, "DUPLICATE"):
            build_candidate("".join(rows).encode(), ["XAUUSD.vx"])

    def test_error_or_truncated_probe_is_blocked(self):
        rows = fixture().decode("utf-8").splitlines(keepends=True)
        rows[2] = rows[2].replace("SESSION;", "SESSION_LIMIT_REACHED;")
        with self.assertRaisesRegex(ValueError, "INCOMPLETE_OR_ERROR"):
            build_candidate("".join(rows).encode(), ["XAUUSD.vx"])

    def test_extra_symbol_and_malformed_overnight_rejected(self):
        rows = fixture().decode("utf-8").splitlines(keepends=True)
        rows[2] = rows[2].replace("XAUUSD.vx", "OTHER.vx")
        with self.assertRaisesRegex(ValueError, "SYMBOL_INVALID"):
            build_candidate("".join(rows).encode(), ["XAUUSD.vx"])
        rows = fixture().decode("utf-8").splitlines(keepends=True)
        rows[2] = rows[2].replace(";3600;86400;", ";3600;172801;")
        with self.assertRaisesRegex(ValueError, "INTERVAL_INVALID"):
            build_candidate("".join(rows).encode(), ["XAUUSD.vx"])

    def test_two_broker_snapshots_must_not_mix(self):
        rows = fixture().decode("utf-8").splitlines(keepends=True)
        rows[2] = rows[2].replace("ResearchServer-1", "OtherServer")
        with self.assertRaisesRegex(ValueError, "MIXED_SNAPSHOT"):
            build_candidate("".join(rows).encode(), ["XAUUSD.vx"])


if __name__ == "__main__":
    unittest.main()
