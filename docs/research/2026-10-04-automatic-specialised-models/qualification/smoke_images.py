#!/usr/bin/env python3
"""Focused staged image-backend qualification; inert without ``--execute``.

Each operation writes a fixture and its current archive under ``--work``.
Encoding and decoding run in separate staged-Python processes, so a failure
leaves the source, archive, child output, and final receipt available for review.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess

MEMORY_BYTES = 768 << 20


def _tag(group: int, element: int, value: bytes) -> bytes:
    return (group.to_bytes(2, "little") + element.to_bytes(2, "little")
            + len(value).to_bytes(4, "little") + value)


def _dicom(values: list[int]) -> bytes:
    if len(values) != 8 * 8 * 2:
        raise ValueError("fixture must contain two 8x8 slices")
    pixels = struct.pack("<" + "H" * len(values), *values)
    return (_tag(0x28, 0x10, (8).to_bytes(2, "little"))
            + _tag(0x28, 0x11, (8).to_bytes(2, "little"))
            + _tag(0x28, 0x100, (16).to_bytes(2, "little"))
            + _tag(0x7FE0, 0x0010, pixels))


def _fixtures() -> dict[str, bytes]:
    count = 8 * 8 * 2
    return {
        "zeros": _dicom([0] * count),
        "u8range": _dicom([index % 256 for index in range(count)]),
        "highbit": _dicom([256 + (index * 257) % 65000 for index in range(count)]),
    }


ENCODE_PROGRAM = r'''
import hashlib, json, sys
from pathlib import Path
from cix_runtime import image_grid
from cix_runtime.legacy import spatial_image_codec as spatial
from cix_runtime.legacy import volume_image_codec as volume
from cix_runtime.legacy import multiscale_volume as multiscale
source = Path(sys.argv[1]).read_bytes(); archive = Path(sys.argv[2]); operation = sys.argv[3]
region = spatial.regions(source)[0]
if operation.startswith("spatial:"):
    frame = spatial.encode_region(source, region, operation.split(":", 1)[1], 10)
    report = {"format": frame[:5].decode("latin1")}
elif operation.startswith("volume:"):
    mode = int(operation.split(":", 1)[1])
    frame = volume.encode(source, region, mode, 9)
    report = {"format": frame[:5].decode("latin1"), "mode": mode}
elif operation == "multiscale":
    frame, report = multiscale.encode(source, region, 0, 0, 0, 10)
    report["format"] = frame[:5].decode("latin1")
elif operation == "shared":
    frame, report = image_grid._mode3_identity(source, region)
else:
    raise ValueError("unknown image operation")
archive.write_bytes(frame)
print(json.dumps({"status":"encoded", "bytes":len(frame), "sha256":hashlib.sha256(frame).hexdigest(), "report":report}))
'''

DECODE_PROGRAM = r'''
import hashlib, json, sys
from pathlib import Path
from cix_runtime.image_grid import DECODERS
frame = Path(sys.argv[1]).read_bytes(); expected = sys.argv[2]; maximum = int(sys.argv[3]); memory = int(sys.argv[4])
decoder = DECODERS.get(frame[:5])
if decoder is None: raise ValueError("no staged image decoder for magic")
data = decoder(frame, maximum, memory)
digest = hashlib.sha256(data).hexdigest()
if digest != expected: raise ValueError("restored digest mismatch")
print(json.dumps({"status":"decoded", "bytes":len(data), "sha256":digest}))
'''


def _environment(stage: Path) -> dict[str, str]:
    return {
        "PATH": "/usr/bin:/bin",
        "PYTHONPATH": str(stage / "python" / "site-packages"),
        "LD_LIBRARY_PATH": str(stage / "python" / "site-packages" / "imagecodecs.libs"),
        "CIX_BACKEND_ROOT": str(stage / "libexec" / "cix"),
        "PYTHONHOME": "",
    }


def _child(python: Path, env: dict[str, str], program: str, *args: str) -> dict:
    completed = subprocess.run([str(python), "-c", program, *args], env=env,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    row = json.loads(lines[-1]) if lines else {"status": "failed", "error": "no child receipt"}
    row["exit_code"] = completed.returncode
    if completed.stderr:
        row["stderr"] = completed.stderr[-4000:]
    return row


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if not args.execute:
        print("plan: pass --execute only from the root scheduler")
        return
    stage = args.stage.resolve()
    python = stage / "python" / "bin" / "python3"
    if not python.is_file():
        raise SystemExit("stage must contain python/bin/python3")
    work = args.work.resolve(); work.mkdir(parents=True, exist_ok=True)
    env = _environment(stage)
    operations = [("spatial:jxl", "zeros"), ("spatial:jls", "u8range"),
                  ("spatial:j2k", "highbit"), *[(f"volume:{mode}", "highbit") for mode in range(6)],
                  ("shared", "highbit"), ("volume:3", "zeros"), ("volume:3", "u8range"),
                  ("multiscale", "zeros"), ("multiscale", "u8range"),
                  ("shared", "zeros"), ("shared", "u8range")]
    report = {"schema": "cix-image-smoke-v1", "stage": str(stage), "memory_bytes": MEMORY_BYTES, "rows": []}
    fixtures = _fixtures()
    for ordinal, (operation, fixture_name) in enumerate(operations):
        source = work / f"{ordinal:02d}-{fixture_name}.bin"
        archive = work / f"{ordinal:02d}-{operation.replace(':', '-')}.cix"
        source.write_bytes(fixtures[fixture_name])
        digest = hashlib.sha256(fixtures[fixture_name]).hexdigest()
        encoded = _child(python, env, ENCODE_PROGRAM, str(source), str(archive), operation)
        row = {"operation": operation, "fixture": fixture_name, "input_sha256": digest, "encode": encoded}
        if encoded.get("status") == "encoded" and encoded.get("exit_code") == 0 and archive.is_file():
            row["decode"] = _child(python, env, DECODE_PROGRAM, str(archive), digest, str(len(fixtures[fixture_name])), str(MEMORY_BYTES))
        else:
            row["decode"] = {"status": "skipped", "reason": "encode did not yield an archive"}
        report["rows"].append(row)
    report["status"] = "VERIFIED" if all(row["decode"].get("status") == "decoded" and row["decode"].get("exit_code") == 0 for row in report["rows"]) else "FAILED"
    receipt = work / "smoke-images.json"; receipt.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "rows": len(report["rows"]), "receipt": str(receipt)}))
    if report["status"] != "VERIFIED": raise SystemExit(1)


if __name__ == "__main__":
    main()
