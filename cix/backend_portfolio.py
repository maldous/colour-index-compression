"""Bounded reference-backend portfolio around the frozen CIXG1 pipeline.

This module does not add reference codecs to CIXG1 substreams.  It evaluates
complete, self-contained alternatives and retains the smallest archive that
completed and restored exactly.  External payloads have a fixed 47-byte CIXB1
envelope; native CIXG1 archives remain byte-for-byte unchanged.

The policy is deliberately byte-observable.  Candidate eligibility depends
only on the declared profile, never on a path, filename, corpus, hash, MIME
type, language, or processor architecture.
"""
from __future__ import annotations

import bz2
import argparse
import gzip
import hashlib
import json
import lzma
import multiprocessing as mp
import os
import resource
import shutil
import signal
import struct
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Iterable, Mapping

from .pipeline import (EFFORTS, END as CIXG1_END, FRAME as CIXG1_FRAME,
                       HEADER as CIXG1_HEADER, MAGIC as CIXG1_MAGIC, ROUTES,
                       decode_file, encode_file)


MAGIC = b"CIXB1"
HEADER = struct.Struct("<5sBBII32s")
assert HEADER.size == 47

BACKENDS = {1: "gzip", 2: "bzip2", 3: "xz", 4: "zstd", 5: "brotli"}
BACKEND_IDS = {name: ident for ident, name in BACKENDS.items()}
PROFILES = {1: "fast", 2: "current", 3: "size"}
PROFILE_IDS = {name: ident for ident, name in PROFILES.items()}
PROFILE_EFFORT = {"fast": "fast", "current": "balanced", "size": "maximum"}

# Copied from benchmarks.codec_profiles.SETTINGS.  A focused test asserts exact
# equality so the integration cannot silently drift from the ranked controls.
REFERENCE_PRESETS = {
    "fast": {
        "gzip": {"level": 1}, "bzip2": {"level": 1},
        "xz": {"level": 0}, "zstd": {"level": -131072},
        "brotli": {"level": 0},
    },
    "current": {
        "gzip": {"level": 9}, "bzip2": {"level": 9},
        "xz": {"level": 6}, "zstd": {"level": 3},
        "brotli": {"level": 6},
    },
    "size": {
        "gzip": {"level": 9}, "bzip2": {"level": 9},
        "xz": {"level": 9, "extreme": True}, "zstd": {"level": 22},
        "brotli": {"level": 11},
    },
}

# Fast is intentionally a small fixed shortlist.  Current and size make every
# policy-compatible integrated reference backend eligible.  Maximum adds an
# exhaustive pass over the eleven existing CIXG1 representations.
PROFILE_BACKENDS = {
    "fast": ("gzip", "zstd", "brotli"),
    "current": ("gzip", "bzip2", "xz", "zstd"),
    "size": ("gzip", "bzip2", "xz", "zstd"),
}
PORTFOLIO_SECONDS = {"fast": 0.75, "current": 3.0, "size": 60.0}
OUTER_MEMORY_BYTES = 2_000_000_000
MAX_INPUT_BYTES = 16 * 1024 * 1024
MAX_EXTERNAL_PAYLOAD_BYTES = MAX_INPUT_BYTES + 1024 * 1024

POLICY_EXCLUDED = {
    "brotli-quality-6-11": (
        "Brotli qualities 6 and 11 can use RFC 7932's built-in static word "
        "dictionary and are outside the generic-input policy.  Quality 0 is "
        "separately eligible because upstream v1.2.0 routes it through the "
        "dictionary-free BrotliCompressFragmentFast path."
    ),
    "paq8px": (
        "The ranked PAQ presets use content-specific models, which are outside "
        "the generic backend policy.  Their pinned AVX2 setting is an "
        "implementation choice and is not, by itself, the exclusion reason."
    ),
}

BROTLI_RUNTIME = {
    "version": "1.2.0",
    "python_wrapper_sha256": "813610bf0d74a6998d7b47d912e8892c3896e6eac19cb7b22575e04fc294b63f",
    "extension_sha256": "ba62b6a5823ee9832364171021d27f5f93cb423d38ae090ce84a7b696f688169",
    "source_evidence": [
        "https://raw.githubusercontent.com/google/brotli/v1.2.0/c/enc/quality.h",
        "https://raw.githubusercontent.com/google/brotli/v1.2.0/c/enc/encode.c",
        "https://raw.githubusercontent.com/google/brotli/v1.2.0/c/enc/compress_fragment.c",
    ],
}


