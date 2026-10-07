#!/usr/bin/env python3
"""Frozen sequential 36-cell staged-CLI qualification harness."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
MEMBERS = ("dickens", "mozilla", "mr", "nci", "ooffice", "osdb", "reymont", "samba", "sao", "webster", "x-ray", "xml")
PROFILES = {"fast": ["--fast"], "default": [], "best": ["--best"]}
CPUS = [8, 10, 12, 14]
MEMORY = 11_000_000_000
AGGREGATE_MEMORY = 12_000_000_000
TEMP = 4_000_000_000
MIB = 1 << 20


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=4, sort_keys=True) + "\n")
    temporary.replace(path)


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def file_id(path: Path) -> dict[str, Any]:
    path = path.resolve()
    if not path.is_file():
        raise RuntimeError(f"required file absent: {path}")
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": sha(path)}


def tree_id(root: Path) -> dict[str, Any]:
    root = root.resolve()
    if not root.is_dir():
        raise RuntimeError(f"required directory absent: {root}")
    rows = []
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if path.is_file() and not {".git", "target", "__pycache__"}.intersection(rel.parts):
            rows.append((str(rel), path.stat().st_size, sha(path)))
    value = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()
    return {"path": str(root), "sha256": hashlib.sha256(value).hexdigest(), "files": len(rows)}


def check_file(value: dict[str, Any]) -> None:
    path = Path(value["path"])
    if not path.is_file() or path.stat().st_size != value["bytes"] or sha(path) != value["sha256"]:
        raise RuntimeError(f"frozen file changed: {path}")


def check_tree(value: dict[str, Any]) -> None:
    if tree_id(Path(value["path"]))["sha256"] != value["sha256"]:
        raise RuntimeError(f"frozen tree changed: {value['path']}")


def harness_id() -> dict[str, dict[str, Any]]:
    return {name: file_id(HERE / name) for name in ("confirm.py", "measure_cli.py", "CONFIRMATION-HARNESS.md")}


def scheduler_id(schedule: Path) -> dict[str, dict[str, Any]]:
    paths = {"entry": schedule, "python": Path(sys.executable),
             "receipt_python": Path("/usr/bin/python3")}
    for name in ("cix_rust_perf_audit.py", "hutter_bounded_runner.py",
                 "hutter_experiment_scheduler.py", "cix_phase_receipt.py"):
        paths[name] = ROOT / "benchmarks" / name
    return {name: file_id(path) for name, path in paths.items()}


def external_dependencies(stage_root: Path) -> dict[str, Any]:
    receipt = stage_root / "runtime-stage.json"
    if not receipt.is_file():
        return {"libraries": [], "stdlib": None, "scope": "fixture stage without runtime dependency receipt"}
    recorded = read(receipt)["external_dependencies"]
    paths = {library["path"] for elf in recorded["elfs"].values()
             for library in elf["resolved_libraries"]}
    return {"libraries": [file_id(Path(path)) for path in sorted(paths)],
            "stdlib": tree_id(Path(recorded["python"]["stdlib"])),
            "scope": "host-pinned ELF library and Python standard-library identities"}


def freeze(a: argparse.Namespace) -> dict[str, Any]:
    return {
        "staged_cix": file_id(a.cix),
        "staged_uncix": file_id(a.uncix),
        "policy": file_id(a.policy),
        "historical_references": file_id(a.references),
        "source_export": tree_id(a.source_export),
        "stage_root": tree_id(a.stage_root),
        "harness": harness_id(),
        "scheduler": scheduler_id(a.schedule),
        "external_dependencies": external_dependencies(a.stage_root),
    }


def check_freeze(value: dict[str, Any]) -> None:
    for name in ("staged_cix", "staged_uncix", "policy", "historical_references"):
        check_file(value[name])
    for name in ("source_export", "stage_root"):
        check_tree(value[name])
    for identity in value["harness"].values():
        check_file(identity)
    for identity in value["scheduler"].values():
        check_file(identity)
    for identity in value["external_dependencies"]["libraries"]:
        check_file(identity)
    if value["external_dependencies"]["stdlib"] is not None:
        check_tree(value["external_dependencies"]["stdlib"])


def source_id(path: Path, name: str) -> dict[str, Any]:
    value = file_id(path)
    value["name"] = name
    return value


def check_source(value: dict[str, Any]) -> None:
    check_file(value)


def prepare(a: argparse.Namespace) -> None:
    area = a.area.resolve()
    if area.exists():
        raise RuntimeError("immutable qualification area already exists")
    cells = []
    for name in MEMBERS:
        source = source_id(a.silesia / name, name)
        for profile, flags in PROFILES.items():
            cells.append({
                "id": f"confirm-{profile}-{name}",
                "profile": profile,
                "profile_flags": flags,
                "source": source,
                "budget": {
                    "cpus": CPUS, "memory_bytes": MEMORY, "aggregate_memory_bytes": AGGREGATE_MEMORY, "temp_bytes": TEMP,
                    "encode_wall_seconds": 48 * 60 * 60,
                    "decode_wall_seconds": 12 * 60 * 60,
                },
            })
    validate_cells(cells, read(a.references))
    area.mkdir(parents=True)
    write(area / "plan.json", {
        "schema": "cix.silesia-confirmation.v2",
        "status": "PREPARED_NOT_EXECUTED",
        "freeze": freeze(a),
        "cells": cells,
        "execution": {
            "order": "canonical member then FAST, DEFAULT, BEST; one phase at a time",
            "retry": "STARTED/FAILED states prohibit implicit retry",
            "measurement": "ordinary staged CLI through measure_cli.py",
        },
    })


def validate_cells(cells: list[dict[str, Any]], references: dict[str, Any]) -> None:
    expected = [(name, profile) for name in MEMBERS for profile in PROFILES]
    actual = [(cell["source"]["name"], cell["profile"]) for cell in cells]
    if actual != expected:
        raise RuntimeError("plan must contain exactly the canonical 36 cells in frozen order")
    identities = {}
    for cell in cells:
        name, profile = cell["source"]["name"], cell["profile"]
        if cell["id"] != f"confirm-{profile}-{name}" or cell["profile_flags"] != PROFILES[profile]:
            raise RuntimeError("canonical cell identity or profile flags changed")
        if name in identities and identities[name] != cell["source"]:
            raise RuntimeError("source identity differs between profiles")
        identities[name] = cell["source"]
        expected_budget = {"cpus": CPUS, "memory_bytes": MEMORY,
            "aggregate_memory_bytes": AGGREGATE_MEMORY, "temp_bytes": TEMP,
            "encode_wall_seconds": 48 * 60 * 60, "decode_wall_seconds": 12 * 60 * 60}
        if cell["budget"] != expected_budget:
            raise RuntimeError("canonical resource policy changed")
    if references.get("fixture_only"):
        return
    rows = references["historical_portfolio"]["rows"]
    for row in rows:
        source = identities[row["file"]]
        if (source["bytes"], source["sha256"]) != (row["input_bytes"], row["input_sha256"]):
            raise RuntimeError("source differs from the frozen canonical corpus identity")
    if len(rows) != 12 or sum(item["bytes"] for item in identities.values()) != 211938580:
        raise RuntimeError("canonical corpus coverage/size mismatch")


def state_path(work: Path) -> Path:
    return work / "state.json"


def verified_result(work: Path, plan_sha: str) -> bool:
    result = work / "result.json"
    if not result.is_file():
        return False
    value = read(result)
    return value.get("status") == "VERIFIED" and value.get("plan_sha256") == plan_sha


def start(work: Path, cell: dict[str, Any], plan_sha: str) -> None:
    if verified_result(work, plan_sha):
        return
    if (work / "result.json").is_file() or state_path(work).is_file():
        state = read(state_path(work)) if state_path(work).is_file() else {}
        raise RuntimeError(f"no implicit retry for {cell['id']}: {state.get('status', 'unverified-result')}")
    work.mkdir(parents=True)
    write(state_path(work), {"status": "ENCODE_STARTED", "cell": cell["id"], "plan_sha256": plan_sha})


def command(phase: str, cell: dict[str, Any], frozen: dict[str, Any], work: Path) -> tuple[list[str], Path, Path]:
    receipt = work / f"{phase}.measurement.json"
    coverage = work / "selection-report.json"
    archive, restored = work / "archive.cix", work / "restored.bin"
    if phase == "encode":
        cli = [
            frozen["staged_cix"]["path"], *cell["profile_flags"],
            "--threads", "4", "--memory", f"{MEMORY}B",
            "--report", str(coverage), "-f", "-o", str(archive),
            cell["source"]["path"],
        ]
    else:
        cli = [
            frozen["staged_uncix"]["path"], "--memory", f"{MEMORY}B",
            "--max-output", str(cell["source"]["bytes"]),
            "-f", "-o", str(restored), str(archive),
        ]
    return [
        frozen["scheduler"]["python"]["path"], frozen["harness"]["measure_cli.py"]["path"],
        "--phase", phase, "--result", str(receipt), "--", *cli,
    ], receipt, coverage


def measurement(path: Path, phase: str) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError(f"missing {phase} measurement")
    value = read(path)
    cgroup = value.get("cgroup", {})
    valid = (
        value.get("schema") == "cix-cli-phase-measurement-v1"
        and value.get("phase") == phase
        and value.get("status") == "completed"
        and value.get("cli_exit_code") == 0
        and isinstance(value.get("wall_seconds"), (int, float))
        and isinstance(value.get("cpu_seconds", {}).get("total"), (int, float))
        and isinstance(cgroup.get("memory_peak_bytes"), int)
        and cgroup["memory_peak_bytes"] > 0
        and isinstance(cgroup.get("cpu_stat"), dict)
    )
    if not valid:
        raise RuntimeError(f"invalid {phase} measurement/cgroup receipt")
    return value


def retained_bytes(area: Path, exclude: Path | None = None) -> int:
    return sum(path.stat().st_size for path in area.rglob("*")
               if path.is_file() and (exclude is None or not path.is_relative_to(exclude)))


def phase(a: argparse.Namespace, plan: dict[str, Any], cell: dict[str, Any], work: Path, name: str) -> tuple[dict[str, Any], Path]:
    check_freeze(plan["freeze"])
    check_source(cell["source"])
    argv, receipt, coverage = command(name, cell, plan["freeze"], work)
    budget = cell["budget"]
    available_temp = budget["temp_bytes"] - retained_bytes(a.area, exclude=work)
    if available_temp <= 0:
        raise RuntimeError("retained qualification evidence exhausted the temporary budget")
    scratch = work / "scratch"
    scratch.mkdir(exist_ok=True)
    spec = {
        "id": f"{cell['id']}-{name}", "work": str(work), "input_bytes": cell["source"]["bytes"],
        "cpus": budget["cpus"], "memory_bytes": budget["aggregate_memory_bytes"], "temp_bytes": available_temp,
        "raw": str(work / "scheduler" / name),
        "env": [f"TMPDIR={scratch}"],
        "wall_seconds": budget[f"{name}_wall_seconds"], "command": argv,
    }
    spec_path = work / f"{name}.schedule.json"
    write(spec_path, spec)
    frozen_schedule = plan["freeze"]["scheduler"]
    if subprocess.run([frozen_schedule["python"]["path"], frozen_schedule["entry"]["path"], str(spec_path)]).returncode:
        write(state_path(work), {"status": f"{name.upper()}_SCHEDULER_FAILED", "cell": cell["id"]})
        raise RuntimeError(f"scheduler failed {cell['id']} {name}; no implicit retry")
    observed = measurement(receipt, name)
    if name == "encode":
        if not (work / "archive.cix").is_file() or not coverage.is_file():
            raise RuntimeError("ordinary encode did not produce archive and --report coverage")
    if retained_bytes(a.area) > TEMP:
        write(state_path(work), {"status": "ARCHIVE_RETENTION_CAP_EXCEEDED", "cell": cell["id"]})
        raise RuntimeError("retained qualification evidence exceeds 4GB temporary cap")
    return observed, coverage


def rate(bytes_: int, seconds: float) -> float | None:
    return bytes_ / MIB / seconds if seconds > 0 else None


def make_result(cell: dict[str, Any], plan_sha: str, work: Path, coverage: Path, enc: dict[str, Any], dec: dict[str, Any]) -> dict[str, Any]:
    source, archive = cell["source"], work / "archive.cix"
    size = archive.stat().st_size
    return {
        "status": "VERIFIED", "plan_sha256": plan_sha, "cell": cell["id"], "profile": cell["profile"],
        "source": source, "archive_bytes": size, "archive_sha256": sha(archive),
        "archive_percent_of_source": size * 100.0 / source["bytes"],
        "reduction_percent": 100.0 - size * 100.0 / source["bytes"],
        "coverage_report": str(coverage),
        "encode": {"measurement": enc, "mib_per_second": rate(source["bytes"], enc["wall_seconds"])},
        "decode": {"measurement": dec, "mib_per_second": rate(source["bytes"], dec["wall_seconds"])},
    }


def write_summary(area: Path, plan: dict[str, Any], plan_sha: str) -> None:
    rows = []
    for cell in plan["cells"]:
        work = area / "results" / cell["id"]
        if verified_result(work, plan_sha):
            rows.append(read(work / "result.json"))
    totals = {}
    for profile in PROFILES:
        group = [row for row in rows if row["profile"] == profile]
        source = sum(row["source"]["bytes"] for row in group)
        archive = sum(row["archive_bytes"] for row in group)
        enc_wall = sum(row["encode"]["measurement"]["wall_seconds"] for row in group)
        dec_wall = sum(row["decode"]["measurement"]["wall_seconds"] for row in group)
        totals[profile] = {
            "verified_cells": len(group), "source_bytes": source, "archive_bytes": archive,
            "archive_percent_of_source": archive * 100.0 / source if source else None,
            "reduction_percent": 100.0 - archive * 100.0 / source if source else None,
            "encode_wall_seconds": enc_wall, "decode_wall_seconds": dec_wall,
            "encode_cpu_seconds": sum(row["encode"]["measurement"]["cpu_seconds"]["total"] for row in group),
            "decode_cpu_seconds": sum(row["decode"]["measurement"]["cpu_seconds"]["total"] for row in group),
            "encode_mib_per_second": rate(source, enc_wall), "decode_mib_per_second": rate(source, dec_wall),
            "encode_kernel_memory_peak_bytes_max": max((row["encode"]["measurement"]["cgroup"]["memory_peak_bytes"] for row in group), default=None),
            "decode_kernel_memory_peak_bytes_max": max((row["decode"]["measurement"]["cgroup"]["memory_peak_bytes"] for row in group), default=None),
        }
    write(area / "summary.json", {
        "schema": "cix.silesia-confirmation-summary.v2",
        "status": "COMPLETE" if len(rows) == 36 else "INCOMPLETE",
        "plan_sha256": plan_sha, "verified_cells": len(rows), "rows": rows, "totals": totals,
        "historical_references": plan["freeze"]["historical_references"],
        "comparison_boundary": "Frozen historical/public references are separate from current measurements.",
    })


def run(a: argparse.Namespace) -> None:
    plan_path = a.area / "plan.json"
    plan = read(plan_path)
    if plan.get("schema") != "cix.silesia-confirmation.v2":
        raise RuntimeError("unsupported plan")
    plan_sha = sha(plan_path)
    check_freeze(plan["freeze"])
    validate_cells(plan["cells"], read(Path(plan["freeze"]["historical_references"]["path"])))
    for cell in plan["cells"]:
        work = a.area / "results" / cell["id"]
        if verified_result(work, plan_sha):
            continue
        start(work, cell, plan_sha)
        try:
            enc, coverage = phase(a, plan, cell, work, "encode")
            write(state_path(work), {"status": "DECODE_STARTED", "cell": cell["id"], "plan_sha256": plan_sha})
            dec, _ = phase(a, plan, cell, work, "decode")
            restored = work / "restored.bin"
            if not restored.is_file() or sha(restored) != cell["source"]["sha256"]:
                raise RuntimeError("fresh archive-only restore mismatch")
            write(work / "result.json", make_result(cell, plan_sha, work, coverage, enc, dec))
            restored.unlink()
            write(state_path(work), {"status": "VERIFIED", "cell": cell["id"], "plan_sha256": plan_sha})
            write_summary(a.area, plan, plan_sha)
        except Exception:
            if read(state_path(work)).get("status") not in {"ENCODE_SCHEDULER_FAILED", "DECODE_SCHEDULER_FAILED", "ARCHIVE_RETENTION_CAP_EXCEEDED"}:
                write(state_path(work), {"status": "FAILED", "cell": cell["id"], "plan_sha256": plan_sha})
            raise
    write_summary(a.area, plan, plan_sha)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--area", type=Path, required=True)
    parser.add_argument("--cix", type=Path, required=True)
    parser.add_argument("--uncix", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--references", type=Path, required=True)
    parser.add_argument("--source-export", type=Path, required=True)
    parser.add_argument("--stage-root", type=Path, required=True)
    parser.add_argument("--silesia", type=Path, default=ROOT / "benchmark-work" / "silesia")
    parser.add_argument("--schedule", type=Path, default=ROOT / "docs/research/2026-10-04-release-0.1/schedule.py")
    parser.add_argument("--run", action="store_true")
    a = parser.parse_args()
    if a.run:
        run(a)
    else:
        prepare(a)


if __name__ == "__main__":
    main()
