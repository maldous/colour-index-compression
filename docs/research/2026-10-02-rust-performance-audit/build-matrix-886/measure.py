#!/usr/bin/env python3
"""Measure the two already-built 886 portable compiler candidates."""
from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
FIX = Path("/home/user/src/colour-index-compression")
OUT = Path(__file__).resolve().parent
CPUS = "20,22"
REPS = 5
BUILDS = {
    "portable-opt3-fat-cgu1": Path("/tmp/cix-buildmatrix886-cgu1-retry/target/release"),
    "portable-opt3-fat-cgu16": Path("/tmp/cix-buildmatrix886-cgu16/target/release"),
}
WORK = (
    ("fast-kennedy", FIX / "benchmark-work/canterbury/kennedy.xls", ("--fast", "--threads", "1")),
    ("default-kennedy", FIX / "benchmark-work/canterbury/kennedy.xls", ("--threads", "1")),
    ("best-constrained-g1-lz-grammar", FIX / "benchmark-work/canterbury/grammar.lsp", ("--best", "--format", "cixg1", "--route", "lz", "--threads", "1")),
)

def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()

def measured(command: list[str], stdin: bytes | None = None) -> tuple[dict, bytes]:
    metric = tempfile.NamedTemporaryFile(prefix="cix-886-metric-", delete=False)
    metric.close()
    before = time.perf_counter_ns()
    run = subprocess.run(["/usr/bin/time", "-o", metric.name, "-f", "%U %S %M", *command],
                         input=stdin, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    wall = (time.perf_counter_ns() - before) / 1e9
    if run.returncode:
        raise RuntimeError(run.stderr.decode(errors="replace"))
    user, system, rss = Path(metric.name).read_text().split()
    Path(metric.name).unlink()
    return {"wall_seconds": wall, "cpu_seconds": float(user) + float(system), "peak_rss_kib": int(rss)}, run.stdout

def main() -> None:
    if subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() != "8865bfbccba354b02920da86c7088c17e5f96aab":
        raise SystemExit("source revision changed")
    archives = Path(tempfile.mkdtemp(prefix="cix-buildmatrix886-measure-", dir="/tmp"))
    rows, artifacts = [], {}
    for repeat in range(REPS):
        work = WORK if repeat % 2 == 0 else tuple(reversed(WORK))
        ordered_builds = tuple(BUILDS) if repeat % 2 == 0 else tuple(reversed(tuple(BUILDS)))
        for label, source, flags in work:
            source_hash = digest(source)
            for name in ordered_builds:
                cix, uncix = BUILDS[name] / "cix", BUILDS[name] / "uncix"
                encode, archive = measured(["taskset", "-c", CPUS, str(cix), *flags, "-c", str(source)])
                archive_path = archives / f"{repeat}-{name}-{label}.cix"
                archive_path.write_bytes(archive)
                archive_hash = digest(archive_path)
                artifacts[(repeat, name, label)] = (archive, source_hash)
                own_decode, restored = measured(["taskset", "-c", CPUS, str(uncix), "-c", "-"], archive)
                if hashlib.sha256(restored).hexdigest() != source_hash:
                    raise RuntimeError(f"own decode mismatch: {name}/{label}/{repeat}")
                rows.append({"repeat": repeat, "variant": name, "workload": label,
                             "input_sha256": source_hash, "archive_sha256": archive_hash,
                             "archive_bytes": len(archive), "encode": encode, "decode": own_decode})
    cross = []
    for (repeat, producer, label), (archive, source_hash) in artifacts.items():
        for consumer, binary_dir in BUILDS.items():
            _, restored = measured(["taskset", "-c", CPUS, str(binary_dir / "uncix"), "-c", "-"], archive)
            actual = hashlib.sha256(restored).hexdigest()
            if actual != source_hash:
                raise RuntimeError(f"cross decode mismatch: {producer}->{consumer}/{label}/{repeat}")
            cross.append({"repeat": repeat, "producer": producer, "consumer": consumer,
                          "workload": label, "restoration_sha256": actual})
    build_bytes = sum(path.stat().st_size for directory in BUILDS.values() for path in directory.rglob("*") if path.is_file())
    archive_bytes = sum(path.stat().st_size for path in archives.rglob("*") if path.is_file())
    if build_bytes + archive_bytes > 512_000_000:
        raise RuntimeError("temporary-space cap exceeded")
    OUT.joinpath("results.json").write_text(json.dumps({
        "schema": "cix-build-matrix-886-v1", "status": "completed_concurrent_host_screening",
        "source_revision": "8865bfbccba354b02920da86c7088c17e5f96aab", "cpus": CPUS,
        "memory_policy": {"cgroup_memory_max_bytes": 2000000000, "cgroup_memory_swap_max_bytes": 0},
        "builds": {name: {"directory": str(directory), "cix_sha256": digest(directory / "cix"), "uncix_sha256": digest(directory / "uncix"), "cix_bytes": (directory / "cix").stat().st_size, "uncix_bytes": (directory / "uncix").stat().st_size} for name, directory in BUILDS.items()},
        "temporary_bytes": {"builds": build_bytes, "archives": archive_bytes, "total": build_bytes + archive_bytes},
        "measurements": rows, "cross_decode": cross}, indent=2, sort_keys=True) + "\n")

if __name__ == "__main__":
    main()