class CandidateVerificationError(RuntimeError):
    """A completed candidate failed exact archive-only restoration."""

    def __init__(self, attempt: dict, attempts: list[dict], work_directory: Path):
        super().__init__(f"candidate verification failed: {attempt['name']}: {attempt['status']}")
        self.attempt = attempt
        self.attempts = attempts
        self.work_directory = str(work_directory)


def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _validate_profile(profile: str) -> None:
    if profile not in PROFILE_IDS:
        raise ValueError(f"unknown profile: {profile}")


def _zstd_binary(policy: Mapping) -> Path:
    record = policy.get("zstd")
    if not isinstance(record, Mapping):
        raise ValueError("policy is missing zstd provenance")
    binary = Path(str(record.get("path", "")))
    expected = str(record.get("sha256", ""))
    if not binary.is_file() or not expected or _sha256_path(binary) != expected:
        raise ValueError("zstd binary is absent or differs from the pinned policy")
    return binary


def _brotli_module():
    import brotli
    import _brotli
    if getattr(brotli, "__version__", None) != BROTLI_RUNTIME["version"]:
        raise ValueError("Brotli runtime differs from pinned v1.2.0")
    if (_sha256_path(Path(brotli.__file__)) != BROTLI_RUNTIME["python_wrapper_sha256"] or
            _sha256_path(Path(_brotli.__file__)) != BROTLI_RUNTIME["extension_sha256"]):
        raise ValueError("Brotli runtime files differ from the pinned policy")
    return brotli


def coverage_table(policy: Mapping) -> list[dict]:
    """Return the explicit integration and decoder-closure inventory."""
    try:
        zstd = _zstd_binary(policy)
        zstd_available = True
        zstd_gap = None
        zstd_requirement = {
            "format": "Zstandard frame",
            "binary_sha256": policy["zstd"]["sha256"],
            "version": policy["zstd"].get("version"),
            "runtime_path_required": False,
            "runtime_binary": zstd.name,
        }
    except ValueError as exc:
        zstd_available = False
        zstd_gap = str(exc)
        zstd_requirement = None
    try:
        _brotli_module()
        brotli_available = True
        brotli_gap = None
    except (ImportError, ValueError) as exc:
        brotli_available = False
        brotli_gap = str(exc)
    rows = [
        {
            "codec": "gzip", "available_inside_cix": True,
            "profile_eligibility": {p: "ELIGIBLE" if "gzip" in PROFILE_BACKENDS[p] else "SHORTLISTED_OUT" for p in PROFILES.values()},
            "integration_gap": None,
            "decoder_requirements": "RFC 1952 gzip decoder; benchmark bytes produced by Python gzip.compress with mtime=0",
        },
        {
            "codec": "bzip2", "available_inside_cix": True,
            "profile_eligibility": {p: "ELIGIBLE" if "bzip2" in PROFILE_BACKENDS[p] else "SHORTLISTED_OUT" for p in PROFILES.values()},
            "integration_gap": None,
            "decoder_requirements": "bzip2-compatible decoder; benchmark bytes produced by Python bz2",
        },
        {
            "codec": "xz", "available_inside_cix": True,
            "profile_eligibility": {p: "ELIGIBLE" if "xz" in PROFILE_BACKENDS[p] else "SHORTLISTED_OUT" for p in PROFILES.values()},
            "integration_gap": None,
            "decoder_requirements": "XZ/LZMA2-compatible decoder; benchmark bytes produced by Python lzma/liblzma",
        },
        {
            "codec": "zstd", "available_inside_cix": zstd_available,
            "profile_eligibility": {p: "ELIGIBLE" if zstd_available and "zstd" in PROFILE_BACKENDS[p] else "UNAVAILABLE" if not zstd_available else "SHORTLISTED_OUT" for p in PROFILES.values()},
            "integration_gap": zstd_gap,
            "decoder_requirements": zstd_requirement,
        },
        {
            "codec": "brotli", "available_inside_cix": brotli_available,
            "profile_eligibility": {
                "fast": "ELIGIBLE_QUALITY_0_DICTIONARY_FREE" if brotli_available else "UNAVAILABLE_PINNED_RUNTIME",
                "current": "POLICY_EXCLUDED_STATIC_DICTIONARY",
                "size": "POLICY_EXCLUDED_STATIC_DICTIONARY",
            },
            "integration_gap": brotli_gap or POLICY_EXCLUDED["brotli-quality-6-11"],
            "decoder_requirements": {**BROTLI_RUNTIME, "runtime_path_required": False} if brotli_available else None,
        },
        {
            "codec": "paq8px", "available_inside_cix": False,
            "profile_eligibility": {
                "fast": "POLICY_EXCLUDED", "current": "POLICY_EXCLUDED",
                "size": "POLICY_EXCLUDED_AND_MEMORY_EXCLUDED_29GB_GT_12GB",
            },
            "integration_gap": POLICY_EXCLUDED["paq8px"],
            "decoder_requirements": None,
        },
    ]
    return rows


