#!/usr/bin/env python3
"""Fetch and validate the pinned public Squash benchmark result CSVs."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

COMMIT = "fed6ea3374155184672b71928d2b805463d156f0"
REPO = "quixdb/squash-benchmark-web"
RAW = f"https://raw.githubusercontent.com/{REPO}/{COMMIT}"
JS_URL = f"{RAW}/squash-benchmark.js"
TREE_URL = f"https://api.github.com/repos/{REPO}/git/trees/{COMMIT}?recursive=1"
EXPECTED_DATASET_COUNT = 28
EXPECTED_MACHINE_COUNT = 9
EXPECTED_RESULTS_PER_MACHINE = 6580
EXPECTED_BLOBS = {
    "beagleboard-xm": ("c57183c9023e6a76578f45d47ccaa9d13fecd4cf", 437051),
    "e-desktop": ("c9fe5bc7071d25cc579f7dceec9545a29d4bce8a", 433868),
    "hoplite": ("c37789836245b5ce6661490f2b271eabbe4e4419", 433888),
    "odroid-c1": ("8676a5d64287dd55a65a6ba056dd87ba2ecfcb6a", 435884),
    "peltast": ("216a28382e65996729569afc5ef7cfe8e6c9a5cf", 433741),
    "phalanx": ("c5f916640832a472267c9f86dbf46d8f37fde302", 435454),
    "raspberry-pi-2": ("44087be92027606f728d14b21c2952fbc3ecc36b", 436388),
    "s-desktop": ("ac7bc422da568a6787ff32d69287de9a5813274b", 433802),
    "satellite-a205": ("54f1cb4dbcb5f7dbed14624a3275511e4a587954", 434530),
}
CSV_FIELDS = [
    "dataset", "plugin", "codec", "level", "compressed_size",
    "compress_cpu", "compress_wall", "decompress_cpu", "decompress_wall",
]


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "CIX-Squash-results-import/1.0"})
    with urllib.request.urlopen(req, timeout=60) as response:
        return response.read()


def git_blob_sha1(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode()
    return hashlib.sha1(header + data).hexdigest()


def array_section(source: str, begin: str, end: str) -> str:
    return source[source.index(begin):source.index(end)]


def parse_datasets(source: str) -> list[dict]:
    section = array_section(source, "var datasets = [", "var dataset_map =")
    result = []
    for match in re.finditer(r"\{\s*id: '([^']+)'(.*?)\}", section, re.S):
        ident, body = match.groups()
        def string(key: str) -> str:
            m = re.search(r"\b" + re.escape(key) + r": '([^']*)'", body)
            if not m:
                raise ValueError(f"missing {key} for dataset {ident}")
            return m.group(1)
        size = re.search(r"\bsize: (\d+)", body)
        if not size:
            raise ValueError(f"missing size for dataset {ident}")
        result.append({"id": ident, "source": string("source"), "source_url": string("sourceUrl"),
                       "description": string("description"), "original_bytes": int(size.group(1))})
    if len(result) != EXPECTED_DATASET_COUNT:
        raise ValueError(f"expected {EXPECTED_DATASET_COUNT} dataset definitions, got {len(result)}")
    return result


def parse_machines(source: str) -> list[dict]:
    section = array_section(source, "var machines = [", "var machine_map =")
    blocks = list(re.finditer(r"^    \{ name: \"([^\"]+)\",([\s\S]*?)(?=^    \{ name:|^\];)", section, re.M))
    result = []
    for match in blocks:
        ident, body = match.groups()
        def value(key: str) -> str | int:
            m = re.search(r"^\s+" + re.escape(key) + r": (.*?)(?:,)?\s*$", body, re.M)
            if not m:
                return ""
            raw = m.group(1).strip()
            quoted = re.fullmatch(r'"(.*)"', raw)
            if quoted:
                return quoted.group(1)
            nums = re.fullmatch(r"(\d+)\s*\*\s*(\d+)", raw)
            if nums:
                return int(nums.group(1)) * int(nums.group(2))
            if raw.isdigit():
                return int(raw)
            return raw
        result.append({"id": ident, "cpu": value("cpu"), "architecture": value("architecture"),
                       "speed_hz": value("speed"), "memory_mib": value("memory"),
                       "platform": value("platform"), "distro": value("distro"),
                       "kernel": value("kernel"), "compiler": value("compiler")})
    if len(result) != EXPECTED_MACHINE_COUNT:
        raise ValueError(f"expected {EXPECTED_MACHINE_COUNT} active machine definitions, got {len(result)}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True, help="Squash evidence directory")
    args = parser.parse_args()
    output = args.output.resolve()
    raw_dir = output / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    js = get(JS_URL).decode("utf-8")
    datasets = parse_datasets(js)
    machines = parse_machines(js)
    machine_ids = [m["id"] for m in machines]
    if set(machine_ids) != set(EXPECTED_BLOBS):
        raise ValueError("upstream active machine list differs from the pinned nine CSV files")
    dataset_sizes = {d["id"]: d["original_bytes"] for d in datasets}

    tree_req = urllib.request.Request(TREE_URL, headers={"Accept": "application/vnd.github+json"})
    tree = json.loads(urllib.request.urlopen(tree_req, timeout=30).read())
    tree_blobs = {x["path"].split("/", 1)[1]: (x["sha"], x["size"])
                  for x in tree["tree"] if x["path"].startswith("data/") and x["path"].endswith(".csv")}
    if tree_blobs != {f"{k}.csv": v for k, v in EXPECTED_BLOBS.items()}:
        raise ValueError("pinned Git tree data files do not match reviewed blob identities")

    files = []
    for machine in machines:
        ident = machine["id"]
        data = get(f"{RAW}/data/{ident}.csv")
        blob, byte_count = EXPECTED_BLOBS[ident]
        if len(data) != byte_count or git_blob_sha1(data) != blob:
            raise ValueError(f"upstream Git blob check failed for {ident}")
        path = raw_dir / f"{ident}.csv"
        path.write_bytes(data)
        with path.open(newline="", encoding="utf-8") as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames != CSV_FIELDS:
                raise ValueError(f"unexpected CSV header for {ident}: {reader.fieldnames}")
            rows = list(reader)
        if len(rows) != EXPECTED_RESULTS_PER_MACHINE:
            raise ValueError(f"expected {EXPECTED_RESULTS_PER_MACHINE} rows for {ident}, got {len(rows)}")
        observed = {row["dataset"] for row in rows}
        if observed != set(dataset_sizes):
            raise ValueError(f"dataset identifiers differ for {ident}")
        if any(int(row["compressed_size"]) < 0 or row["plugin"] == "" or row["codec"] == "" for row in rows):
            raise ValueError(f"invalid result row in {ident}")
        files.append({"machine": ident, "path": f"raw/{ident}.csv", "source_url": f"{RAW}/data/{ident}.csv",
                      "rows": len(rows), "bytes": len(data), "git_blob_sha1": blob,
                      "sha256": hashlib.sha256(data).hexdigest()})

    manifest = {
        "schema": 1,
        "title": "Squash Compression Benchmark — published results import",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "upstream_page": "https://quixdb.github.io/squash-benchmark/",
        "upstream_repository": f"https://github.com/{REPO}",
        "upstream_commit": COMMIT,
        "upstream_commit_url": f"https://github.com/{REPO}/commit/{COMMIT}",
        "upstream_js_url": JS_URL,
        "upstream_js_sha256": hashlib.sha256(js.encode("utf-8")).hexdigest(),
        "license": "CC0-1.0 for benchmark data as stated by the benchmark site; attribution retained.",
        "metrics": {"size": "compressed_size bytes", "ratio": "dataset original bytes / compressed_size",
                    "compression_time": "compress_cpu seconds", "decompression_time": "decompress_cpu seconds",
                    "compression_speed": "original bytes / compress_cpu / 1048576 MiB/s",
                    "decompression_speed": "original bytes / decompress_cpu / 1048576 MiB/s",
                    "timing_basis": "CPU time; published site says wall-clock is captured but not displayed."},
        "dataset_count": len(datasets), "machine_count": len(machines),
        "results_per_machine": EXPECTED_RESULTS_PER_MACHINE,
        "result_count": EXPECTED_MACHINE_COUNT * EXPECTED_RESULTS_PER_MACHINE,
        "datasets": datasets, "machines": machines, "files": files,
        "comparability_note": "These are Squash's published results on the listed historical machines and settings. They are shown as a separate external benchmark and are not combined with local CIX rankings or treated as same-hardware results.",
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"datasets": len(datasets), "machines": len(machines), "results": manifest["result_count"],
                      "raw_bytes": sum(f["bytes"] for f in files), "verified_files": len(files)}, sort_keys=True))


if __name__ == "__main__":
    main()
