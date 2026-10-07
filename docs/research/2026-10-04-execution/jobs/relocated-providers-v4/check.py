#!/usr/bin/env python3
"""Focused, explicit-runtime validation for relocated CIX providers.

This helper is deliberately not a test discovery entry point.  It executes only
when invoked directly and refuses every path except the supplied relocated
runtime.  It records binary/source hashes, every worker argv/result, and exact
round-trip comparisons in a private 0700 workspace.
"""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
from typing import Any

REPOSITORY = Path(__file__).resolve().parents[3]
DEFAULT_RUNTIME = REPOSITORY / "benchmark-work/native-rc-check-v1/runtime-closure-v1/relocated/usr"
MAX_IMAGE_OUTPUT = 1 << 20
PAQ_OUTPUT = 1 << 20


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def require_regular(path: Path, label: str) -> Path:
    path = path.resolve(strict=True)
    if not path.is_file() or path.is_symlink():
        raise RuntimeError(f"{label} must be an ordinary regular file: {path}")
    return path


def require_directory(path: Path, label: str) -> Path:
    path = path.resolve(strict=True)
    if not path.is_dir() or path.is_symlink():
        raise RuntimeError(f"{label} must be an ordinary directory: {path}")
    return path


def private_workspace(requested: Path | None) -> Path:
    if requested is None:
        path = Path(tempfile.mkdtemp(prefix="cix-relocated-provider-"))
    else:
        path = requested.resolve()
        path.mkdir(mode=0o700, parents=True, exist_ok=False)
    os.chmod(path, 0o700)
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode != 0o700:
        raise RuntimeError(f"workspace must be mode 0700, found {mode:03o}")
    return path


class Buffer(ctypes.Structure):
    _fields_ = [("data", ctypes.POINTER(ctypes.c_uint8)), ("size", ctypes.c_size_t)]


class Gray(ctypes.Structure):
    _fields_ = [
        ("pixels", ctypes.POINTER(ctypes.c_uint8)), ("pixels_size", ctypes.c_size_t),
        ("width", ctypes.c_uint32), ("height", ctypes.c_uint32),
        ("bits_per_sample", ctypes.c_uint32), ("sample_type", ctypes.c_uint32),
        ("effort", ctypes.c_uint32),
    ]


class Planar(ctypes.Structure):
    _fields_ = [
        ("pixels", ctypes.POINTER(ctypes.c_uint8)), ("pixels_size", ctypes.c_size_t),
        ("depth", ctypes.c_uint32), ("width", ctypes.c_uint32), ("height", ctypes.c_uint32),
        ("bits_per_sample", ctypes.c_uint32), ("sample_type", ctypes.c_uint32),
        ("effort", ctypes.c_uint32),
    ]


def image_round_trips(bridge_path: Path, receipt: dict[str, Any]) -> None:
    # Absolute filename is intentional: no PATH search or Python codec runtime.
    bridge = ctypes.CDLL(str(bridge_path), mode=ctypes.RTLD_LOCAL | os.RTLD_NOW)
    bridge.cix_jxl_encode_gray_2d.argtypes = [ctypes.POINTER(Gray), ctypes.c_size_t, ctypes.POINTER(Buffer)]
    bridge.cix_jxl_encode_planar.argtypes = [ctypes.POINTER(Planar), ctypes.c_size_t, ctypes.POINTER(Buffer)]
    for name in ("cix_jxl_encode_gray_2d", "cix_jxl_encode_planar"):
        getattr(bridge, name).restype = ctypes.c_int
    bridge.cix_jxl_decode_gray_2d.argtypes = [ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32, ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t]
    bridge.cix_jxl_decode_planar.argtypes = [ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32, ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t]
    bridge.cix_jxl_decode_gray_2d.restype = ctypes.c_int
    bridge.cix_jxl_decode_planar.restype = ctypes.c_int
    bridge.cix_jxl_free_buffer.argtypes = [ctypes.POINTER(Buffer)]
    bridge.cix_jxl_free_buffer.restype = None

    def run(kind: str, data: bytes, shape: tuple[int, ...]) -> None:
        source = (ctypes.c_uint8 * len(data)).from_buffer_copy(data)
        encoded = Buffer()
        if kind == "gray":
            width, height = shape
            image = Gray(source, len(data), width, height, 8, 1, 7)
            status = bridge.cix_jxl_encode_gray_2d(ctypes.byref(image), MAX_IMAGE_OUTPUT, ctypes.byref(encoded))
        else:
            depth, width, height = shape
            image = Planar(source, len(data), depth, width, height, 8, 1, 10)
            status = bridge.cix_jxl_encode_planar(ctypes.byref(image), MAX_IMAGE_OUTPUT, ctypes.byref(encoded))
        if status != 0:
            raise RuntimeError(f"JXL {kind} encode status={status}")
        try:
            codestream = ctypes.string_at(encoded.data, encoded.size)
            restored = (ctypes.c_uint8 * len(data))()
            packed = (ctypes.c_uint8 * len(codestream)).from_buffer_copy(codestream)
            if kind == "gray":
                width, height = shape
                status = bridge.cix_jxl_decode_gray_2d(packed, len(codestream), width, height, 8, 1, restored, len(data))
            else:
                depth, width, height = shape
                status = bridge.cix_jxl_decode_planar(packed, len(codestream), depth, width, height, 8, 1, restored, len(data))
            if status != 0 or bytes(restored) != data:
                raise RuntimeError(f"JXL {kind} round-trip failed status={status}")
            receipt["jxl"].append({"kind": kind, "shape": shape, "input_sha256": hashlib.sha256(data).hexdigest(), "codestream_sha256": hashlib.sha256(codestream).hexdigest(), "codestream_bytes": len(codestream), "exact": True})
        finally:
            bridge.cix_jxl_free_buffer(ctypes.byref(encoded))

    run("gray", bytes((i * 37 + 11) & 0xFF for i in range(7 * 5)), (7, 5))
    run("planar", bytes((i * 53 + 19) & 0xFF for i in range(3 * 5 * 4)), (3, 5, 4))