def native_cix_inventory() -> list[dict]:
    """Identify native routes without implying that all share one format."""
    return [
        {
            "format": "CIXG1", "status": "PORTFOLIO_INTEGRATED",
            "profiles": dict(PROFILE_EFFORT), "routes": list(ROUTES.values()),
            "backends": ["raw", "runs", "cix-exact-1024", "deflate", "adaptive-range", "same-count-range-1024"],
        },
        {
            "format": "CIXM6", "status": "AVAILABLE_STANDALONE_NOT_INTEGRATED",
            "profiles": {"fast": "level 1", "current": "level 5", "size": "level 9"},
            "reason": "CIXM6 is a separate 21-mode stream format; this bounded change leaves its established selector untouched.",
        },
    ]


def _external_payload(data: bytes, backend: str, profile: str, policy: Mapping, work: Path) -> bytes:
    setting = REFERENCE_PRESETS[profile][backend]
    if backend == "gzip":
        return gzip.compress(data, compresslevel=setting["level"], mtime=0)
    if backend == "bzip2":
        return bz2.compress(data, compresslevel=setting["level"])
    if backend == "xz":
        preset = setting["level"] | (lzma.PRESET_EXTREME if setting.get("extreme") else 0)
        return lzma.compress(data, preset=preset)
    if backend == "zstd":
        binary = _zstd_binary(policy)
        source = work / "zstd.source"
        payload = work / "zstd.payload"
        source.write_bytes(data)
        args = [str(binary), "--single-thread", "--no-asyncio", "-q", "-f"]
        level = setting["level"]
        args += ["--ultra", "-22"] if level == 22 else [f"--fast={-level}"] if level < 0 else [f"-{level}"]
        subprocess.run(args + [str(source), "-o", str(payload)], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        return payload.read_bytes()
    if backend == "brotli":
        if profile != "fast" or setting["level"] != 0:
            raise ValueError("only dictionary-free Brotli quality 0 is policy eligible")
        return _brotli_module().compress(data, quality=0)
    raise ValueError(f"backend is not integrated: {backend}")


def encode_external_bytes(data: bytes, backend: str, profile: str, policy: Mapping) -> bytes:
    """Encode one exact reference preset and include all CIX dispatch metadata."""
    _validate_profile(profile)
    if backend not in BACKEND_IDS or backend not in PROFILE_BACKENDS[profile]:
        raise ValueError(f"backend {backend!r} is not eligible for {profile}")
    if len(data) > MAX_INPUT_BYTES:
        raise ValueError("input exceeds bounded backend-portfolio limit")
    with tempfile.TemporaryDirectory(prefix="cix-backend-") as directory:
        payload = _external_payload(data, backend, profile, policy, Path(directory))
    if len(payload) > MAX_EXTERNAL_PAYLOAD_BYTES:
        raise ValueError("external payload exceeds bounded archive limit")
    return HEADER.pack(MAGIC, BACKEND_IDS[backend], PROFILE_IDS[profile], len(data),
                       len(payload), hashlib.sha256(data).digest()) + payload


def _bounded_decompressor(payload: bytes, expected: int, kind: str) -> bytes:
    if kind == "gzip":
        import zlib
        decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
        data = decoder.decompress(payload, expected + 1)
        if len(data) != expected or not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
            raise ValueError("gzip length or framing mismatch")
        return data
    if kind == "bzip2":
        decoder = bz2.BZ2Decompressor()
        data = decoder.decompress(payload, max_length=expected + 1)
        if len(data) != expected or not decoder.eof or decoder.unused_data:
            raise ValueError("bzip2 length or framing mismatch")
        return data
    if kind == "xz":
        decoder = lzma.LZMADecompressor()
        data = decoder.decompress(payload, max_length=expected + 1)
        if len(data) != expected or not decoder.eof or decoder.unused_data:
            raise ValueError("xz length or framing mismatch")
        return data
    if kind == "brotli":
        data = _brotli_module().decompress(payload)
        if len(data) != expected:
            raise ValueError("brotli length mismatch")
        return data
    raise ValueError("not a bounded stdlib backend")


def _decode_zstd(payload: bytes, expected: int, policy: Mapping, work: Path) -> bytes:
    binary = _zstd_binary(policy)
    source = work / "zstd.payload"
    restored = work / "zstd.restored"
    source.write_bytes(payload)
    # The subprocess inherits this worker's file-size ceiling.  The explicit
    # postcondition also rejects concatenated or overlong output.
    subprocess.run([str(binary), "--single-thread", "--no-asyncio", "-q", "-f", "-d",
                    str(source), "-o", str(restored)], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if restored.stat().st_size != expected:
        raise ValueError("zstd length mismatch")
    return restored.read_bytes()


def decode_external_bytes(blob: bytes, policy: Mapping) -> bytes:
    if len(blob) < HEADER.size:
        raise ValueError("truncated CIXB1 archive")
    magic, backend_id, profile_id, expected, payload_size, digest = HEADER.unpack_from(blob)
    if magic != MAGIC or backend_id not in BACKENDS or profile_id not in PROFILES:
        raise ValueError("unsupported CIXB1 header")
    if expected > MAX_INPUT_BYTES or payload_size > MAX_EXTERNAL_PAYLOAD_BYTES:
        raise ValueError("CIXB1 resource limit")
    if len(blob) != HEADER.size + payload_size:
        raise ValueError("CIXB1 payload length mismatch")
    payload = blob[HEADER.size:]
    backend = BACKENDS[backend_id]
    try:
        if backend == "zstd":
            with tempfile.TemporaryDirectory(prefix="cix-backend-decode-") as directory:
                data = _decode_zstd(payload, expected, policy, Path(directory))
        else:
            data = _bounded_decompressor(payload, expected, backend)
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"{backend} payload failed to decode") from exc
    if hashlib.sha256(data).digest() != digest:
        raise ValueError("CIXB1 checksum mismatch")
    return data


def decode_archive(source: Path, destination: Path, policy: Mapping) -> dict:
    """Dispatch CIXG1 or CIXB1 without requiring the encoder's source path."""
    started = time.perf_counter()
    with source.open("rb") as stream:
        magic = stream.read(5)
    if magic == CIXG1_MAGIC:
        report = decode_file(source, destination)
        if report["decoded_bytes"] > MAX_INPUT_BYTES:
            destination.unlink(missing_ok=True)
            raise ValueError("decoded CIXG1 exceeds backend-portfolio limit")
        return {"format": "CIXG1", **report}
    if magic != MAGIC:
        raise ValueError("unknown backend-portfolio archive")
    blob = source.read_bytes()
    data = decode_external_bytes(blob, policy)
    destination.write_bytes(data)
    return {"format": "CIXB1", "decoded_bytes": len(data),
            "decoded_sha256": hashlib.sha256(data).hexdigest(),
            "decode_seconds": time.perf_counter() - started}


def candidate_plan(profile: str, *, disabled: Iterable[str] = (),
                   routes: Iterable[str] | None = None,
                   exhaustive_routes: bool | None = None) -> list[dict]:
    _validate_profile(profile)
    disabled = set(disabled)
    plan: list[dict] = []
    # The byte-for-byte raw CIXG1 fallback is not an optional model.  Backend
    # and route ablations may remove every compressor, but never this recovery
    # path.
    plan.append({"name": "cix-route:raw", "kind": "cix-route", "route": "raw"})
    for backend in PROFILE_BACKENDS[profile]:
        if backend not in disabled and f"{backend}:direct" not in disabled:
            plan.append({"name": f"{backend}:direct", "kind": "external", "backend": backend})
    if "cix" not in disabled and "cix-adaptive" not in disabled:
        plan.append({"name": "cix-adaptive", "kind": "cix-adaptive"})
    exhaustive = profile == "size" if exhaustive_routes is None else exhaustive_routes
    if exhaustive:
        selected_routes = list(ROUTES.values()) if routes is None else list(routes)
        unknown = set(selected_routes) - set(ROUTES.values())
        if unknown:
            raise ValueError(f"unknown routes: {sorted(unknown)}")
        for route in selected_routes:
            name = f"cix-route:{route}"
            if route == "raw" or "cix" in disabled or name in disabled:
                continue
            plan.append({"name": name, "kind": "cix-route", "route": route})
    return plan


def _encode_raw_cixg1(source: Path, destination: Path, effort: str) -> dict:
    """Write the mandatory original-byte fallback without running a search."""
    block_bytes = EFFORTS[effort].block_bytes
    whole = hashlib.sha256(); source_bytes = 0; blocks = 0
    started = time.perf_counter()
    with source.open("rb") as src, destination.open("wb") as dst:
        dst.write(CIXG1_HEADER.pack(CIXG1_MAGIC, block_bytes, 0))
        while data := src.read(block_bytes):
            digest = hashlib.sha256(data).digest()
            dst.write(CIXG1_FRAME.pack(0, len(data), len(data), digest))
            dst.write(data)
            whole.update(data); source_bytes += len(data); blocks += 1
        dst.write(CIXG1_FRAME.pack(CIXG1_END, 0, 0, whole.digest()))
    return {
        "format": "CIXG1", "effort": effort, "force": "raw",
        "source_bytes": source_bytes, "source_sha256": whole.hexdigest(),
        "compressed_bytes": destination.stat().st_size, "block_count": blocks,
        "encode_seconds": time.perf_counter() - started,
        "selection_total_seconds": 0.0,
        "search_and_launch_overhead_seconds": 0.0,
    }


def _worker_encode(conn, source: str, destination: str, item: dict,
                   profile: str, policy: dict) -> None:
    os.setsid()
    resource.setrlimit(resource.RLIMIT_AS, (OUTER_MEMORY_BYTES, OUTER_MEMORY_BYTES))
    conn.send({"ready": True})
    started = time.perf_counter()
    try:
        source_path = Path(source); destination_path = Path(destination)
        if item["kind"] == "external":
            data = source_path.read_bytes()
            archive = encode_external_bytes(data, item["backend"], profile, policy)
            destination_path.write_bytes(archive)
            detail = {"backend": item["backend"], "preset": REFERENCE_PRESETS[profile][item["backend"]],
                      "standalone_payload_bytes": len(archive) - HEADER.size,
                      "wrapper_bytes": HEADER.size}
            if item["backend"] == "zstd":
                detail.update(runtime_identity_verified=True, source_verified=True,
                              decoder_requirement=coverage_table(policy)[3]["decoder_requirements"])
            elif item["backend"] == "brotli":
                detail.update(runtime_identity_verified=True, source_verified=False,
                              source_verification_note="upstream q0 path audited; local wheel hash pinned without a reproducible-build attestation",
                              decoder_requirement={**BROTLI_RUNTIME, "runtime_path_required": False})
            else:
                detail.update(runtime_identity_verified=policy.get("python") == sys.version,
                              source_verified=False,
                              source_verification_note="standard format and exact Python runtime recorded; linked codec library binary not source-attested")
        elif item["kind"] == "cix-route" and item["route"] == "raw":
            detail = _encode_raw_cixg1(source_path, destination_path, PROFILE_EFFORT[profile])
            detail["standalone_payload_bytes"] = destination_path.stat().st_size
            detail["wrapper_bytes"] = 0
            detail["source_verified"] = True
        else:
            kwargs = {"effort": PROFILE_EFFORT[profile], "backend": "hybrid"}
            if item["kind"] == "cix-route":
                kwargs["force"] = item["route"]
            detail = encode_file(source_path, destination_path, **kwargs)
            detail["standalone_payload_bytes"] = destination_path.stat().st_size
            detail["wrapper_bytes"] = 0
            detail["source_verified"] = True
        conn.send({
            "status": "COMPLETE", "encode_seconds": time.perf_counter() - started,
            "archive_bytes": destination_path.stat().st_size,
            "archive_sha256": _sha256_path(destination_path), "detail": detail,
            "peak_rss_kib": max(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                                resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss),
        })
    except BaseException as exc:
        conn.send({"status": "FAILED", "error": f"{type(exc).__name__}: {exc}",
                   "encode_seconds": time.perf_counter() - started})
    finally:
        conn.close()


def _worker_verify(conn, expected_size: int, expected_hash: str,
                   archive: str, restored: str, policy: dict) -> None:
    os.setsid()
    resource.setrlimit(resource.RLIMIT_AS, (OUTER_MEMORY_BYTES, OUTER_MEMORY_BYTES))
    resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_INPUT_BYTES, MAX_INPUT_BYTES))
    conn.send({"ready": True})
    started = time.perf_counter()
    try:
        report = decode_archive(Path(archive), Path(restored), policy)
        actual_size = Path(restored).stat().st_size
        actual_hash = _sha256_path(Path(restored))
        if (actual_size, actual_hash) != (expected_size, expected_hash):
            raise ValueError("independent restoration differs from source")
        conn.send({"status": "VERIFIED", "decode_seconds": time.perf_counter() - started,
                   "restored_bytes": actual_size, "restored_sha256": actual_hash,
                   "decoder_report": report,
                   "peak_rss_kib": max(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                                       resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)})
    except MemoryError as exc:
        conn.send({"status": "RESOURCE_LIMIT", "error": f"{type(exc).__name__}: {exc}",
                   "decode_seconds": time.perf_counter() - started})
    except BaseException as exc:
        conn.send({"status": "VERIFY_FAILED", "error": f"{type(exc).__name__}: {exc}",
                   "decode_seconds": time.perf_counter() - started})
    finally:
        conn.close()


