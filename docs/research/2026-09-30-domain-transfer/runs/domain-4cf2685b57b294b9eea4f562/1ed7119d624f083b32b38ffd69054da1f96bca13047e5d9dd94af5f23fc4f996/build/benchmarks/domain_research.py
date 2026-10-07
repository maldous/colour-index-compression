#!/usr/bin/env python3
"""Immutable, bounded forward-transfer cells for CIX domain adapters.

This module intentionally contains no domain transformation.  It freezes the
input, adapter/probe sources and command line, then delegates execution to the
shared bounded runner.  In particular it never installs a size gate: domain
experiments always run their independent archive-only decoder so time and
memory remain measured for both directions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path

from benchmarks.hutter_bounded_runner import build_identity, load_manifest
from benchmarks.hutter_experiment_registry import Registry, canonical, digest
from benchmarks.hutter_experiment_scheduler import WaveScheduler

ROOT = Path(__file__).resolve().parents[1]
REL = Path("docs/research/2026-09-30-domain-transfer")
MAGIC = b"CIXDOM01"
HEADER = struct.Struct(">8sBBQQI")
PAQ_BINARY = "benchmark-work/references/paq8px-v216/build-local/paq8px"
PAQ_SHA256 = "4fd7b3e768917a665ee4b91c6df3af1d22f540f7ff5beefe7fec689a8db182cc"
PAQ_OPTIONS = "-4 -simd AVX2"
TIME_BINARY = Path("/usr/bin/time")
LANES = (0, 2, 4, 6)

# These are the actual adapters currently in the repository.  The public
# domain names are deliberately stable even when an adapter's file name needs
# a provenance suffix (for example, NOAA or CSV).
ADAPTERS = {
    "molecular": "benchmarks/domain_molecular.py",
    "numeric": "benchmarks/domain_numeric_noaa.py",
    "database": "benchmarks/domain_database_csv.py",
    "executable": "benchmarks/domain_executable_adapter.py",
    "volume": "benchmarks/domain_volume.py",
}


def sha256(path: Path) -> str:
    digest_ = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest_.update(block)
    return digest_.hexdigest()


def immutable(path: Path, value: dict) -> None:
    data = canonical(value) + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError(f"immutable record differs: {path}")
        return
    with path.open("xb") as stream:
        stream.write(data)
    path.chmod(0o444)


def _relative(root: Path, path: str | Path) -> str:
    candidate = Path(path)
    resolved = (root / candidate).resolve() if not candidate.is_absolute() else candidate.resolve()
    if root != resolved and root not in resolved.parents:
        raise ValueError(f"build path must remain under repository root: {path}")
    if not resolved.is_file():
        raise ValueError(f"declared build path is missing: {path}")
    return str(resolved.relative_to(root))


def _asset(assetpath: str | Path) -> dict:
    path = Path(assetpath).resolve()
    if not path.is_file() or path.stat().st_size <= 0:
        raise ValueError("asset must be a non-empty file")
    digest_ = sha256(path)
    return {"path": str(path), "offset": 0, "length": path.stat().st_size,
            "sha256": digest_, "dataset_sha256": digest_}


def _control(receipt_path: str | Path, source: dict, domain: str | None = None) -> dict:
    """Rehash an optional matched original-byte PAQ control for reporting.

    Unlike the Wikipedia size gate, this never affects decode scheduling.
    """
    receipt_path = Path(receipt_path).resolve()
    try:
        row = json.loads(receipt_path.read_text())
        identity, verify, artifacts = row["identity"], row["verification"], row["artifacts"]
        archive, restored = Path(artifacts["archive"]), Path(artifacts["restored"])
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise ValueError("invalid control receipt") from error
    if row.get("status") != "VERIFIED_SCREENING" or not verify.get("matched"):
        raise ValueError("control receipt must be independently verified")
    control_input, config = identity.get("input", {}), identity.get("configuration", {})
    if any(control_input.get(key) != source[key] for key in ("path", "offset", "length", "sha256")):
        raise ValueError("control receipt input does not match asset")
    required_config = {"variant": "original", "backend": "paq",
                       "paq_binary_sha256": PAQ_SHA256,
                       "paq_options": PAQ_OPTIONS,
                       "source_filename": "candidate.source.bin"}
    if any(config.get(key) != value for key, value in required_config.items()):
        raise ValueError("control receipt is not pinned original-byte PAQ")
    if domain is not None and config.get("domain") != domain:
        raise ValueError("control receipt domain does not match candidate declaration")
    if not archive.is_file() or not restored.is_file() or archive.stat().st_size != row.get("archive_bytes"):
        raise ValueError("control artifacts are incomplete")
    if sha256(archive) != row.get("archive_sha256") or sha256(restored) != source["sha256"]:
        raise ValueError("control artifacts fail rehash")
    return {"receipt": str(receipt_path), "archive_bytes": row["archive_bytes"],
            "archive_sha256": row["archive_sha256"], "configuration": {
                key: config.get(key) for key in (*required_config, "domain", "wrapper_magic")}}


def prepare(assetpath: str | Path, domain: str, variant: str, backend: str,
            source_build_paths: list[str] | tuple[str, ...], cpu: int, budget: int = 300,
            control_receipt: str | Path | None = None, *, root: Path = ROOT,
            owner: str = "/root/paragraph_trials") -> dict:
    """Freeze a first-pass domain experiment; execution is a separate step."""
    root = Path(root).resolve()
    if domain not in ADAPTERS:
        raise ValueError("domain must be molecular, numeric, database, executable, or volume")
    if not isinstance(variant, str) or not variant.strip() or len(variant) > 128:
        raise ValueError("variant must be a non-empty short string")
    if backend not in ("paq", "native"):
        raise ValueError("backend must be paq or native")
    if cpu not in LANES:
        raise ValueError("domain scheduler lanes are CPU0, CPU2, CPU4, CPU6")
    if not isinstance(budget, int) or not 1 <= budget <= 1200:
        raise ValueError("domain budget must be 1..1200 seconds")
    if not isinstance(owner, str) or not owner.startswith("/root/"):
        raise ValueError("explicit /root worker owner is required")
    if not isinstance(source_build_paths, (list, tuple)):
        raise ValueError("source_build_paths must be a list of repository files")

    area = root / REL
    source = _asset(assetpath)
    probe = _relative(root, "benchmarks/domain_probe.py")
    adapter = _relative(root, ADAPTERS[domain])
    runner = _relative(root, "benchmarks/hutter_bounded_runner.py")
    harness = _relative(root, "benchmarks/domain_research.py")
    declared = [_relative(root, item) for item in source_build_paths]
    build_paths = sorted(set([probe, adapter, runner, harness, *declared]))
    # Fail preparation if the pinned PAQ binary changed or is absent, even for
    # native frames; it is recorded for a consistent future comparison.
    paq_path = root / PAQ_BINARY
    if not paq_path.is_file() or sha256(paq_path) != PAQ_SHA256:
        raise ValueError("pinned PAQ v216 binary is missing or has a different hash")
    if not TIME_BINARY.is_file():
        raise ValueError("/usr/bin/time is required for per-phase peak RSS")
    time_sha = sha256(TIME_BINARY)
    control = _control(control_receipt, source, domain) if control_receipt else None

    registry = Registry(area / "registry")
    input_id = registry.register_input(source["dataset_sha256"], 0, source["length"], source["sha256"])
    classification = registry.record_classification(input_id, {
        "domain": domain, "variant": variant, "backend": backend,
        "evidence_stratum": "forward_domain", "scale": "first_pass",
        "expected_mechanism": f"{domain}:{variant}", "compression_status": "PREPARED_NOT_RUN",
    }, {"asset_path": source["path"], "asset_sha256": source["sha256"],
        "adapter": adapter, "adapter_sha256": sha256(root / adapter)})
    registry.record_exposure(input_id, {"kind": "development",
        "evidence_refs": [str(REL / "registry" / "classifications" / f"{classification}.json")],
        "userdirective_refs": ["forward-domain programme, 2026-09-30"]})

    control_declaration = {"domain": domain, "variant": "original", "backend": "paq",
                           "paq_binary_sha256": PAQ_SHA256, "paq_options": PAQ_OPTIONS,
                           "source_filename": "candidate.source.bin", "wrapper_magic": MAGIC.decode(),
                           "input": {key: source[key] for key in ("path", "offset", "length", "sha256")}}
    config = {"domain": domain, "variant": variant, "backend": backend,
              "wrapper_magic": MAGIC.decode(), "wrapper_header_format": ">8sBBQQI",
              "paq_binary_sha256": PAQ_SHA256, "paq_options": PAQ_OPTIONS,
              "time_binary": str(TIME_BINARY), "time_binary_sha256": time_sha,
              "time_measurement": "GNU time -v Maximum resident set size (kbytes), separately for the encoder or decoder child process and its children; not a simultaneous process-tree aggregate",
              "source_filename": "candidate.source.bin", "selector": "NONE",
              "decode_policy": "always independently archive-only decode; no size gate"}
    archive = "{workdir}/candidate.cixdom"
    timed = [str(TIME_BINARY), "-v", "-o"]
    environment = ["/usr/bin/env", "OMP_NUM_THREADS=1", "OPENBLAS_NUM_THREADS=1", "MKL_NUM_THREADS=1", sys.executable]
    encode = [*timed, "{workdir}/encode.time.txt", *environment, str(root / probe), "encode", "{source}", archive,
              "--domain", domain, "--variant", variant, "--backend", backend,
              "--paq-binary", str(paq_path), "--paq-sha256", PAQ_SHA256]
    decode = [*timed, "{workdir}/decode.time.txt", *environment, str(root / probe), "decode", archive, "{workdir}/restored.bin",
              "--backend", backend, "--paq-binary", str(paq_path), "--paq-sha256", PAQ_SHA256]
    manifest = {"hypothesis": f"{domain}/{variant}: a paid reversible adapter may expose structure beyond original-byte PAQ.",
                "matched_control": "rehash-validated original-byte PAQ receipt" if control else "DECLARED original-byte PAQ control: same exact input, domain, wrapper and pinned PAQ identifiers; receipt binds before any matched delta",
                "mechanism": f"domain={domain}; variant={variant}; backend={backend}; all outer/adapter bytes paid",
                "promotion_criteria": "Finished physical archive and independent archive-only SHA-256 restoration. A first-pass result is domain evidence only, not a cross-domain rank or Hutter claim.",
                "input": source, "configuration": config,
                "initial_state": "empty per supplied asset; no external model, dictionary, filename recognition, training, or state sharing",
                "budget": {"cpu": cpu, "wall_seconds": budget, "max_rss_bytes": 3_000_000_000, "max_temp_bytes": 1_000_000_000},
                "artifacts": {"archive": archive, "restored": "{workdir}/restored.bin"},
                "build_paths": build_paths, "encode_command": encode, "decode_command": decode,
                "stage": "screening" if budget <= 300 else "moderate_contiguous",
                "stratum": "forward_domain", "prepared_not_run": True}
    if budget > 300:
        manifest["longer_budget_justification"] = (
            "The declared forward-domain asset requires a bounded 301..1200 second combined "
            "encode/decode allowance to measure the same complete archive and independent decode; "
            "input remains below the runner's 16 MiB moderate-contiguous ceiling.")
    # Deliberately no decode_size_gate here.
    build = build_identity(manifest, root)
    key = digest({"input_id": input_id, "domain": domain, "variant": variant, "backend": backend,
                  "manifest": manifest, "build": build})
    cell_id = "domain-" + key[:24]
    manifest_path = area / "manifests" / f"{cell_id}.json"
    immutable(manifest_path, manifest)
    loaded, manifest_sha = load_manifest(manifest_path)
    cell = {"cell_id": cell_id, "owner": owner, "input_id": input_id, "domain": domain,
            "variant": variant, "backend": backend, "state": "PREPARED_NOT_RUN",
            "manifest_path": str(manifest_path), "expected_manifest_sha256": manifest_sha,
            "expected_build_sha256": build_identity(loaded, root),
            "output_dir": str(area / "runs" / cell_id), "resource_lease": manifest["budget"],
            "control": control, "control_declaration": control_declaration,
            "classification_id": classification}
    immutable(area / "cells" / f"{cell_id}.json", cell)
    return cell


def _terminal(output: Path) -> tuple[Path | None, dict | None]:
    records = [path for name in ("receipt.json", "size-rejected.json", "failed.json") for path in output.glob(f"*/{name}")]
    if len(records) > 1:
        raise ValueError("multiple terminal records for immutable domain cell")
    return (records[0], json.loads(records[0].read_text())) if records else (None, None)


def _physical(archive: Path) -> dict:
    blob = archive.read_bytes()
    if len(blob) < HEADER.size:
        raise ValueError("short CIXDOM01 frame")
    magic, domain_code, backend_code, original, transformed, metadata_len = HEADER.unpack_from(blob)
    if magic != MAGIC or HEADER.size + metadata_len > len(blob):
        raise ValueError("invalid CIXDOM01 frame")
    raw_metadata = blob[HEADER.size:HEADER.size + metadata_len]
    try:
        metadata = json.loads(raw_metadata)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("CIXDOM01 metadata is not JSON") from error
    return {"complete_bytes": len(blob), "archive_sha256": sha256(archive),
            "header_bytes": HEADER.size, "metadata_bytes": metadata_len,
            "payload_bytes": len(blob) - HEADER.size - metadata_len,
            "original_bytes": original, "transformed_bytes": transformed,
            "domain_code": domain_code, "backend_code": backend_code,
            "paid_metadata": metadata}


def _time_peak_kib(path: Path) -> int | None:
    """Read GNU time's per-command Max RSS without conflating it with cgroups."""
    if not path.is_file():
        return None
    for line in path.read_text(errors="replace").splitlines():
        if "Maximum resident set size (kbytes):" in line:
            try:
                return int(line.rsplit(":", 1)[1].strip())
            except ValueError:
                return None
    return None


