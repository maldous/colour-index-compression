import tempfile
import time
import multiprocessing
from pathlib import Path
import unittest
from unittest.mock import patch

from cix_runtime.engine import decode, encode, raw_encode
from cix_runtime.model import Candidate


def _slow_frame(data):
    time.sleep(0.15)
    return raw_encode(data)


def _fast_frame(data):
    return raw_encode(data)


def _broken_frame(_):
    raise ValueError("malformed optional candidate")


class EngineTests(unittest.TestCase):
    def test_paid_selection_ties_and_failure_evidence(self):
        data = b"unknown bytes\x00\xff"
        frame = raw_encode(data)
        def broken(_):
            raise ValueError("malformed optional candidate")
        candidates = [
            Candidate("first", "test", lambda _: frame, 1000, 1000),
            Candidate("tie", "test", lambda _: frame, 1000, 1000),
            Candidate("over-budget", "test", lambda _: b"short", 10**12, 1000),
            Candidate("broken", "test", broken, 1000, 1000),
        ]
        with tempfile.TemporaryDirectory() as work:
            result, report = encode(data, candidates=candidates, progress_path=Path(work)/"progress.json")
        self.assertEqual(result, frame)
        self.assertEqual(report["selected"], "first")
        self.assertEqual([x["status"] for x in report["trials"]],
                         ["completed", "completed", "budget-omitted", "failed"])
        self.assertEqual(decode(result), data)

    def test_raw_integrity_and_bounds(self):
        frame = raw_encode(b"abcdef")
        with self.assertRaises(ValueError):
            decode(frame, max_output_bytes=5)
        with self.assertRaises(ValueError):
            decode(frame + b"trailing")
        with self.assertRaises(ValueError):
            decode(frame[:-1] + b"!")

    def test_resource_admitted_parallel_trials_keep_priority_ties(self):
        data = b"parallel candidate input"
        candidates = [
            Candidate("first-slow", "test", _slow_frame, 64 << 20, 64 << 20),
            Candidate("second-fast", "test", _fast_frame, 64 << 20, 64 << 20),
            Candidate("broken", "test", _broken_frame, 64 << 20, 64 << 20),
        ]
        result, report = encode(data, candidates=candidates, memory_bytes=160 << 20)
        self.assertEqual(result, raw_encode(data))
        self.assertEqual(report["selected"], "first-slow")
        self.assertGreaterEqual(report["strategy"]["maximum_inflight"], 2)
        self.assertEqual([row["id"] for row in report["trials"]],
                         ["first-slow", "second-fast", "broken"])
        self.assertEqual([row["status"] for row in report["trials"]],
                         ["completed", "completed", "failed"])

    def test_progress_failure_reaps_running_workers(self):
        before = {process.pid for process in multiprocessing.active_children()}
        candidate = Candidate("slow", "test", _slow_frame, 64 << 20, 64 << 20)
        with patch("cix_runtime.engine._write_progress", side_effect=OSError("report unavailable")):
            with self.assertRaisesRegex(OSError, "report unavailable"):
                encode(b"failure fixture", candidates=[candidate])
        self.assertEqual(before, {process.pid for process in multiprocessing.active_children()})


if __name__ == "__main__":
    unittest.main()