def _stop_group(proc: mp.Process, group_established: bool) -> None:
    """Stop only the session created by the candidate worker.

    A timed-out worker can exit while a nested CIX or codec subprocess remains.
    Once the ready handshake proves ``setsid()`` completed, the worker PID is a
    dedicated process-group ID and remains the safe cleanup target even if its
    leader has already exited.
    """
    if group_established:
        if proc.pid == os.getpgrp():
            raise RuntimeError("refusing to signal the portfolio parent group")
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    elif proc.is_alive():
        proc.terminate()
    proc.join(0.25)
    if proc.is_alive():
        if group_established:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        else:
            proc.kill()
        proc.join()


def _run_worker(target, args: tuple, timeout: float) -> dict:
    context = mp.get_context("fork")
    parent, child = context.Pipe(False)
    process = context.Process(target=target, args=(child, *args))
    started = time.perf_counter(); process.start(); child.close()
    group_established = False
    try:
        if not parent.poll(max(0.0, min(timeout, 1.0))):
            return {"status": "TIME_BUDGET", "wall_seconds": time.perf_counter() - started}
        ready = parent.recv()
        if not ready.get("ready"):
            return {"status": "WORKER_START_FAILED", "wall_seconds": time.perf_counter() - started}
        group_established = True
        remaining = timeout - (time.perf_counter() - started)
        if remaining <= 0 or not parent.poll(remaining):
            return {"status": "TIME_BUDGET", "wall_seconds": time.perf_counter() - started}
        result = parent.recv()
        process.join(0.25)
        result["wall_seconds"] = time.perf_counter() - started
        return result
    except (EOFError, OSError) as exc:
        return {"status": "WORKER_EXIT", "error": f"{type(exc).__name__}: {exc}",
                "wall_seconds": time.perf_counter() - started}
    finally:
        # Even a worker that returned normally may have left a nested codec
        # process alive.  The ready handshake proves this is our dedicated
        # session, so always close that process group before returning.
        _stop_group(process, group_established)
        parent.close()