def _time_wall_seconds(path: Path) -> float | None:
    """Read GNU time's elapsed wall clock for the actual I/O command."""
    if not path.is_file():
        return None
    marker = "Elapsed (wall clock) time (h:mm:ss or m:ss):"
    for line in path.read_text(errors="replace").splitlines():
        if marker not in line:
            continue
        value = line.split(marker, 1)[1].strip()
        try:
            fields = [float(part) for part in value.split(":")]
        except ValueError:
            return None
        if len(fields) == 2:
            return fields[0] * 60 + fields[1]
        if len(fields) == 3:
            return fields[0] * 3600 + fields[1] * 60 + fields[2]
        return None
    return None


def _phase_identity(phases: list[dict], config: dict) -> bool:
    """Check the recorded commands still identify the paid probe phases."""
    encode = next((x for x in phases if str(x.get("phase", "")).endswith("-encode")), None)
    decode = next((x for x in phases if str(x.get("phase", "")).endswith("-decode")), None)
    if not encode or not decode or encode.get("exit_code") != 0 or decode.get("exit_code") != 0:
        return False
    ec, dc = [str(value) for value in encode.get("command", [])], [str(value) for value in decode.get("command", [])]
    def value(command, flag):
        try: return command[command.index(flag) + 1]
        except (ValueError, IndexError): return None
    return ("encode" in ec and "decode" in dc and "--domain" in ec and "--variant" in ec
            and "--domain" not in dc and "--variant" not in dc
            and value(ec, "--domain") == config["domain"] and value(ec, "--variant") == config["variant"]
            and value(ec, "--backend") == config["backend"] and value(dc, "--backend") == config["backend"]
            and value(ec, "--paq-sha256") == PAQ_SHA256 and value(dc, "--paq-sha256") == PAQ_SHA256)


