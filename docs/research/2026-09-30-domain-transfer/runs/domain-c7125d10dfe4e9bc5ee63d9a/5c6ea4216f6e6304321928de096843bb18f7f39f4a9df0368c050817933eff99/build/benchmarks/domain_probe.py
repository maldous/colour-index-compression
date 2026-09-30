#!/usr/bin/env python3
"""Self-contained generic domain-transform compression probe.

The archive names its domain adapter and variant in paid canonical JSON.  It is
an experiment harness: no input filename, corpus hash, selector, dictionary, or
sidecar participates in decoding.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import types
from pathlib import Path

MAGIC = b"CIXDOM01"
HEADER = struct.Struct(">8sBBQQI")
PAQ, NATIVE = 1, 2
DOMAINS = {
    "molecular": (1, "benchmarks.domain_molecular"),
    "numeric": (2, "benchmarks.domain_numeric_noaa"),
    "database": (3, "benchmarks.domain_database_csv"),
    "executable": (4, "benchmarks.domain_executable_adapter"),
    "volume": (5, "benchmarks.domain_volume"),
}
BY_CODE = {code: (name, adapter) for name, (code, adapter) in DOMAINS.items()}
COPY = 1024 * 1024
_SNAPSHOT_ROOT: Path | None = None


def _within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def bootstrap_snapshot(snapshot_root: Path) -> None:
    """Force benchmark and CIX imports to a frozen snapshot root.

    ``benchmarks`` is a namespace package in this repository.  Explicitly
    constraining its path prevents a missing snapshot module from falling back
    through editable-install import hooks to the live checkout.
    """
    global _SNAPSHOT_ROOT
    root = Path(snapshot_root).resolve()
    benchmarks_root, cix_root = root / "benchmarks", root / "cix"
    if not benchmarks_root.is_dir() or not cix_root.is_dir() or not (cix_root / "__init__.py").is_file():
        raise RuntimeError("snapshot root lacks required benchmarks/ and cix/ packages")
    sys.path[:] = [str(root), *[entry for entry in sys.path if Path(entry or ".").resolve() != root]]
    for name in tuple(sys.modules):
        if name == "benchmarks" or name.startswith("benchmarks.") or name == "cix" or name.startswith("cix."):
            del sys.modules[name]
    namespace = types.ModuleType("benchmarks")
    namespace.__package__ = "benchmarks"
    namespace.__path__ = [str(benchmarks_root)]
    sys.modules["benchmarks"] = namespace
    cix = importlib.import_module("cix")
    if not _within(Path(cix.__file__ or ""), root):
        raise RuntimeError("snapshot cix package resolved outside snapshot root")
    cix.__path__ = [str(cix_root)]
    _SNAPSHOT_ROOT = root
    audit_snapshot_imports()


def audit_snapshot_imports() -> dict[str, dict[str, str]]:
    """Fail closed if any loaded benchmark or CIX source escaped the snapshot."""
    if _SNAPSHOT_ROOT is None:
        return {}
    diagnostics = {}
    for name, module in sorted(tuple(sys.modules.items())):
        if name not in ("benchmarks", "cix") and not name.startswith(("benchmarks.", "cix.")):
            continue
        if name == "benchmarks":
            paths = [Path(value) for value in getattr(module, "__path__", ())]
            if paths != [_SNAPSHOT_ROOT / "benchmarks"]:
                raise RuntimeError("benchmarks namespace escaped snapshot root")
            continue
        path_text = getattr(module, "__file__", None)
        if not path_text:
            raise RuntimeError(f"{name} has no auditable source path")
        path = Path(path_text)
        if not _within(path, _SNAPSHOT_ROOT):
            raise RuntimeError(f"{name} resolved outside snapshot root: {path}")
        diagnostics[name] = {"path": str(path.relative_to(_SNAPSHOT_ROOT)), "sha256": sha256(path.read_bytes())}
    return diagnostics


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_meta(variant: str, source: bytes) -> bytes:
    return json.dumps({"source_sha256": sha256(source), "variant": variant},
                      sort_keys=True, separators=(",", ":")).encode("utf-8")


def _read_meta(blob: bytes) -> dict:
    try:
        meta = json.loads(blob.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("invalid domain metadata") from error
    if list(meta) != ["source_sha256", "variant"] or not isinstance(meta["variant"], str):
        raise ValueError("unsupported domain metadata")
    if not isinstance(meta["source_sha256"], str) or len(meta["source_sha256"]) != 64:
        raise ValueError("invalid source SHA-256 metadata")
    return meta


def _checked_binary(path: Path, expected_sha: str) -> Path:
    path = Path(path)
    if len(expected_sha) != 64 or any(byte not in "0123456789abcdef" for byte in expected_sha.lower()):
        raise ValueError("PAQ SHA-256 must be 64 hexadecimal characters")
    if not path.is_file() or sha256(path.read_bytes()) != expected_sha.lower():
        raise ValueError("PAQ binary SHA-256 mismatch")
    return path


def _load_adapter(adapter):
    loaded = importlib.import_module(adapter) if isinstance(adapter, str) else adapter
    audit_snapshot_imports()
    return loaded


def _adapter(domain: str):
    # ``numerical`` was an early spelling. The archive always records the
    # canonical short form, so a decoder and a manifest agree on ``numeric``.
    domain = "numeric" if domain == "numerical" else domain
    try:
        code, adapter = DOMAINS[domain]
        return domain, code, _load_adapter(adapter)
    except KeyError as error:
        raise ValueError("unknown domain") from error


def _transform(adapter, data: bytes, variant: str) -> bytes:
    return data if variant == "original" else adapter.encode(data, variant)


def _inverse(adapter, transformed: bytes, variant: str) -> bytes:
    return transformed if variant == "original" else adapter.decode(transformed)


def _native_allowed(domain: str, variant: str) -> bool:
    return domain == "volume" and variant == "jxl-planar3-e10"


def _temporary_root(temporary: Path | None) -> Path:
    if temporary is not None:
        temporary.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix="cix-domain-probe-", dir=temporary))


def _paq_encode(transformed: bytes, binary: Path, root: Path) -> bytes:
    source = root / "candidate.source.bin"
    archive = root / "candidate.payload.paq8px216"
    source.write_bytes(transformed)
    subprocess.run([str(binary), "-4", "-simd", "AVX2", str(source), str(archive)], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return archive.read_bytes()


def _paq_decode(payload: bytes, binary: Path, root: Path) -> bytes:
    archive = root / "payload.paq8px216"
    output = root / "decoded.bin"
    archive.write_bytes(payload)
    subprocess.run([str(binary), "-d", "-simd", "AVX2", str(archive), str(output)], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return output.read_bytes()


def _parse(frame: bytes) -> tuple[str, object, int, int, int, bytes, bytes]:
    if len(frame) < HEADER.size or frame[:8] != MAGIC:
        raise ValueError("invalid domain probe frame")
    magic, domain_code, backend, original_bytes, transformed_bytes, meta_bytes = HEADER.unpack_from(frame)
    if magic != MAGIC or backend not in (PAQ, NATIVE):
        raise ValueError("unsupported domain probe frame")
    try:
        domain, adapter = BY_CODE[domain_code]
    except KeyError as error:
        raise ValueError("unknown domain code") from error
    end_meta = HEADER.size + meta_bytes
    if end_meta > len(frame):
        raise ValueError("truncated domain metadata")
    metadata = frame[HEADER.size:end_meta]
    payload = frame[end_meta:]
    if not payload:
        raise ValueError("empty domain payload")
    return domain, _load_adapter(adapter), backend, original_bytes, transformed_bytes, metadata, payload


def encode(data: bytes, *, domain: str, variant: str, backend: str, paq_binary_path: Path,
           paq_sha256: str, temporary: Path | None = None) -> tuple[bytes, dict]:
    domain, code, adapter = _adapter(domain)
    if backend not in ("paq", "native"):
        raise ValueError("backend must be paq or native")
    if backend == "native" and not _native_allowed(domain, variant):
        raise ValueError("native backend is only volume jxl-planar3-e10")
    binary = _checked_binary(paq_binary_path, paq_sha256)
    transformed = _transform(adapter, data, variant)
    root = _temporary_root(temporary)
    started = time.perf_counter()
    try:
        payload = _paq_encode(transformed, binary, root) if backend == "paq" else transformed
        metadata = _canonical_meta(variant, data)
        frame = HEADER.pack(MAGIC, code, PAQ if backend == "paq" else NATIVE, len(data), len(transformed), len(metadata)) + metadata + payload
        return frame, {"policy": "cix-domain-probe-v1", "operation": "encode", "domain": domain,
                       "variant": variant, "backend": backend, "actual_backend": backend,
                       "source_bytes": len(data), "source_sha256": sha256(data),
                       "transformed_bytes": len(transformed), "payload_bytes": len(payload),
                       "header_bytes": HEADER.size, "metadata_bytes": len(metadata),
                       "physical_bytes": len(frame), "raw_transform_bytes": len(transformed),
                       "metadata": json.loads(metadata), "paq_options": "-4 -simd AVX2" if backend == "paq" else None,
                       "paq_binary_sha256": paq_sha256.lower(), "round_trip": "not_verified_by_encoder",
                       "seconds": time.perf_counter() - started}
    finally:
        shutil.rmtree(root, ignore_errors=True)


def decode(frame: bytes, *, paq_binary_path: Path, paq_sha256: str,
           temporary: Path | None = None) -> bytes:
    domain, adapter, backend, original_bytes, transformed_bytes, metadata_blob, payload = _parse(frame)
    metadata = _read_meta(metadata_blob)
    binary = _checked_binary(paq_binary_path, paq_sha256)
    if backend == NATIVE and not _native_allowed(domain, metadata["variant"]):
        raise ValueError("unsupported native domain payload")
    root = _temporary_root(temporary)
    try:
        transformed = _paq_decode(payload, binary, root) if backend == PAQ else payload
        if len(transformed) != transformed_bytes:
            raise ValueError("domain transformed length mismatch")
        restored = _inverse(adapter, transformed, metadata["variant"])
        if len(restored) != original_bytes or sha256(restored) != metadata["source_sha256"]:
            raise ValueError("domain source integrity mismatch")
        return restored
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _write_exclusive(path: Path, content: bytes) -> None:
    with path.open("xb") as output:
        output.write(content)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("encode", "decode"))
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--domain")
    parser.add_argument("--variant")
    parser.add_argument("--backend", choices=("paq", "native"))
    parser.add_argument("--paq-binary", required=True, type=Path)
    parser.add_argument("--paq-sha256", required=True)
    parser.add_argument("--temporary", type=Path)
    parser.add_argument("--snapshot-root", type=Path, help="frozen runtime root; imports fail closed outside it")
    args = parser.parse_args()
    source = args.input.read_bytes()
    started = time.perf_counter()
    if args.operation == "encode":
        if not args.domain or not args.variant or not args.backend:
            parser.error("encode requires --domain, --variant and --backend")
        output, report = encode(source, domain=args.domain, variant=args.variant, backend=args.backend,
                                paq_binary_path=args.paq_binary, paq_sha256=args.paq_sha256,
                                temporary=args.temporary or args.output.parent / "probe-temp")
        _write_exclusive(args.output, output)
    else:
        output = decode(source, paq_binary_path=args.paq_binary, paq_sha256=args.paq_sha256,
                        temporary=args.temporary or args.output.parent / "probe-temp")
        _write_exclusive(args.output, output)
        domain, _adapter, backend, original_bytes, transformed_bytes, metadata, payload = _parse(source)
        report = {"policy": "cix-domain-probe-v1", "operation": "decode", "domain": domain,
                  "variant": _read_meta(metadata)["variant"], "actual_backend": "paq" if backend == PAQ else "native",
                  "source_bytes": len(source), "output_bytes": len(output), "output_sha256": sha256(output),
                  "transformed_bytes": transformed_bytes, "payload_bytes": len(payload), "header_bytes": HEADER.size,
                  "metadata_bytes": len(metadata), "physical_bytes": len(source), "round_trip": len(output) == original_bytes}
    report["seconds"] = time.perf_counter() - started
    if _SNAPSHOT_ROOT is not None:
        report["snapshot_dependencies"] = audit_snapshot_imports()
    print(json.dumps(report, sort_keys=True, indent=2))


if __name__ == "__main__":
    snapshot = None
    for index, value in enumerate(sys.argv[1:]):
        if value == "--snapshot-root":
            try:
                snapshot = Path(sys.argv[index + 2])
            except IndexError as error:
                raise SystemExit("--snapshot-root requires a path") from error
            break
    bootstrap_snapshot(snapshot or Path(__file__).resolve().parents[1])
    main()
