#!/usr/bin/env python3
"""Prepare or execute the fixed first five-domain pilot, without auto-retries."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from benchmarks import domain_research as research

ROOT = Path(__file__).resolve().parents[1]
AREA = ROOT / research.REL


def definitions():
    assets = {
        "mol2": "assets/pubchem-2d-batch/pubchem-2d-cids-1983-2244-2519-3672-5793-5950-681-702.sdf",
        "mol3": "assets/pubchem-3d-batch/pubchem-3d-cids-1983-2244-2519-3672-5793-5950-681-702.sdf",
        "num": "assets/noaa-water-level-202401.csv",
        "db": "database-data/uci-adult-first2048-nonblank.data",
        "elf": "input/strip-0d980587ada7.bin",
        "vol": "assets/nibabel-example4d.nii",
    }
    # Fixed waves; all variants and controls are declared before execution.
    waves = [
        [("mol2", "molecular", "original"), ("mol2", "molecular", "hydrogen_slots_v1"),
         ("mol3", "molecular", "original"), ("mol3", "molecular", "hydrogen_slots_v1")],
        [("num", "numeric", "original"), ("num", "numeric", "numeric-delta-columns-v1"),
         ("num", "numeric", "numeric-delta-columns-packed-meta-v1"), ("db", "database", "original")],
        [("db", "database", "literal"), ("db", "database", "dictionary_remaining"),
         ("elf", "executable", "original"), ("elf", "executable", "raw")],
        [("elf", "executable", "address"), ("elf", "executable", "address-packed"),
         ("vol", "volume", "jxl-planar3-e10"), ("vol", "volume", "original")],
        [("vol", "volume", "plane-stack"), ("vol", "volume", "delta-z")],
    ]
    return assets, waves


def prepare():
    path = AREA / "pilot-v1.json"
    if path.exists():
        return json.loads(path.read_text())
    assets, waves = definitions()
    # Complete transitive local import closure. The probe enforces that loaded
    # benchmarks/CIX modules resolve under the per-cell immutable build root.
    sources = [str(p.relative_to(ROOT)) for p in sorted((ROOT / "cix").glob("*.py"))]
    sources += ["benchmarks/" + name + ".py" for name in (
        "sdf_hydrogen", "sdf_geometry", "mysql_record_constraints",
        "domain_probe", "domain_pilot", "domain_research", "domain_molecular",
        "domain_numeric_noaa", "domain_database_csv", "domain_executable_adapter",
        "domain_volume", "hutter_bounded_runner", "hutter_experiment_registry",
        "hutter_experiment_scheduler")]
    sources += [str(research.REL / "README.md"), str(research.REL / "runtime-manifest.json")]
    cells = []
    for wave in waves:
        records = []
        for cpu, (asset, domain, variant) in zip(research.LANES, wave):
            backend = "native" if variant == "jxl-planar3-e10" else "paq"
            cell = research.prepare(AREA / assets[asset], domain, variant, backend, sources, cpu,
                                    600 if domain == "volume" else 300, owner="/root/domain_pilot")
            records.append(str(AREA / "cells" / (cell["cell_id"] + ".json")))
        cells.append(records)
    value = {"schema": 1, "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
             "protocol": str(research.REL / "README.md"), "waves": cells,
             "cells": sum(map(len, cells)), "status": "PREDECLARED_NOT_RUN"}
    research.immutable(path, value)
    return value


def run():
    path = AREA / "pilot-v1.json"
    if not path.exists():
        raise ValueError("prepare and preserve immutable declarations before execution")
    plan = json.loads(path.read_text())
    for number, cells in enumerate(plan["waves"], 1):
        records = research.run_wave(cells)
        research.immutable(AREA / f"pilot-wave-{number}-terminal.json", {"wave": number, "records": records})
        report = research.report()
        print(json.dumps({"wave": number, "results": [
            {k: row[k] for k in ("domain", "variant", "complete_bytes", "control_delta_bytes", "verification", "encode_seconds", "decode_seconds")}
            for row in report["rows"] if row["verification"] != "NOT_RUN"]}), flush=True)
    return {"status": "PILOT_FINISHED", "report": str(AREA / "domain-report.json")}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("prepare", "run"))
    args = parser.parse_args()
    print(json.dumps(prepare() if args.operation == "prepare" else run(), sort_keys=True))