def _matching_control(rows: list[dict], candidate: dict) -> dict | None:
    """Bind only a rehashed raw-PAQ control with the complete declared identity."""
    declaration = candidate["control_declaration"]
    for possible in rows:
        if possible["cell_id"] == candidate["cell_id"] or possible["verification"] != "SHA256_MATCHED_REHASHED":
            continue
        config, inp = possible["configuration"], possible["input"]
        if all(config.get(key) == declaration[key] for key in ("domain", "variant", "backend", "paq_binary_sha256", "paq_options", "source_filename", "wrapper_magic")) and all(inp.get(key) == declaration["input"][key] for key in declaration["input"]):
            return {"cell_id": possible["cell_id"], "receipt": possible["terminal_record"],
                    "archive_bytes": possible["complete_bytes"], "archive_sha256": possible["archive_sha256"],
                    "binding": "auto-bound exact immutable raw-PAQ control"}
    return None


def report(*, root: Path = ROOT) -> dict:
    root, area = Path(root).resolve(), Path(root).resolve() / REL
    rows = []
    for cell_path in sorted((area / "cells").glob("domain-*.json")):
        cell = json.loads(cell_path.read_text()); terminal_path, terminal = _terminal(Path(cell["output_dir"]))
        manifest = json.loads(Path(cell["manifest_path"]).read_text())
        if not isinstance(cell.get("expected_build_sha256"), dict):
            raise ValueError("cell expected_build_sha256 must be a declared build identity map")
        source_bytes = sum((root / item).stat().st_size for item in cell["expected_build_sha256"].keys() if (root / item).is_file())
        row = {"cell_id": cell["cell_id"], "domain": cell["domain"], "variant": cell["variant"], "backend": cell["backend"],
               "input": manifest["input"], "configuration": manifest["configuration"], "state": cell["state"], "control": cell.get("control"), "control_declaration": cell["control_declaration"],
               "raw_input_bytes": manifest["input"]["length"], "complete_bytes": None, "transform_bytes": None,
               "backend_payload_bytes": None, "native_attribution": "NOT_MEASURED", "program_source_bytes": source_bytes,
               "program_package_bytes": "NOT_MEASURED", "verification": "NOT_RUN", "decode_skipped": False,
               "encode_seconds": None, "decode_seconds": None,
               "encode_supervisory_elapsed_seconds": None, "decode_supervisory_elapsed_seconds": None,
               "time_precision_seconds": 0.01, "memory_lower_bound_bytes": None,
               "encode_peak_process_rss_kib": None, "decode_peak_process_rss_kib": None, "phase_identity_verified": False,
               "peak_process_rss_note": "GNU time -v Maximum resident set size (kbytes), separately per encoder/decoder command; not a simultaneous process-tree aggregate",
               "temporary_disk_high_water_bytes": None, "control_delta_bytes": None,
               "terminal_record": str(terminal_path) if terminal_path else None}
        if terminal is not None:
            row["state"] = terminal.get("status", "FAILED")
            artifacts, verification = terminal.get("artifacts", {}), terminal.get("verification", {})
            archive, restored = Path(artifacts.get("archive", "")), Path(artifacts.get("restored", ""))
            phases = [phase for phase in terminal.get("phases", []) if phase]
            phase_ok = _phase_identity(phases, manifest["configuration"])
            row["phase_identity_verified"] = phase_ok
            if row["state"] == "VERIFIED_SCREENING" and verification.get("matched") and phase_ok and archive.is_file() and restored.is_file():
                try:
                    physical = _physical(archive)
                    if physical["complete_bytes"] != terminal.get("archive_bytes") or physical["archive_sha256"] != terminal.get("archive_sha256"):
                        raise ValueError("archive identity mismatch")
                    if sha256(restored) != manifest["input"]["sha256"]:
                        raise ValueError("restored hash mismatch")
                    row.update(physical); row["verification"] = "SHA256_MATCHED_REHASHED"
                except ValueError:
                    row["verification"] = "INVALID_TERMINAL_ARTIFACT"
            else:
                row["verification"] = row["state"]
            row["encode_supervisory_elapsed_seconds"] = next((x.get("elapsed_seconds") for x in phases if str(x.get("phase", "")).endswith("-encode")), None)
            row["decode_supervisory_elapsed_seconds"] = next((x.get("elapsed_seconds") for x in phases if str(x.get("phase", "")).endswith("-decode")), None)
            row["memory_lower_bound_bytes"] = max((x.get("sampled_cgroup_memory_high_water_bytes", 0) for x in phases), default=None)
            row["temporary_disk_high_water_bytes"] = max((x.get("peak_temp_bytes", 0) for x in phases), default=None)
            if archive.parent.is_dir():
                row["encode_peak_process_rss_kib"] = _time_peak_kib(archive.parent / "encode.time.txt")
                row["decode_peak_process_rss_kib"] = _time_peak_kib(archive.parent / "decode.time.txt")
                row["encode_seconds"] = _time_wall_seconds(archive.parent / "encode.time.txt")
                row["decode_seconds"] = _time_wall_seconds(archive.parent / "decode.time.txt")
            if row["complete_bytes"] is not None:
                row["transform_bytes"] = row["transformed_bytes"]
                row["backend_payload_bytes"] = row["payload_bytes"]
                row["native_attribution"] = row["payload_bytes"] if row["backend"] == "native" else "PAQ_PAYLOAD"
        rows.append(row)
    # Explicitly declared controls may complete concurrently with candidates.
    # Bind only after both terminal artifact hashes and all config/input fields
    # above have been independently rechecked.
    for row in rows:
        if row["control"] is None:
            row["control"] = _matching_control(rows, row)
        if row["control"] and row["complete_bytes"] is not None:
            row["control_delta_bytes"] = row["complete_bytes"] - row["control"]["archive_bytes"]
    result = {"schema": 1, "rows": rows,
              "ranking_policy": "No rankings cross datasets or domains. Each optional matched PAQ delta applies only to exactly the same immutable asset.",
              "cost_policy": "raw input, adapter transform, outer header, paid metadata, payload and program source inventory are separate; no byte class is added twice."}
    (area / "domain-report.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    lines = ["# CIX forward-domain research", "", "| Domain / variant | Raw bytes | Complete bytes | Δ matched PAQ | Verification | Encode / decode s | Peak RSS KiB (encode/decode) | Cgroup lower bound |", "|---|---:|---:|---:|---|---:|---:|---:|"]
    for row in rows:
        times = f"{row['encode_seconds']:.2f}" if row['encode_seconds'] is not None else "—"
        times += " / " + (f"{row['decode_seconds']:.2f}" if row['decode_seconds'] is not None else "—")
        rss = f"{row['encode_peak_process_rss_kib'] if row['encode_peak_process_rss_kib'] is not None else '—'} / {row['decode_peak_process_rss_kib'] if row['decode_peak_process_rss_kib'] is not None else '—'}"
        lines.append(f"| {row['domain']} / {row['variant']} ({row['backend']}) | {row['raw_input_bytes']} | {row['complete_bytes'] if row['complete_bytes'] is not None else '—'} | {row['control_delta_bytes'] if row['control_delta_bytes'] is not None else '—'} | {row['verification']} | {times} | {rss} | {row['memory_lower_bound_bytes'] if row['memory_lower_bound_bytes'] is not None else '—'} |")
    lines += ["", "Encode/decode time is GNU time's elapsed wall clock for the actual I/O command, shown to 0.01 s. Scheduler/runner supervisory elapsed time is retained separately in JSON and is not used as codec timing; this avoids treating launch/poll overhead as compression work on small assets.", "", "Peak RSS is GNU time's Maximum resident set size for each encoder or decoder command and its children, not a simultaneous process-tree aggregate. Cgroup memory is retained as a separate sampled lower bound.", "", "All first-domain candidates are required to independently decode, including size losses. Results are domain-specific forward-transfer evidence; they are not cross-dataset rankings or Hutter results.", ""]
    (area / "DOMAIN-RESULTS.md").write_text("\n".join(lines))
    return result


def run_wave(cells: list[dict] | list[str], *, root: Path = ROOT) -> list[dict]:
    root = Path(root).resolve()
    decoded = [json.loads(Path(cell).read_text()) if isinstance(cell, str) else cell for cell in cells]
    if not decoded or any(cell.get("state") != "PREPARED_NOT_RUN" for cell in decoded):
        raise ValueError("only prepared domain cells may be dispatched")
    return WaveScheduler(root, max_jobs=4, max_memory_bytes=12_000_000_000,
                         max_temp_bytes=4_000_000_000).run_wave(decoded)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare"); p.add_argument("assetpath", type=Path); p.add_argument("--domain", choices=sorted(ADAPTERS), required=True); p.add_argument("--variant", required=True); p.add_argument("--backend", choices=("paq", "native"), required=True); p.add_argument("--source-build-path", action="append", default=[]); p.add_argument("--cpu", type=int, required=True); p.add_argument("--budget", type=int, default=300); p.add_argument("--control-receipt", type=Path); p.add_argument("--owner", default="/root/paragraph_trials")
    p = sub.add_parser("run-wave"); p.add_argument("cells", nargs="+")
    sub.add_parser("report"); args = parser.parse_args()
    if args.command == "prepare": result = prepare(args.assetpath, args.domain, args.variant, args.backend, args.source_build_path, args.cpu, args.budget, args.control_receipt, owner=args.owner)
    elif args.command == "run-wave": result = run_wave(args.cells)
    else: result = report()
    print(json.dumps(result, sort_keys=True)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
