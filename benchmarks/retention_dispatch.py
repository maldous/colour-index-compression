#!/usr/bin/env python3
"""Resume frozen retention cells with corrected terminal-log classification.

This wrapper changes orchestration only.  It imports the frozen experiment
harness, replaces its failure classifier, and calls the existing ``run``.  The
WaveScheduler still skips every claimed/terminal cell, so this cannot retry the
first twelve identities or change any manifest, encoder, decoder, budget, or
source snapshot.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from benchmarks import retention_round as frozen


def failure_details(terminal_path: Path, receipt: dict) -> tuple[str, str]:
    destination = Path(terminal_path).parent
    # ``*.stderr.log`` does not match a file named exactly ``stderr.log``.
    # Preserve both outer systemd logs and nested repetition logs.
    logs = sorted(set(destination.rglob("*.stderr.log")) |
                  set(destination.rglob("stderr.log")))
    contents = [(path, path.read_text(errors="replace")) for path in logs]
    phase_stops = [str(phase.get("stop_reason")) for phase in receipt.get("phases", [])
                   if isinstance(phase, dict) and phase.get("stop_reason")]

    # A path mentioned by an outer traceback is not evidence of a route budget
    # event.  Require the marker in retained log content itself.
    markers = {marker for _, text in contents for marker in
               ("TIME_BUDGET", "SEARCH_BUDGET", "MemoryError", "WORKER_EXIT")
               if marker in text}
    if markers & {"TIME_BUDGET", "SEARCH_BUDGET"}:
        return "UNQUALIFIED", "confirmed internal route/search budget marker in retained stderr"
    if "MemoryError" in markers or any(stop == "memory_budget_exhausted" for stop in phase_stops):
        return "RESOURCE_LIMIT", "confirmed memory budget marker or cgroup stop reason"
    if any(stop in ("wall_budget_exhausted", "temp_budget_exhausted") for stop in phase_stops):
        return "RESOURCE_LIMIT", "confirmed outer wall/temp cgroup stop reason"
    # WORKER_EXIT alone is not promoted to a resource exclusion: it can also
    # indicate an implementation fault and therefore stops subsequent waves.
    return "UNEXPECTED_FAILURE", "no confirmed timeout or resource marker in retained evidence"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", action="append", required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    args = parser.parse_args()
    frozen._failure_details = failure_details
    frozen.run(set(args.stage), args.authorization)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
