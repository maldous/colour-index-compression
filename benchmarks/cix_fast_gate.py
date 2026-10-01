#!/usr/bin/env python3
"""Prepare or run the native CIX FAST Canterbury/Calgary/Artificial gate.

This adapter only orchestrates immutable native ``cix``/``uncix`` artifacts
through the repository's bounded runner and WaveScheduler.  It never invokes
the Python codec, downloads data, or starts a benchmark unless ``--run`` is
given.  One candidate and one incumbent cell are declared for every cached
CCA input; cells are dispatched serially because each native process owns the
four physical CPUs needed for its bounded worker pool.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from benchmarks.cix_fast_opportunity import gnu_time
from benchmarks.hutter_bounded_runner import build_identity, canonical, load_manifest
from benchmarks.hutter_experiment_scheduler import WaveScheduler

CPUS = [16, 17, 18, 19]
MEMORY_BYTES = 3_000_000_000
TEMP_BYTES = 512_000_000
WALL_SECONDS = 300
STRATA = ("canterbury", "calgary", "artificial")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def artifact_identity(directory: Path) -> dict:
    """Verify the declared immutable native artifacts before freezing cells."""
    directory = directory.resolve()
    if ROOT not in directory.parents:
        raise ValueError("artifacts must be inside the repository")
    metadata_path = directory / "native-release.json"
    if not metadata_path.is_file():
        raise ValueError(f"missing native artifact metadata: {metadata_path}")
    metadata = json.loads(metadata_path.read_text())
    values = {"directory": relative(directory), "metadata": relative(metadata_path), "source_revision": metadata.get("source_revision")}
    for name in ("cix", "uncix"):
        binary = directory / name
        declared = metadata.get("binaries", {}).get(name, {})
        actual = sha256(binary) if binary.is_file() else None
        if not binary.is_file() or not os.access(binary, os.X_OK):
            raise ValueError(f"native {name} is not executable: {binary}")
        if actual != declared.get("sha256"):
            raise ValueError(f"native {name} does not match native-release.json")
        values[name] = {"path": relative(binary), "sha256": actual, "bytes": binary.stat().st_size}
    return values


def require_cpu_topology() -> None:
    unavailable = set(CPUS) - os.sched_getaffinity(0)
    if unavailable:
        raise RuntimeError(f"required CPUs unavailable: {sorted(unavailable)}")
    cores: set[tuple[int, int]] = set()
    for cpu in CPUS:
        base = Path(f"/sys/devices/system/cpu/cpu{cpu}/topology")
        try:
            key = (int((base / "physical_package_id").read_text()), int((base / "core_id").read_text()))
        except (OSError, ValueError):
            key = (0, cpu)
        if key in cores:
            raise RuntimeError("the fixed CPU reservation contains sibling logical CPUs")
        cores.add(key)


def cached_inputs() -> list[dict]:
    rows = []
    for stratum in STRATA:
        directory = ROOT / "benchmark-work" / stratum
        if not directory.is_dir():
            raise RuntimeError(f"required cached gate stratum is missing: {directory}")
        for path in sorted(item for item in directory.iterdir() if item.is_file()):
            if path.stat().st_size < 1:
                raise RuntimeError(f"gate source is empty: {path}")
            rows.append({"label": f"{stratum}/{path.name}", "stratum": stratum,
                         "path": path, "length": path.stat().st_size, "sha256": sha256(path),
                         "kind": "cached_verified"})
    counts = {stratum: sum(row["stratum"] == stratum for row in rows) for stratum in STRATA}
    if counts != {"canterbury": 11, "calgary": 18, "artificial": 4}:
        raise RuntimeError(f"unexpected CCA input census: {counts}")
    return rows


def synthetic_inputs(area: Path) -> list[dict]:
    """Freeze small generic stress cases; no corpus bytes or names steer CIX."""
    directory = area / "inputs"
    directory.mkdir()
    state = 0xC1A0_2026_1002_0001

    def next_byte() -> int:
        nonlocal state
        state ^= (state << 13) & ((1 << 64) - 1)
        state ^= state >> 7
        state ^= (state << 17) & ((1 << 64) - 1)
        state &= (1 << 64) - 1
        return state & 0xff

    record = bytes((i * 29 + (i >> 3)) & 0xff for i in range(257))
    strong = (record + record[:31]) * 480
    weak = bytes(next_byte() for _ in range(128 * 1024))
    absent = bytes((next_byte() ^ ((i * 17) & 0xff)) for i in range(128 * 1024))
    definitions = (("synthetic-strong-repeats.bin", strong, "repeated variable records"),
                   ("synthetic-weak-random.bin", weak, "deterministic pseudorandom bytes"),
                   ("synthetic-absent-opportunity.bin", absent, "deterministic high-variation residual-like bytes"))
    rows = []
    for name, data, mechanism in definitions:
        path = directory / name
        path.write_bytes(data)
        rows.append({"label": f"synthetic/{name}", "stratum": "synthetic", "path": path,
                     "length": len(data), "sha256": sha256(path), "kind": "generated_deterministic",
                     "generator": {"algorithm": "xorshift64-shift13-7-17", "seed": "0xC1A0202610020001",
                                   "mechanism": mechanism, "bytes": len(data)}})
    return rows


def build_paths(candidate: dict, incumbent: dict) -> list[str]:
    paths = ["benchmarks/cix_fast_gate.py", "benchmarks/cix_fast_opportunity.py",
             "benchmarks/hutter_bounded_runner.py", "benchmarks/hutter_experiment_scheduler.py"]
    for identity in (candidate, incumbent):
        paths.extend((identity["cix"]["path"], identity["uncix"]["path"], identity["metadata"]))
    return sorted(set(paths))


def verify_reuse_receipt(receipt_path: Path, input_row: dict, role: str, artifact: dict,
                         candidate: dict, incumbent: dict) -> dict | None:
    """Accept only an intact v1 verified result with exactly this experiment meaning."""
    try:
        receipt = json.loads(receipt_path.read_text())
        manifest = json.loads((receipt_path.parent / "manifest.json").read_text())
        identity, configuration = receipt["identity"], receipt["identity"]["configuration"]
        source, verification, artifacts = identity["input"], receipt["verification"], receipt["artifacts"]
        archive, restored = Path(artifacts["archive"]), Path(artifacts["restored"])
        if (receipt.get("status") != "VERIFIED_SCREENING" or not verification.get("matched")
                or manifest["input"].get("label") != input_row["label"]
                or manifest["input"].get("stratum") != input_row["stratum"]
                or source.get("path") != str(input_row["path"].resolve())
                or source.get("length") != input_row["length"] or source.get("sha256") != input_row["sha256"]
                or verification.get("source_sha256") != input_row["sha256"]
                or verification.get("restored_sha256") != input_row["sha256"]
                or configuration.get("role") != role or configuration.get("effort") != "fast"
                or configuration.get("flags") != ["--fast", "--verbose"]
                or configuration.get("advanced_overrides") != []
                or configuration.get("automatic_selection") is not True
                or configuration.get("artifact") != artifact
                or configuration.get("matched_artifacts") != {"candidate": candidate, "incumbent": incumbent}
                or not archive.is_file() or not restored.is_file()
                or archive.stat().st_size != receipt.get("archive_bytes")
                or sha256(archive) != receipt.get("archive_sha256")
                or sha256(restored) != input_row["sha256"]):
            return None
        build = identity["build_sha256"]
        if (build.get(artifact["cix"]["path"]) != artifact["cix"]["sha256"]
                or build.get(artifact["uncix"]["path"]) != artifact["uncix"]["sha256"]):
            return None
        return {"receipt": relative(receipt_path), "receipt_sha256": sha256(receipt_path),
                "archive_sha256": receipt["archive_sha256"], "restored_sha256": input_row["sha256"],
                "source_area": relative(receipt_path.parents[3]),
                "verification": "receipt, physical archive/restoration, input identity, public flags and artifact hashes rechecked"}
    except (KeyError, OSError, TypeError, json.JSONDecodeError):
        return None


def reusable_receipts(reuse_area: Path | None, inputs: list[dict], candidate: dict, incumbent: dict) -> dict[tuple[str, str], dict]:
    if reuse_area is None:
        return {}
    reuse_area = reuse_area.resolve()
    if ROOT not in reuse_area.parents or not reuse_area.is_dir():
        raise ValueError("--reuse-area must be an existing evidence directory inside this repository")
    wanted = {row["label"]: row for row in inputs}
    found: dict[tuple[str, str], dict] = {}
    for receipt_path in sorted((reuse_area / "runs").glob("**/receipt.json")):
        try:
            prior_manifest = json.loads((receipt_path.parent / "manifest.json").read_text())
            label = prior_manifest["input"]["label"]
            role = prior_manifest["configuration"]["role"]
        except (KeyError, OSError, TypeError, json.JSONDecodeError):
            continue
        if label not in wanted or role not in {"candidate", "incumbent"}:
            continue
        artifact = candidate if role == "candidate" else incumbent
        proof = verify_reuse_receipt(receipt_path, wanted[label], role, artifact, candidate, incumbent)
        if proof is None:
            continue
        key = (label, role)
        if key in found:
            raise RuntimeError(f"multiple valid reusable receipts for {label} {role}; select a narrower reuse area")
        found[key] = proof
    return found


def make_manifest(input_row: dict, role: str, artifact: dict, candidate: dict, incumbent: dict) -> dict:
    flags = ["--fast", "--verbose"]
    return {
        "hypothesis": "A compact bounded native FAST implementation must preserve exact generic lossless behavior across the CCA gate before MR screening; compare complete physical archives with the incumbent release.",
        "matched_control": "Candidate and incumbent use the same complete cached input bytes, public --fast interface, fresh encoder and archive-only decoder processes, four physical CPUs, GNU time format, and bounded runner.",
        "input": {"path": str(input_row["path"].resolve()), "offset": 0, "length": input_row["length"],
                  "sha256": input_row["sha256"], "label": input_row["label"], "stratum": input_row["stratum"],
                  "kind": input_row["kind"], "generator": input_row.get("generator")},
        "configuration": {"role": role, "effort": "fast", "flags": flags, "automatic_selection": True,
                          "advanced_overrides": [], "artifact": artifact,
                          "matched_artifacts": {"candidate": candidate, "incumbent": incumbent}},
        "initial_state": "fresh native encoder and fresh archive-only native decoder; host cache and unrelated host load are uncontrolled",
        "mechanism": "The native automatic FAST selector chooses routes and coding internally. Complete CIX framing, candidate discovery, discarded trials, metadata and footer are included in the measured archive.",
        "budget": {"cpu": CPUS, "max_rss_bytes": MEMORY_BYTES, "max_temp_bytes": TEMP_BYTES,
                   "wall_seconds": WALL_SECONDS, "swap_bytes": 0},
        "stage": "generic_cca_gate",
        "promotion_criteria": "Every candidate and incumbent input must fresh-decode to the original SHA-256. Record every archive size and GNU wall/CPU/RSS value, including losses. Candidate CCA completion precedes new candidate MR screening; this gate alone does not establish a corpus rank.",
        "resource_accounting": "Each cell leases CPUs 16,17,18,19 (four distinct physical cores) and runs serially. WaveScheduler aggregate capacity remains four cores, decimal 12 GB RAM, 4 GB temporary storage, no swap.",
        "encode_command": ["/usr/bin/time", "-v", "-o", "{workdir}/encode.gnu-time.txt", str(ROOT / artifact["cix"]["path"]), *flags,
                           "-o", "{workdir}/candidate.cix", "{source}"],
        "decode_command": ["/usr/bin/time", "-v", "-o", "{workdir}/decode.gnu-time.txt", str(ROOT / artifact["uncix"]["path"]),
                           "-o", "{workdir}/restored.bin", "{workdir}/candidate.cix"],
        "artifacts": {"archive": "{workdir}/candidate.cix", "restored": "{workdir}/restored.bin"},
        "build_paths": build_paths(candidate, incumbent),
    }


def prepare(area: Path, candidate: dict, incumbent: dict, include_synthetic: bool,
            reuse_area: Path | None) -> list[dict]:
    require_cpu_topology()
    if area.exists():
        raise RuntimeError(f"evidence area exists; immutable plans are never overwritten: {area}")
    area.mkdir(parents=True)
    (area / ".gitignore").write_text("runs/**/work/\nruns/**/build/\n")
    inputs = cached_inputs()
    if include_synthetic:
        inputs.extend(synthetic_inputs(area))
    reuse = reusable_receipts(reuse_area, inputs, candidate, incumbent)
    (area / "input-census.json").write_bytes(canonical({"inputs": [{**row, "path": relative(row["path"])} for row in inputs]}) + b"\n")
    manifests = area / "manifests"
    manifests.mkdir()
    cells = []
    for input_row in inputs:
        for role, artifact in (("incumbent", incumbent), ("candidate", candidate)):
            slug = hashlib.sha256(canonical({"input": input_row["sha256"], "label": input_row["label"],
                                               "path": relative(input_row["path"]), "role": role,
                                               "artifact": artifact["cix"]["sha256"], "effort": "fast"})).hexdigest()[:16]
            cell_id = f"cix-fast-gate-{role}-{slug}"
            manifest_path = manifests / f"{cell_id}.json"
            if manifest_path.exists():
                raise RuntimeError(f"refuse to overwrite a gate manifest: {manifest_path}")
            manifest_path.write_bytes(canonical(make_manifest(input_row, role, artifact, candidate, incumbent)) + b"\n")
            frozen, manifest_sha = load_manifest(manifest_path)
            cells.append({"cell_id": cell_id, "owner": "/root", "role": role, "label": input_row["label"],
                          "stratum": input_row["stratum"], "manifest_path": relative(manifest_path),
                          "output_dir": relative(area / "runs" / cell_id), "cpu": CPUS,
                          "expected_manifest_sha256": manifest_sha,
                          "expected_build_sha256": build_identity(frozen, ROOT),
                          "fresh_justification": "Predeclared native candidate/incumbent CCA paired cells; no retry or selection between runs.",
                          "reuse": reuse.get((input_row["label"], role))})
    (area / "cells.json").write_bytes(canonical({"candidate": candidate, "incumbent": incumbent,
                                                    "include_synthetic": include_synthetic, "cells": cells}) + b"\n")
    return cells


def receipt_row(cell: dict, scheduler: WaveScheduler) -> dict:
    terminal = scheduler._terminal_path(cell["cell_id"])
    row = {key: cell[key] for key in ("cell_id", "role", "label", "stratum")}
    if cell.get("reuse"):
        receipt_path = ROOT / cell["reuse"]["receipt"]
        receipt = json.loads(receipt_path.read_text())
        work = receipt_path.parent / "work"
        return {**row, "status": "REUSED_VERIFIED", "receipt": cell["reuse"]["receipt"],
                "reuse_provenance": cell["reuse"], "input_bytes": receipt["identity"]["input"]["length"],
                "input_sha256": receipt["identity"]["input"]["sha256"], "archive_bytes": receipt["archive_bytes"],
                "archive_sha256": receipt["archive_sha256"], "verification": receipt["verification"],
                "encode": gnu_time(work / "encode.gnu-time.txt"), "decode": gnu_time(work / "decode.gnu-time.txt"),
                "phases": receipt["phases"]}
    if not terminal.is_file():
        return {**row, "status": "PENDING"}
    terminal_row = json.loads(terminal.read_text())
    receipt_name = terminal_row.get("runner_result", {}).get("receipt")
    if not receipt_name or not Path(receipt_name).is_file():
        return {**row, "status": terminal_row.get("runner_status", "FAILED"), "terminal": relative(terminal)}
    receipt_path = Path(receipt_name)
    receipt = json.loads(receipt_path.read_text())
    work = receipt_path.parent / "work"
    return {**row, "status": receipt["status"], "receipt": relative(receipt_path),
            "input_bytes": receipt["identity"]["input"]["length"], "input_sha256": receipt["identity"]["input"]["sha256"],
            "archive_bytes": receipt["archive_bytes"], "archive_sha256": receipt["archive_sha256"],
            "verification": receipt["verification"], "encode": gnu_time(work / "encode.gnu-time.txt"),
            "decode": gnu_time(work / "decode.gnu-time.txt"), "phases": receipt["phases"]}


def summarize(area: Path, cells: list[dict]) -> dict:
    scheduler = WaveScheduler(ROOT, max_jobs=4, max_memory_bytes=12_000_000_000, max_temp_bytes=4_000_000_000)
    rows = [receipt_row(cell, scheduler) for cell in cells]
    by_label: dict[str, dict] = {}
    for row in rows:
        by_label.setdefault(row["label"], {})[row["role"]] = row
    comparisons = []
    for label, pair in sorted(by_label.items()):
        incumbent, candidate = pair.get("incumbent"), pair.get("candidate")
        comparison = {"label": label, "incumbent_status": incumbent.get("status") if incumbent else None,
                      "candidate_status": candidate.get("status") if candidate else None}
        verified_statuses = {"VERIFIED_SCREENING", "REUSED_VERIFIED"}
        if incumbent and candidate and incumbent.get("status") in verified_statuses and candidate.get("status") in verified_statuses:
            delta = candidate["archive_bytes"] - incumbent["archive_bytes"]
            comparison.update({"incumbent_archive_bytes": incumbent["archive_bytes"], "candidate_archive_bytes": candidate["archive_bytes"],
                               "archive_delta_bytes": delta, "archive_delta_ratio": delta / incumbent["archive_bytes"],
                               "outcome": "loss" if delta > 0 else ("win" if delta < 0 else "tie")})
        comparisons.append(comparison)
    verified = [item for item in comparisons if item.get("outcome") in {"win", "loss", "tie"}]
    totals = {"pairs": len(comparisons), "verified_pairs": len(verified),
              "candidate_bytes": sum(item["candidate_archive_bytes"] for item in verified),
              "incumbent_bytes": sum(item["incumbent_archive_bytes"] for item in verified),
              "wins": sum(item.get("outcome") == "win" for item in comparisons),
              "losses": sum(item.get("outcome") == "loss" for item in comparisons),
              "ties": sum(item.get("outcome") == "tie" for item in comparisons)}
    totals["archive_delta_bytes"] = totals["candidate_bytes"] - totals["incumbent_bytes"]
    report = {"rows": rows, "comparisons": comparisons, "totals": totals,
              "measurement_note": "GNU time metrics are reported per input in rows. Totals compare complete archive bytes only; do not aggregate wall time into a cross-hardware rank."}
    (area / "results.json").write_bytes(canonical(report) + b"\n")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", required=True, help="new immutable evidence identity")
    parser.add_argument("--artifacts", required=True, help="candidate native artifact directory containing cix, uncix and native-release.json")
    parser.add_argument("--incumbent-artifacts", default="benchmark-work/cix-qualified-release/final",
                        help="incumbent native artifact directory")
    parser.add_argument("--reuse-area", type=Path,
                        help="prior immutable gate area whose fully verified matching cells may be imported")
    parser.add_argument("--synthetic", action="store_true", help="also freeze three small deterministic generic stress inputs")
    parser.add_argument("--run", action="store_true", help="dispatch predeclared serial cells through WaveScheduler")
    args = parser.parse_args()
    if not args.id.replace("-", "").isalnum():
        parser.error("--id must use letters, numbers and hyphens")
    candidate = artifact_identity(ROOT / args.artifacts)
    incumbent = artifact_identity(ROOT / args.incumbent_artifacts)
    area = ROOT / "docs/research/2026-10-02-fast-opportunity" / args.id
    if area.exists():
        plan = json.loads((area / "cells.json").read_text())
        cells = plan["cells"]
        if plan["candidate"] != candidate or plan["incumbent"] != incumbent:
            raise RuntimeError("existing immutable gate identity uses different artifacts")
    else:
        cells = prepare(area, candidate, incumbent, args.synthetic, args.reuse_area)
    if not args.run:
        print(json.dumps({"prepared": len(cells), "area": relative(area), "cached_cca_pairs": 33,
                          "synthetic": args.synthetic, "execution": "not started"}, sort_keys=True))
        return 0
    scheduler = WaveScheduler(ROOT, max_jobs=4, max_memory_bytes=12_000_000_000, max_temp_bytes=4_000_000_000)
    for cell in cells:
        if cell.get("reuse"):
            continue
        terminal = scheduler._terminal_path(cell["cell_id"])
        if terminal.is_file():
            continue
        outcome = scheduler.run_wave([cell])[0]
        if outcome.get("runner_status") not in {"VERIFIED_SCREENING", "REUSED_VERIFIED"}:
            summarize(area, cells)
            raise RuntimeError(f"stop after non-verified gate cell: {cell['label']} {cell['role']}")
        summarize(area, cells)
    report = summarize(area, cells)
    if report["totals"]["verified_pairs"] != len({cell["label"] for cell in cells}):
        raise RuntimeError("gate has incomplete candidate/incumbent pairs")
    print(json.dumps({"area": relative(area), "totals": report["totals"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
