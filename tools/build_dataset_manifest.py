#!/usr/bin/env python3
"""Build an acquisition-only manifest for the external CIX dataset store.

This program neither downloads nor transforms data.  It verifies source-declared
sizes where available and hashes only complete byte streams.  By default it
writes the JSON manifest outside the repository; pass --output to create a
versioned review copy once an acquisition batch has finished.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import date
from pathlib import Path


ROOT = Path("/home/user/cix-datasets")
REPO = Path(__file__).resolve().parents[1]
PREP = REPO / "docs/research/2026-09-30-dataset-preparation"

SILESIA_MD5 = {
    "dickens": "88334708559f6db57d79096bc0aca07e", "mozilla": "c7789a2097f1ff944b0c737430a339b3",
    "mr": "38e623e3093b7bf2003ca4b1bbc19927", "nci": "31f85bc8706f3c921104e7c169e2e2e1",
    "ooffice": "573c4ae915e36631d8f2dcffb9b9b66d", "osdb": "e734b0c48e6a982adfb5802da3032ecd",
    "reymont": "d8f54d78105079775f32d76dc55fc671", "samba": "154eaea7ea70e89f6339ff0abf4112ca",
    "sao": "79e95a22e18cd82b7e42bf91b380d30b", "webster": "474931ad907ac27bf962c75ded46c069",
    "x-ray": "9baec32ad14ec3eff487d254382cb91c", "xml": "9b09c0c80104adb8aae910b7d7db003e",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def file_record(path: Path, expected_bytes: int | None = None, **extra: object) -> dict[str, object]:
    record: dict[str, object] = {"path": str(path), **extra}
    if not path.is_file():
        record.update(status="MISSING", bytes=None, sha256=None)
        return record
    size = path.stat().st_size
    complete = expected_bytes is None or size == expected_bytes
    record.update(
        status="READY" if complete else "SIZE_MISMATCH",
        bytes=size,
        expected_bytes=expected_bytes,
        # A size mismatch is not a verified benchmark input, but it is still
        # an acquired artifact and must be identifiable for review/recovery.
        sha256=sha256(path),
    )
    return record


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "manifests/dataset-preparation-2026-09-30.json")
    args = parser.parse_args()
    generated = date.today().isoformat()

    silesia_root = REPO / "benchmark-work/silesia"
    silesia = []
    for name, published_md5 in SILESIA_MD5.items():
        rec = file_record(silesia_root / name, source="https://mattmahoney.net/dc/silesia.html", layout="original raw file")
        rec["published_md5"] = published_md5
        silesia.append({"name": name, **rec})

    fcbench = []
    with (PREP / "fcbench-files.tsv").open(newline="") as table:
        reader = csv.reader(table, delimiter="\t")
        for row in reader:
            if not row or row[0].startswith("#"):
                continue
            name, file_id, dtype, shape, declared, category = row
            fcbench.append({
                "name": name, "google_drive_id": file_id, "declared_type": dtype,
                "declared_shape": shape, "class": category,
                **file_record(ROOT / "originals/fcbench" / name, int(declared),
                            source="https://github.com/hpdps-group/FCBench", layout="raw FCBench source bytes"),
            })

    golf_archive = ROOT / "archives/compression-golf-data.json.gz"
    golf_json = ROOT / "originals/compression-golf/data.json"
    golf = {
        "status": "PARTIAL",
        "source_commit": "b1a5218a6730984f0b52bc293cff12925e2c5e2a",
        "source": "https://github.com/agavra/compression-golf",
        "training_archive": file_record(golf_archive, layout="gzip-compressed supplied JSONL"),
        "training_jsonl": file_record(golf_json, layout="one million parsed GitHub-event JSON records"),
        "evaluation": {"status": "NOT_RELEASED", "detail": "No official evaluation asset was present at the pinned source commit."},
    }

    document = {
        "schema": "cix.dataset-preparation.v1",
        "generated_on": generated,
        "external_dataset_root": str(ROOT),
        "scope": "acquisition and verification only; no compression experiments",
        "opportunities": {
            "silesia": {"status": "READY", "files": silesia},
            "fcbench": {
                "status": "PARTIAL",
                "source_commit": "aba31b51959e16b78b1ad1c06757248e31a00362",
                "access": "public Google Drive IDs published in the FCBench repository; no per-object publisher checksum supplied",
                "files": fcbench,
                "retained_invalid_artifacts": [file_record(
                    ROOT / "archives/fcbench-invalid-resumes/astro_pt_f64.size-1008685056",
                    source="https://github.com/hpdps-group/FCBench",
                    layout="interrupted-resume artifact; not a benchmark input",
                )],
            },
            "raw_astronomical_image": {
                "status": "BLOCKED",
                "source": "https://pratas.github.io/rai-challenge.html",
                "training_link": "https://pratas.github.io/data/data2.zip",
                "source_page_snapshot": file_record(ROOT / "archives/rai-challenge.html", layout="official challenge-page HTML snapshot"),
                "detail": "The official training URL returned HTTP 404 on 2026-09-30; evaluation assets are intentionally withheld.",
            },
            "compression_golf": golf,
            "gdcc": {
                "status": "BLOCKED",
                "edition": "4th Global Data Compression Competition (closed 2025-04-15)",
                "source": "https://gdcc.tech/rules/",
                "detail": "Public samples are described as residing in an official VM. No direct dataset URL could be resolved from the currently reachable source, and the reported VM archive/extraction footprint exceeds the safe remaining storage budget.",
            },
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
