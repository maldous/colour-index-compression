import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

import cix.backend_portfolio as portfolio
from benchmarks.codec_profiles import SETTINGS
from cix.backend_portfolio import (
    HEADER, MAX_INPUT_BYTES, POLICY_EXCLUDED, REFERENCE_PRESETS,
    candidate_plan, coverage_table, decode_external_bytes,
    decode_portfolio, encode_external_bytes, encode_portfolio,
    native_cix_inventory, _select_smallest_verified,
)


POLICY_PATH = Path("docs/research/2026-09-30-codec-profiles/policy.json")


def policy():
    return json.loads(POLICY_PATH.read_text())


def test_presets_are_the_ranked_reference_settings():
    expected = {
        profile: {name: SETTINGS[profile][name] for name in ("gzip", "bzip2", "xz", "zstd", "brotli")}
        for profile in ("fast", "current", "size")
    }
    assert REFERENCE_PRESETS == expected


@pytest.mark.parametrize("profile", ["fast", "current", "size"])
@pytest.mark.parametrize("backend", ["gzip", "zstd"])
def test_external_envelope_round_trip(profile, backend):
    data = (b"generic-byte-observable-data\x00\xff" * 97) + bytes(range(251))
    archive = encode_external_bytes(data, backend, profile, policy())
    assert len(archive) >= HEADER.size
    assert decode_external_bytes(archive, policy()) == data


@pytest.mark.parametrize("backend", ["bzip2", "xz"])
def test_balanced_external_envelope_round_trip(backend):
    data = bytes(range(256)) * 9
    archive = encode_external_bytes(data, backend, "current", policy())
    assert decode_external_bytes(archive, policy()) == data


def test_fast_brotli_quality_zero_round_trip():
    data = bytes(range(256)) * 9
    archive = encode_external_bytes(data, "brotli", "fast", policy())
    assert decode_external_bytes(archive, policy()) == data
    with pytest.raises(ValueError, match="not eligible"):
        encode_external_bytes(data, "brotli", "current", policy())


def test_envelope_rejects_corruption_and_limits():
    data = b"abc" * 100
    archive = bytearray(encode_external_bytes(data, "gzip", "fast", policy()))
    archive[-1] ^= 1
    with pytest.raises((ValueError, OSError, EOFError)):
        decode_external_bytes(bytes(archive), policy())
    with pytest.raises(ValueError, match="bounded"):
        encode_external_bytes(b"x" * (MAX_INPUT_BYTES + 1), "gzip", "fast", policy())


def test_size_plan_has_all_four_backends_and_all_eleven_routes():
    plan = candidate_plan("size")
    names = [item["name"] for item in plan]
    assert [name for name in names if name.endswith(":direct")] == [
        "gzip:direct", "bzip2:direct", "xz:direct", "zstd:direct"
    ]
    assert {name.removeprefix("cix-route:") for name in names if name.startswith("cix-route:")} == {
        "raw", "runs", "composition", "lz", "predictor", "bwt", "stride",
        "phrases", "ppm", "mixture", "deflate",
    }
    assert "cix-adaptive" in names
    direct_end = names.index("cix-adaptive")
    assert all(name == "cix-route:raw" or name.endswith(":direct") for name in names[:direct_end])


def test_fast_shortlist_and_disabled_controls_are_explicit():
    names = [item["name"] for item in candidate_plan("fast")]
    assert names == ["cix-route:raw", "gzip:direct", "zstd:direct", "brotli:direct", "cix-adaptive"]
    disabled = [item["name"] for item in candidate_plan("current", disabled=("zstd", "cix-adaptive"))]
    assert "zstd:direct" not in disabled
    assert "cix-adaptive" not in disabled
    assert "cix-route:raw" in disabled


def test_every_ablation_keeps_the_raw_original_byte_fallback():
    names = [item["name"] for item in candidate_plan(
        "size", disabled=("cix", "cix-route:raw", "gzip", "bzip2", "xz", "zstd"),
        routes=(),
    )]
    assert names == ["cix-route:raw"]


def test_selection_uses_complete_verified_bytes_only():
    attempts = [
        {"name": "small-failed", "status": "VERIFY_FAILED", "archive_bytes": 8, "plan_index": 0},
        {"name": "larger", "status": "VERIFIED", "archive_bytes": 40, "plan_index": 1},
        {"name": "smallest-qualified", "status": "VERIFIED", "archive_bytes": 30, "plan_index": 2},
        {"name": "timeout", "status": "TIME_BUDGET", "archive_bytes": None, "plan_index": 3},
    ]
    assert _select_smallest_verified(attempts)["name"] == "smallest-qualified"


def test_coverage_records_policy_and_memory_exclusions():
    rows = {row["codec"]: row for row in coverage_table(policy())}
    assert rows["zstd"]["available_inside_cix"]
    assert rows["brotli"]["profile_eligibility"]["fast"] == "ELIGIBLE_QUALITY_0_DICTIONARY_FREE"
    assert rows["brotli"]["profile_eligibility"]["size"] == "POLICY_EXCLUDED_STATIC_DICTIONARY"
    assert "dictionary" in rows["brotli"]["integration_gap"].lower()
    assert rows["paq8px"]["profile_eligibility"]["size"].startswith("POLICY_EXCLUDED_AND_MEMORY_EXCLUDED")
    assert "content-specific" in rows["paq8px"]["integration_gap"]
    assert "not, by itself" in rows["paq8px"]["integration_gap"]
    assert set(POLICY_EXCLUDED) == {"brotli-quality-6-11", "paq8px"}