def _select_smallest_verified(attempts: list[dict]) -> dict:
    eligible = [attempt for attempt in attempts if attempt.get("status") == "VERIFIED"]
    if not eligible:
        raise RuntimeError("no candidate completed exact verification")
    return min(eligible, key=lambda attempt: (attempt["archive_bytes"], attempt["plan_index"]))


def encode_portfolio(source: Path, destination: Path, *, profile: str,
                     policy: Mapping, disabled: Iterable[str] = (),
                     routes: Iterable[str] | None = None,
                     exhaustive_routes: bool | None = None,
                     attempt_directory: Path | None = None) -> dict:
    """Run the bounded portfolio and retain the smallest verified archive.

    Encode search time includes completed and discarded candidates.  Independent
    candidate validation is timed separately and does not masquerade as
    production encode time.  It is nevertheless required before selection in
    this audit API.
    """
    _validate_profile(profile)
    source = Path(source); destination = Path(destination)
    source_size = source.stat().st_size
    if source_size > MAX_INPUT_BYTES:
        raise ValueError("input exceeds bounded backend-portfolio limit")
    if source.resolve() == destination.resolve():
        raise ValueError("input and output must differ")
    source_hash = _sha256_path(source)
    policy_dict = dict(policy)
    plan = candidate_plan(profile, disabled=disabled, routes=routes,
                          exhaustive_routes=exhaustive_routes)
    budget = PORTFOLIO_SECONDS[profile]
    direct_plan = [item for item in plan if item["kind"] == "external" or
                   (item["kind"] == "cix-route" and item.get("route") == "raw")]
    direct_reserve = len(direct_plan) * EFFORTS[PROFILE_EFFORT[profile]].trial_seconds
    if profile == "size" and direct_reserve > budget:
        raise RuntimeError("maximum profile cannot reserve one attempt for every direct fallback")
    began = time.perf_counter(); attempts: list[dict] = []; search_used = 0.0
    owned_directory = None; completed_audit = False
    if attempt_directory is None:
        work = Path(tempfile.mkdtemp(prefix="cix-portfolio-"))
        owned_directory = work
    else:
        work = Path(attempt_directory); work.mkdir(parents=True, exist_ok=True)
    try:
        for index, item in enumerate(plan):
            remaining = budget - search_used
            record = {"plan_index": index, **item}
            archive = work / f"{index:02d}-{item['name'].replace(':', '-')}.cix"
            record["archive_name"] = archive.name
            if remaining <= 0:
                record.update(status="SEARCH_BUDGET", archive_bytes=None)
                attempts.append(record); continue
            policy_effort = EFFORTS[PROFILE_EFFORT[profile]]
            candidate_cap = policy_effort.search_seconds if item["kind"] == "cix-adaptive" else policy_effort.trial_seconds
            per_trial = min(candidate_cap, remaining)
            record["encode_cap_seconds"] = per_trial
            measured = _run_worker(_worker_encode,
                                   (str(source), str(archive), item, profile, policy_dict),
                                   per_trial)
            search_used += float(measured.get("wall_seconds", 0.0))
            record.update(measured)
            if measured.get("status") != "COMPLETE":
                archive.unlink(missing_ok=True)
                record["archive_bytes"] = None
                attempts.append(record); continue
            # Validation is evidence overhead and is deliberately accounted
            # separately from the encoder's candidate-search budget.
            restored = work / f"{index:02d}-{item['name'].replace(':', '-')}.restored"
            validation_cap = max(1.0, EFFORTS[PROFILE_EFFORT[profile]].trial_seconds)
            record["validation_cap_seconds"] = validation_cap
            verify = _run_worker(_worker_verify,
                                 (source_size, source_hash, str(archive), str(restored), policy_dict),
                                 validation_cap)
            record["validation"] = verify
            validation_status = verify.get("status", "VERIFY_FAILED")
            record["status"] = ("VERIFIED" if validation_status == "VERIFIED" else
                                "UNQUALIFIED" if validation_status in ("TIME_BUDGET", "RESOURCE_LIMIT") else
                                validation_status)
            restored.unlink(missing_ok=True)
            attempts.append(record)
            if record["status"] not in ("VERIFIED", "UNQUALIFIED"):
                raise CandidateVerificationError(record, list(attempts), work)
        selected = _select_smallest_verified(attempts)
        selected_archive = work / f"{selected['plan_index']:02d}-{selected['name'].replace(':', '-')}.cix"
        shutil.copyfile(selected_archive, destination)
        if destination.stat().st_size != selected["archive_bytes"] or _sha256_path(destination) != selected["archive_sha256"]:
            raise RuntimeError("selected archive copy differs from verified candidate")
        encode_wall = sum(float(a.get("wall_seconds", 0.0)) for a in attempts)
        validation_wall = sum(float(a.get("validation", {}).get("wall_seconds", 0.0)) for a in attempts)
        report = {
            "format": "CIX backend portfolio audit v1", "profile": profile,
            "source_bytes": source_size, "source_sha256": source_hash,
            "search_budget_seconds": budget,
            "search_budget_scope": "candidate encoding and discarded trials only; exact-restoration validation is separately capped and reported",
            "default_forced_candidate_cap_seconds": EFFORTS[PROFILE_EFFORT[profile]].trial_seconds,
            "adaptive_candidate_cap_seconds": EFFORTS[PROFILE_EFFORT[profile]].search_seconds,
            "default_validation_cap_seconds": max(1.0, EFFORTS[PROFILE_EFFORT[profile]].trial_seconds),
            "recommended_outer_audit_cap_seconds": 180.0,
            "outer_memory_bytes": OUTER_MEMORY_BYTES,
            "selected": selected["name"], "compressed_bytes": destination.stat().st_size,
            "archive_sha256": _sha256_path(destination), "attempts": attempts,
            "selection_encode_wall_seconds": encode_wall,
            "candidate_validation_wall_seconds": validation_wall,
            "selection_plus_validation_wall_seconds": encode_wall + validation_wall,
            "full_encode_and_validation_wall_seconds": encode_wall + validation_wall,
            "total_audit_wall_seconds": time.perf_counter() - began,
            "guarantee": "smallest complete exact-verified archive among attempted eligible candidates",
            "candidate_plan": [item["name"] for item in plan],
            "direct_attempt_reserve_seconds": direct_reserve,
            "direct_attempts": [
                {"name": attempt["name"], "status": attempt["status"],
                 "archive_bytes": attempt.get("archive_bytes")}
                for attempt in attempts
                if attempt["kind"] == "external" or
                   (attempt["kind"] == "cix-route" and attempt.get("route") == "raw")
            ],
            "maximum_direct_attempt_coverage": (
                "ALL_ATTEMPTED" if profile == "size" and
                all(attempt["status"] != "SEARCH_BUDGET" for attempt in attempts
                    if attempt["kind"] == "external" or
                       (attempt["kind"] == "cix-route" and attempt.get("route") == "raw"))
                else "NOT_AN_EXHAUSTIVE_PROFILE" if profile != "size"
                else "INCOMPLETE"
            ),
            "policy_excluded": dict(POLICY_EXCLUDED),
            "brotli_quality_0_source_basis": dict(BROTLI_RUNTIME),
            "implementation_sha256": {
                "backend_portfolio": _sha256_path(Path(__file__)),
                "frozen_pipeline": _sha256_path(Path(__file__).with_name("pipeline.py")),
            },
        }
        completed_audit = True
        return report
    finally:
        if owned_directory is not None and completed_audit:
            shutil.rmtree(owned_directory)