def run_paq(cix: Path, library: Path, workspace: Path, receipt: dict[str, Any], variants: list[str], level: str, memory: int) -> None:
    source = bytes((i * 29 + (i >> 3) + 7) & 0xFF for i in range(4096))
    input_path = workspace / "paq-input.bin"
    input_path.write_bytes(source)
    for variant in variants:
        encoded = workspace / f"{variant}.encoded"
        restored = workspace / f"{variant}.restored"
        joint = "0" if variant == "joint-discount" else "none"
        record: dict[str, Any] = {
            "variant": variant,
            "input_sha256": hashlib.sha256(source).hexdigest(),
            "commands": [],
        }
        receipt["paq"].append(record)
        for operation, src, dst in (("encode", input_path, encoded), ("decode", encoded, restored)):
            argv = [str(cix), "--internal-paq-worker-v1", variant, operation, str(library), str(src), str(dst), str(memory), str(PAQ_OUTPUT), level, "1", joint]
            completed = subprocess.run(argv, cwd=workspace, env={"LC_ALL": "C", "OMP_NUM_THREADS": "1"}, capture_output=True, text=True, check=False)
            record["commands"].append({"argv": argv, "returncode": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr})
            if completed.returncode != 0:
                raise RuntimeError(f"PAQ {variant} {operation} failed: {completed.stderr}")
        if restored.read_bytes() != source:
            raise RuntimeError(f"PAQ {variant} exact comparison failed")
        record.update({"encoded_sha256": sha256(encoded), "encoded_bytes": encoded.stat().st_size, "exact": True})


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", type=Path, default=DEFAULT_RUNTIME)
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--paq-variant", action="append", choices=("v215", "v216", "joint-discount", "store-state"))
    parser.add_argument("--paq-level", choices=tuple(f"-{number}" for number in range(13)), default="-0")
    parser.add_argument("--paq-memory", type=int, default=512 << 20)
    parser.add_argument("--jxl-header", type=Path, default=REPOSITORY / "rust/cix-native/codecs/jxl/cix_jxl_bridge.h")
    args = parser.parse_args()
    runtime = require_directory(args.runtime, "runtime")
    cix = require_regular(runtime / "bin/cix", "relocated cix")
    library = require_directory(runtime / "lib/cix", "relocated provider directory")
    bridge = require_regular(library / "libcix_jxl_bridge.so", "relocated JXL bridge")
    workspace = private_workspace(args.workspace)
    header = args.jxl_header
    if args.paq_memory <= 0:
        raise RuntimeError("PAQ memory must be positive")
    variants = args.paq_variant or ["v215", "v216", "joint-discount", "store-state"]
    receipt: dict[str, Any] = {"runtime": str(runtime), "workspace": str(workspace), "paq_controls": {"variants": variants, "level": args.paq_level, "memory": args.paq_memory, "output_cap": PAQ_OUTPUT}, "hashes": {"script": sha256(Path(__file__)), "jxl_bridge_header": sha256(require_regular(header, "JXL bridge header")), "cix": sha256(cix), "jxl_bridge": sha256(bridge), "provider_libraries": {path.name: sha256(path) for path in sorted(library.glob("*.so")) if path.is_file() and not path.is_symlink()}}, "jxl": [], "paq": []}
    try:
        image_round_trips(bridge, receipt)
        run_paq(cix, library, workspace, receipt, variants, args.paq_level, args.paq_memory)
        receipt["status"] = "ok"
    except Exception as error:
        receipt["status"] = "error"
        receipt["error"] = str(error)
        raise
    finally:
        (workspace / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