def test_native_inventory_does_not_conflate_cixg1_and_cixm6():
    rows = {row["format"]: row for row in native_cix_inventory()}
    assert rows["CIXG1"]["status"] == "PORTFOLIO_INTEGRATED"
    assert len(rows["CIXG1"]["routes"]) == 11
    assert rows["CIXM6"]["status"] == "AVAILABLE_STANDALONE_NOT_INTEGRATED"


def test_portfolio_raw_fallback_is_complete_and_dispatches(tmp_path):
    source = tmp_path / "source.bin"
    archive = tmp_path / "selected.cix"
    restored = tmp_path / "restored.bin"
    data = (b"fallback-check\x00" * 43) + bytes(range(31))
    source.write_bytes(data)
    report = encode_portfolio(
        source, archive, profile="fast", policy=policy(),
        disabled=("gzip", "zstd", "brotli", "cix-adaptive"),
    )
    assert report["selected"] == "cix-route:raw"
    assert report["attempts"][0]["status"] == "VERIFIED"
    source.unlink()
    decoded = decode_portfolio(archive, restored, policy=policy())
    assert decoded["decoded_sha256"] == report["source_sha256"]
    assert restored.read_bytes() == data


def test_unexpected_verification_failure_stops_and_preserves_archive(tmp_path, monkeypatch):
    source = tmp_path / "source.bin"; source.write_bytes(b"verification-failure")
    attempts = tmp_path / "attempts"

    def fake_worker(target, args, timeout):
        if target is portfolio._worker_encode:
            archive = Path(args[1]); archive.parent.mkdir(parents=True, exist_ok=True)
            archive.write_bytes(b"invalid-completed-archive")
            return {"status": "COMPLETE", "archive_bytes": archive.stat().st_size,
                    "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
                    "wall_seconds": 0.01, "encode_seconds": 0.01,
                    "peak_rss_kib": 1, "detail": {"standalone_payload_bytes": 25, "wrapper_bytes": 0}}
        return {"status": "VERIFY_FAILED", "error": "ValueError: deliberate corruption",
                "wall_seconds": 0.01, "decode_seconds": 0.01}

    monkeypatch.setattr(portfolio, "_run_worker", fake_worker)
    with pytest.raises(portfolio.CandidateVerificationError) as failure:
        portfolio.encode_portfolio(
            source, tmp_path / "selected.cix", profile="fast", policy=policy(),
            disabled=("gzip", "zstd", "brotli", "cix-adaptive"),
            attempt_directory=attempts,
        )
    assert failure.value.attempt["status"] == "VERIFY_FAILED"
    assert (attempts / failure.value.attempt["archive_name"]).read_bytes() == b"invalid-completed-archive"
    assert not (tmp_path / "selected.cix").exists()


def test_validation_timeout_is_unqualified_and_does_not_hide_next_verified_candidate(tmp_path, monkeypatch):
    source = tmp_path / "source.bin"; data = b"timeout-is-not-corruption"; source.write_bytes(data)
    verify_count = 0

    def fake_worker(target, args, timeout):
        nonlocal verify_count
        if target is portfolio._worker_encode:
            item = args[2]; archive = Path(args[1]); payload = b"r" * (20 if item["name"] == "cix-route:raw" else 10)
            archive.parent.mkdir(parents=True, exist_ok=True); archive.write_bytes(payload)
            return {"status": "COMPLETE", "archive_bytes": len(payload),
                    "archive_sha256": hashlib.sha256(payload).hexdigest(),
                    "wall_seconds": 0.01, "encode_seconds": 0.01,
                    "peak_rss_kib": 1, "detail": {"standalone_payload_bytes": len(payload), "wrapper_bytes": 0}}
        assert args[0] == len(data)
        assert args[1] == hashlib.sha256(data).hexdigest()
        assert str(source) not in args
        verify_count += 1
        if verify_count == 1:
            return {"status": "TIME_BUDGET", "wall_seconds": timeout}
        return {"status": "VERIFIED", "wall_seconds": 0.01, "decode_seconds": 0.01,
                "restored_bytes": len(data), "restored_sha256": hashlib.sha256(data).hexdigest(),
                "peak_rss_kib": 1}

    monkeypatch.setattr(portfolio, "_run_worker", fake_worker)
    report = portfolio.encode_portfolio(
        source, tmp_path / "selected.cix", profile="fast", policy=policy(),
        disabled=("zstd", "brotli", "cix-adaptive"),
        attempt_directory=tmp_path / "attempts",
    )
    assert report["attempts"][0]["status"] == "UNQUALIFIED"
    assert report["attempts"][0]["validation"]["status"] == "TIME_BUDGET"
    assert report["selected"] == "gzip:direct"


def _worker_leaving_descendant(conn, pid_path):
    os.setsid(); conn.send({"ready": True})
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    Path(pid_path).write_text(str(child.pid))
    conn.send({"status": "COMPLETE"}); conn.close()


def test_completed_worker_process_group_does_not_leave_running_descendant(tmp_path):
    pid_path = tmp_path / "child.pid"
    result = portfolio._run_worker(_worker_leaving_descendant, (str(pid_path),), 1.0)
    assert result["status"] == "COMPLETE"
    child_pid = int(pid_path.read_text())
    running = True
    for _ in range(50):
        stat = Path(f"/proc/{child_pid}/stat")
        if not stat.exists() or stat.read_text().split()[2] == "Z":
            running = False; break
        time.sleep(0.01)
    assert not running
