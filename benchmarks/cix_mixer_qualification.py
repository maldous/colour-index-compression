#!/usr/bin/env python3
"""Prepare or explicitly run a paired fixed-mix throughput qualification.

The four cells compare two immutable encoder/decoder pairs on the frozen first
128 KiB of the verified Dickens development source.  The route is forced only
to isolate the fixed-mix implementation; it is not an AUTO selector result.
Nothing executes unless both ``--run`` and ``--full`` are supplied.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from benchmarks.hutter_bounded_runner import build_identity, canonical, load_manifest
from benchmarks.hutter_experiment_scheduler import WaveScheduler

SOURCE = Path("/home/user/src/colour-index-compression/benchmark-work/silesia/dickens")
SOURCE_BYTES = 10_192_446
SOURCE_SHA256 = "b24c37886142e11d0ee687db6ab06f936207aa7f2ea1fd1d9a36763c7a507e6a"
RANGE_OFFSET = 0
RANGE_LENGTH = 128 * 1024
RANGE_SHA256 = "20e33fcc8faa96dc32a2d0921115c0f363e64c598a5847ce1a3876e356d59872"
RESERVED_CPUS = [16, 17, 18, 19]
REPETITIONS = 2
EXECUTION_ORDER = (("control", 1), ("candidate", 1), ("candidate", 2), ("control", 2))
WALL_SECONDS = 300
MEMORY_BYTES = 2 * 1024**3
TEMP_BYTES = 512 * 1024**2
PREFIX = re.compile(r"^[a-z0-9][a-z0-9-]{2,63}$")


def sha256(path: Path, offset: int = 0, length: int | None = None) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        stream.seek(offset)
        remaining = length
        while remaining is None or remaining:
            block = stream.read(min(1 << 20, remaining) if remaining is not None else 1 << 20)
            if not block:
                break
            digest.update(block)
            if remaining is not None:
                remaining -= len(block)
    return digest.hexdigest()


def relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(ROOT))
    except ValueError as error:
        raise ValueError(f"immutable binary must be inside integration root: {resolved}") from error


def require_binary(path: Path, label: str) -> Path:
    resolved = path.resolve()
    if not resolved.is_file() or not os.access(resolved, os.X_OK):
        raise RuntimeError(f"{label} must be an executable immutable binary: {resolved}")
    relative(resolved)
    return resolved


def require_environment(binaries: dict[str, Path]) -> None:
    if SOURCE.stat().st_size != SOURCE_BYTES or sha256(SOURCE) != SOURCE_SHA256:
        raise RuntimeError("verified Dickens source identity changed")
    if sha256(SOURCE, RANGE_OFFSET, RANGE_LENGTH) != RANGE_SHA256:
        raise RuntimeError("frozen first-128KiB Dickens hash changed")
    unavailable = set(RESERVED_CPUS) - os.sched_getaffinity(0)
    if unavailable:
        raise RuntimeError(f"required qualification CPUs are unavailable: {sorted(unavailable)}")
    cores: set[tuple[int, int]] = set()
    for cpu in RESERVED_CPUS:
        topology = Path(f"/sys/devices/system/cpu/cpu{cpu}/topology")
        try:
            core = (int((topology / "physical_package_id").read_text()), int((topology / "core_id").read_text()))
        except (OSError, ValueError):
            core = (0, cpu)
        if core in cores:
            raise RuntimeError("CPU reservation includes sibling logical cores")
        cores.add(core)
    for label, binary in binaries.items():
        require_binary(binary, label)


def exact_flags() -> list[str]:
    return [
        "--best", "--route", "mixture", "--format", "cixg2", "--block-size", "64KiB",
        "--memory", "512MiB", "--threads", "1", "--parallelism", "candidates", "--verbose",
    ]


def build_paths(encoder: Path, decoder: Path) -> list[str]:
    """Bind this cell to its artifacts and harness, never the mutable Rust tree.

    The control source snapshot is recorded from its immutable prior receipt,
    rather than being misrepresented by hashes from the candidate worktree.
    """
    return [
        relative(encoder), relative(decoder),
        "benchmarks/cix_mixer_qualification.py",
        "benchmarks/hutter_bounded_runner.py",
        "benchmarks/hutter_experiment_scheduler.py",
    ]


def require_sha256(value: object, label: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise RuntimeError(f"control receipt lacks valid {label}")
    return value


def load_control_binding(
    receipt_path: Path,
    control_revision: str,
    control_encoder_hash: str,
    control_decoder_hash: str,
) -> dict:
    """Read a verified immutable build receipt and bind the old binary pair to it."""
    if not receipt_path.is_file():
        raise RuntimeError(f"--control-receipt must name an immutable receipt: {receipt_path}")
    try:
        receipt = json.loads(receipt_path.read_text())
        identity = receipt["identity"]
        configuration = identity["configuration"]
        source_hashes = identity["build_sha256"]
    except (json.JSONDecodeError, KeyError, TypeError) as error:
        raise RuntimeError(f"invalid control receipt: {receipt_path}") from error
    if receipt.get("status") not in {"VERIFIED_SCREENING", "REUSED_VERIFIED"}:
        raise RuntimeError(f"control receipt is not verified: {receipt_path}")
    if not receipt.get("verification", {}).get("matched"):
        raise RuntimeError(f"control receipt lacks fresh decode verification: {receipt_path}")
    receipt_revision = configuration.get("implementation_revision", configuration.get("candidate_revision"))
    if receipt_revision != control_revision:
        raise RuntimeError(
            f"--control-revision {control_revision!r} does not match receipt revision {receipt_revision!r}"
        )
    expected_encoder = require_sha256(configuration.get("encoder_sha256"), "encoder_sha256")
    expected_decoder = require_sha256(configuration.get("decoder_sha256"), "decoder_sha256")
    if control_encoder_hash != expected_encoder or control_decoder_hash != expected_decoder:
        raise RuntimeError("control binary hash does not match its immutable control receipt")
    if not isinstance(source_hashes, dict):
        raise RuntimeError("control receipt lacks immutable source hashes")
    rust_sources = {
        str(path): require_sha256(digest, f"build_sha256[{path!r}]")
        for path, digest in source_hashes.items()
        if isinstance(path, str)
        and (path == "rust/cix-native/Cargo.toml" or path == "rust/cix-native/Cargo.lock" or path.startswith("rust/cix-native/src/"))
    }
    if not rust_sources:
        raise RuntimeError("control receipt has no Rust source identity hashes")
    # The receipt's build identity must itself contain the executable artifacts.
    if expected_encoder not in source_hashes.values() or expected_decoder not in source_hashes.values():
        raise RuntimeError("control receipt build identity does not bind both executable hashes")
    return {
        "receipt": str(receipt_path.resolve()),
        "receipt_sha256": sha256(receipt_path),
        "implementation_revision": control_revision,
        "encoder_sha256": expected_encoder,
        "decoder_sha256": expected_decoder,
        "prior_build_source_sha256": rust_sources,
    }


def control_binding(receipt_path: Path, control_revision: str, binaries: dict[str, Path]) -> dict:
    return load_control_binding(
        receipt_path,
        control_revision,
        sha256(binaries["control_cix"]),
        sha256(binaries["control_uncix"]),
    )


def implementation_revision(implementation: str, control_revision: str, candidate_revision: str) -> str:
    if implementation == "control":
        return control_revision
    if implementation == "candidate":
        return candidate_revision
    raise ValueError(f"unknown implementation: {implementation}")


def manifest_for(
    implementation: str,
    repetition: int,
    candidate_revision: str,
    control_revision: str,
    binaries: dict[str, Path],
    immutable_control_binding: dict,
) -> dict:
    encoder = binaries[f"{implementation}_cix"]
    decoder = binaries[f"{implementation}_uncix"]
    flags = exact_flags()
    return {
        "hypothesis": "Replacing fixed-mix variable scratch structures with fixed-size arrays preserves the deterministic forced-mixture CIXG2 archive while changing local encode/decode resource use.",
        "matched_control": "Control and candidate use the same frozen first 128KiB Dickens bytes, exact forced-mixture CLI, CIXG2 framing, four-core reservation, fresh processes, and two repetitions. Each encoder uses its matching immutable decoder; decoder changes are measured rather than attributed to the encoder.",
        "input": {
            "path": str(SOURCE), "offset": RANGE_OFFSET, "length": RANGE_LENGTH,
            "sha256": RANGE_SHA256, "full_asset_sha256": SOURCE_SHA256,
            "dataset": "existing verified Silesia Dickens", "development_only": True,
        },
        "configuration": {
            "implementation": implementation,
            "implementation_revision": implementation_revision(implementation, control_revision, candidate_revision),
            "comparison_candidate_revision": candidate_revision,
            "harness_sha256": sha256(Path(__file__)),
            "control_receipt_binding": immutable_control_binding if implementation == "control" else None,
            "repetition": repetition,
            "profile": "best",
            "route": "mixture",
            "format": "cixg2",
            "block_size": "64KiB",
            "memory": "512MiB",
            "threads": 1,
            "parallelism": "candidates",
            "flags": flags,
            "encoder_sha256": sha256(encoder),
            "decoder_sha256": sha256(decoder),
            "binary_pair": {"encoder": str(encoder), "decoder": str(decoder)},
        },
        "initial_state": "Fresh encoder and matching fresh archive-only decoder processes; host background and cache state are uncontrolled.",
        "mechanism": "Forced mixture is an implementation control for fixed-mix only. It does not measure normal AUTO CIX route, backend, package, or block selection.",
        "budget": {
            "cpu": RESERVED_CPUS, "max_rss_bytes": MEMORY_BYTES,
            "max_temp_bytes": TEMP_BYTES, "wall_seconds": WALL_SECONDS, "swap_bytes": 0,
        },
        "stage": "method_development",
        "promotion_criteria": "Both repetitions per binary pair must fresh-decode exactly. All four complete archive SHA-256 values must be identical. Verbose selector ledger must report exactly mixture:131072 selected source bytes and budget_skips=0, proving the forced route did not qualify through raw fallback or a skipped candidate. GNU time provides local wall, CPU, and max-RSS evidence only.",
        "exposure": "Existing verified 128KiB Dickens development range. No acquisition, held-out claim, full Silesia claim, or AUTO selector claim.",
        "encode_command": [
            "/usr/bin/time", "-v", "-o", "{workdir}/encode.gnu-time.txt", str(encoder), *flags,
            "-o", "{workdir}/candidate.cix", "{source}",
        ],
        "decode_command": [
            "/usr/bin/time", "-v", "-o", "{workdir}/decode.gnu-time.txt", str(decoder),
            "-o", "{workdir}/restored.bin", "{workdir}/candidate.cix",
        ],
        "artifacts": {"archive": "{workdir}/candidate.cix", "restored": "{workdir}/restored.bin"},
        "build_paths": build_paths(encoder, decoder),
        "resource_accounting": "Each serial cell leases CPUs 16,17,18,19. WaveScheduler aggregate cap is four physical cores, 12GB RAM, 4GB temporary storage, and no swap.",
    }


def assert_unique_prefix(prefix: str, area: Path) -> None:
    if not PREFIX.fullmatch(prefix):
        raise ValueError("--experiment-prefix must be 3..64 lowercase letters, digits, or hyphens")
    if area.exists():
        raise RuntimeError(f"evidence area already exists: {area}")
    claims = ROOT / ".hutter-experiment-scheduler/claims"
    if claims.exists() and any(claims.glob(f"{prefix}-mixer-*.claim.json")):
        raise RuntimeError("experiment prefix already has scheduler claims; choose a unique prefix")


def prepare(
    area: Path,
    prefix: str,
    candidate_revision: str,
    control_revision: str,
    control_receipt: Path,
    binaries: dict[str, Path],
) -> list[dict]:
    require_environment(binaries)
    immutable_control_binding = control_binding(control_receipt, control_revision, binaries)
    assert_unique_prefix(prefix, area)
    manifests = area / "manifests"
    manifests.mkdir(parents=True)
    cells = []
    for implementation, repetition in EXECUTION_ORDER:
        cell_id = f"{prefix}-mixer-{implementation}-r{repetition}"
        path = manifests / f"{cell_id}.json"
        path.write_bytes(canonical(manifest_for(
            implementation, repetition, candidate_revision, control_revision, binaries, immutable_control_binding,
        )) + b"\n")
        frozen, manifest_sha = load_manifest(path)
        cells.append({
            "cell_id": cell_id,
            "owner": "/root",
            "manifest_path": str(path.relative_to(ROOT)),
            "output_dir": str((area / "runs" / cell_id).relative_to(ROOT)),
            "cpu": RESERVED_CPUS,
            "expected_manifest_sha256": manifest_sha,
            "expected_build_sha256": build_identity(frozen, ROOT),
            "fresh_justification": "Predeclared paired repetition required for matched local resource variability.",
        })
    (area / "cells.json").write_text(json.dumps(cells, indent=2) + "\n")
    return cells


def gnu_time(path: Path) -> dict:
    values: dict[str, object] = {"path": str(path), "available": path.is_file()}
    if not path.is_file():
        return values
    for line in path.read_text(errors="replace").splitlines():
        if line.startswith("\tUser time (seconds):"):
            values["user_seconds"] = float(line.rsplit(":", 1)[1].strip())
        elif line.startswith("\tSystem time (seconds):"):
            values["system_seconds"] = float(line.rsplit(":", 1)[1].strip())
        elif line.startswith("\tMaximum resident set size (kbytes):"):
            values["max_rss_kib"] = int(line.rsplit(":", 1)[1].strip())
        elif line.startswith("\tElapsed (wall clock) time"):
            text = line.split("):", 1)[1].strip()
            parts = [float(part) for part in text.split(":")]
            values["wall_seconds"] = sum(value * 60 ** power for power, value in enumerate(reversed(parts)))
    return values


def selector_log(receipt: Path) -> Path:
    experiment_id = json.loads(receipt.read_text())["experiment_id"][:12]
    return receipt.parent / f"cix-bounded-{experiment_id}-encode.stderr.log"


def verify_selector_ledger(log: Path) -> str:
    if not log.is_file():
        raise RuntimeError(f"missing verbose selector stderr: {log}")
    text = log.read_text(errors="replace")
    if not re.search(r"\bbudget_skips=0\b", text):
        raise RuntimeError(f"selector budget skip in forced-mixture control: {log}")
    if "selected_source_bytes=[mixture:131072]" not in text:
        raise RuntimeError(f"forced mixture did not select all 128KiB without raw fallback: {log}")
    return sha256(log)


def validate_archive_consensus(receipts: list[dict]) -> None:
    """Ensure all forced-route archives have the same valid complete size and hash."""
    hashes: set[str] = set()
    sizes: set[int] = set()
    for receipt in receipts:
        archive_hash = receipt.get("archive_sha256")
        archive_bytes = receipt.get("archive_bytes")
        if not isinstance(archive_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", archive_hash):
            raise RuntimeError("missing complete archive hash")
        if type(archive_bytes) is not int or archive_bytes < 0:
            raise RuntimeError("archive_bytes must be a nonnegative integer")
        hashes.add(archive_hash)
        sizes.add(archive_bytes)
    if len(receipts) != REPETITIONS * 2 or len(hashes) != 1 or len(sizes) != 1:
        raise RuntimeError("control/candidate complete archives differ; do not attribute a throughput-only change")


def summarize_and_assert(area: Path, rows: list[dict]) -> list[dict]:
    summary = []
    receipts = []
    expected_timing = {"wall_seconds", "user_seconds", "system_seconds", "max_rss_kib"}
    for row in rows:
        receipt_name = row.get("runner_result", {}).get("receipt")
        if row.get("runner_status") not in {"VERIFIED_SCREENING", "REUSED_VERIFIED"} or not receipt_name:
            raise RuntimeError(f"qualification cell failed: {row.get('cell_id')}")
        receipt = Path(receipt_name)
        result = json.loads(receipt.read_text())
        if not result.get("verification", {}).get("matched"):
            raise RuntimeError(f"fresh decoder mismatch: {receipt}")
        receipts.append(result)
        archive_hash = result.get("archive_sha256")
        archive_bytes = result.get("archive_bytes")
        if type(archive_bytes) is not int or archive_bytes < 0:
            raise RuntimeError(f"archive_bytes must be a nonnegative integer: {receipt}")
        work = receipt.parent / "work"
        encode = gnu_time(work / "encode.gnu-time.txt")
        decode = gnu_time(work / "decode.gnu-time.txt")
        if not expected_timing <= set(encode) or not expected_timing <= set(decode):
            raise RuntimeError(f"incomplete GNU time evidence: {receipt}")
        log = selector_log(receipt)
        summary.append({
            "cell_id": row["cell_id"],
            "implementation": result["identity"]["configuration"]["implementation"],
            "archive_bytes": result.get("archive_bytes"),
            "archive_sha256": archive_hash,
            "encode": encode,
            "decode": decode,
            "selector_stderr": {"path": str(log), "sha256": verify_selector_ledger(log)},
            "verification": result["verification"],
        })
    validate_archive_consensus(receipts)
    (area / "qualification-summary.json").write_bytes(canonical({"rows": summary}) + b"\n")
    return summary


def plan(candidate_revision: str, control_revision: str, control_receipt: Path, binaries: dict[str, Path], prefix: str, area: Path) -> dict:
    return {
        "experiment_prefix": prefix,
        "candidate_revision": candidate_revision,
        "control_revision": control_revision,
        "control_receipt": str(control_receipt),
        "execution_order": [f"{implementation}-r{repetition}" for implementation, repetition in EXECUTION_ORDER],
        "source": {"path": str(SOURCE), "offset": RANGE_OFFSET, "length": RANGE_LENGTH, "sha256": RANGE_SHA256},
        "cells": REPETITIONS * 2,
        "serial_cells": True,
        "reserved_cpus": RESERVED_CPUS,
        "exact_encode_flags": exact_flags(),
        "binary_pairs": {key: str(path) for key, path in binaries.items()},
        "area": str(area),
        "execution": "blocked until both --run and --full; no benchmark execution occurred",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true", help="dispatch the prepared four-cell serial WaveScheduler plan")
    parser.add_argument("--full", action="store_true", help="required alongside --run to authorize local dispatch")
    parser.add_argument("--experiment-prefix", required=True)
    parser.add_argument("--candidate-revision", required=True)
    parser.add_argument("--control-revision", required=True, help="immutable source revision recorded by --control-receipt")
    parser.add_argument("--control-receipt", type=Path, required=True, help="verified immutable receipt for the supplied control binary pair")
    parser.add_argument("--control-cix", type=Path, required=True)
    parser.add_argument("--control-uncix", type=Path, required=True)
    parser.add_argument("--candidate-cix", type=Path, default=ROOT / "rust/cix-native/target/release-lto/cix")
    parser.add_argument("--candidate-uncix", type=Path, default=ROOT / "rust/cix-native/target/release-lto/uncix")
    parser.add_argument("--area", type=Path)
    args = parser.parse_args()
    if args.run != args.full:
        parser.error("dispatch requires both --run and --full")
    binaries = {
        "control_cix": args.control_cix,
        "control_uncix": args.control_uncix,
        "candidate_cix": args.candidate_cix,
        "candidate_uncix": args.candidate_uncix,
    }
    area = (args.area or ROOT / "docs/research/2026-10-01-cix-optimization" / f"cix-mixer-qualification-{args.experiment_prefix}").resolve()
    frozen_plan = plan(args.candidate_revision, args.control_revision, args.control_receipt, binaries, args.experiment_prefix, area)
    if not args.run:
        print(json.dumps(frozen_plan, indent=2, sort_keys=True))
        return 0
    cells = prepare(area, args.experiment_prefix, args.candidate_revision, args.control_revision, args.control_receipt, binaries)
    scheduler = WaveScheduler(ROOT, max_jobs=4, max_memory_bytes=12_000_000_000, max_temp_bytes=4_000_000_000)
    rows = []
    for cell in cells:  # Every cell leases all four physical cores, so dispatch serially.
        rows.extend(scheduler.run_wave([cell]))
    summary = summarize_and_assert(area, rows)
    print(json.dumps({"rows": rows, "summary": summary}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