def decode_portfolio(source: Path, destination: Path, *, policy: Mapping) -> dict:
    """Production decode dispatches only the selected complete archive."""
    return decode_archive(Path(source), Path(destination), policy)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="bounded CIX reference-backend portfolio")
    subparsers = parser.add_subparsers(dest="operation", required=True)
    encode = subparsers.add_parser("encode")
    encode.add_argument("source", type=Path); encode.add_argument("destination", type=Path)
    encode.add_argument("--profile", choices=PROFILE_IDS, required=True)
    encode.add_argument("--policy", type=Path, required=True)
    encode.add_argument("--receipt", type=Path)
    encode.add_argument("--attempt-directory", type=Path)
    encode.add_argument("--disable", action="append", default=[])
    encode.add_argument("--route", action="append", choices=ROUTES.values())
    encode.add_argument("--no-exhaustive-routes", action="store_true")
    decode = subparsers.add_parser("decode")
    decode.add_argument("source", type=Path); decode.add_argument("destination", type=Path)
    decode.add_argument("--policy", type=Path, required=True)
    decode.add_argument("--receipt", type=Path)
    coverage = subparsers.add_parser("coverage")
    coverage.add_argument("--policy", type=Path, required=True)
    args = parser.parse_args(argv)
    policy = json.loads(args.policy.read_text())
    if args.operation == "encode":
        exhaustive = False if args.no_exhaustive_routes else None
        try:
            report = encode_portfolio(
                args.source, args.destination, profile=args.profile, policy=policy,
                disabled=args.disable, routes=args.route,
                exhaustive_routes=exhaustive, attempt_directory=args.attempt_directory,
            )
        except CandidateVerificationError as exc:
            failure = {
                "status": "VERIFY_FAILED", "error": str(exc),
                "failed_attempt": exc.attempt, "attempts": exc.attempts,
                "preserved_work_directory": exc.work_directory,
            }
            if args.receipt:
                args.receipt.write_text(json.dumps(failure, indent=2, sort_keys=True) + "\n")
            raise
    elif args.operation == "decode":
        report = decode_portfolio(args.source, args.destination, policy=policy)
    else:
        report = {"coverage": coverage_table(policy), "native_cix": native_cix_inventory()}
    if getattr(args, "receipt", None):
        args.receipt.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "attempts"}, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
