#!/usr/bin/env python3
"""Run an isolated copy of the frozen pipe probe against audit binaries."""

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "benchmarks" / "cix_stream_latency_probe.py"
SPEC = importlib.util.spec_from_file_location("stream_latency_probe", SOURCE)
assert SPEC and SPEC.loader
PROBE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROBE)
PROBE.CIX = Path("/tmp/cix-gstream-candidate-target/release/cix")
PROBE.UNCIX = Path("/tmp/cix-gstream-candidate-target/release/uncix")
PROBE.CPU = 12

raise SystemExit(PROBE.main())
