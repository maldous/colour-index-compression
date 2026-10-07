#!/usr/bin/env python3
"""Scheduled-only runtime-closure qualification for an explicit frozen CIX set.

This helper performs no work on import.  The release scheduler must supply every
selected artifact path and a bounded disposable work directory.  It never finds
providers through PATH, LD_LIBRARY_PATH, a directory scan, or a workstation
fallback.  Its JSON receipt preserves both expected negative configuration and
post-relocation checks.
"""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

PAQ_NAMES = (
    "libcix_paq_v215_bridge.so",
    "libcix_paq_v216_bridge.so",
    "libcix_paq_joint_discount_bridge.so",
    "libcix_paq_store_state_bridge.so",
)
JXL_NAMES = (
    "libjxl.so.0.12.0", "libjxl_threads.so.0.12.0", "libjxl_cms.so.0.12.0",
    "libbrotlidec.so.1.2.0", "libbrotlienc.so.1.2.0", "libbrotlicommon.so.1.2.0",
)
COMPANION_NAMES = JXL_NAMES + ("libcharls.so.2.4.2", "libopenjp2.so.2.5.0")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def required_file(path: Path, label: str) -> Path:
    if not path.is_absolute() or not path.is_file():
        raise RuntimeError(f"{label} must be an existing absolute regular file: {path}")
    return path


def call(command: list[str], *, env: dict[str, str] | None = None,
         expect: int = 0, binary: bool = False) -> subprocess.CompletedProcess:
    result = subprocess.run(command, text=not binary, capture_output=True, env=env,
                            check=False, timeout=300)
    if result.returncode != expect:
        raise RuntimeError(
            f"unexpected exit {result.returncode}, expected {expect}: {command}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}")
    return result


def clean_loader_env() -> dict[str, str]:
    """Retain only harmless process basics; forbid loader/PATH provider fallback."""
    return {key: value for key, value in os.environ.items()
            if not key.startswith(("LD_", "DYLD_")) and key not in {"PATH", "PYTHONPATH"}}


def cmake_args(args: argparse.Namespace, cix: Path, jxl_bridge: Path) -> list[str]:
    paq = [args.paq_dir / name for name in PAQ_NAMES]
    jxl = [args.jxl_dir / name for name in JXL_NAMES]
    spatial = args.spatial_dir / "libcix_spatial_bridge.so"
    charls = args.codec_dir / "libcharls.so.2.4.2"
    openjpeg = args.codec_dir / "libopenjp2.so.2.5.0"
    values = {
        "CIX_RUNTIME_CIX_EXECUTABLE": cix,
        "CIX_RUNTIME_READELF": args.readelf,
        "CIX_RUNTIME_PAQ_V215_BRIDGE": paq[0],
        "CIX_RUNTIME_PAQ_V216_BRIDGE": paq[1],
        "CIX_RUNTIME_PAQ_JOINT_DISCOUNT_BRIDGE": paq[2],
        "CIX_RUNTIME_PAQ_STORE_STATE_BRIDGE": paq[3],
        "CIX_RUNTIME_JXL_BRIDGE": jxl_bridge,
        "CIX_RUNTIME_SPATIAL_BRIDGE": spatial,
        "CIX_RUNTIME_JXL_LIBRARY": jxl[0],
        "CIX_RUNTIME_JXL_THREADS_LIBRARY": jxl[1],
        "CIX_RUNTIME_JXL_CMS_LIBRARY": jxl[2],
        "CIX_RUNTIME_BROTLIDEC_LIBRARY": jxl[3],
        "CIX_RUNTIME_BROTLIENC_LIBRARY": jxl[4],
        "CIX_RUNTIME_BROTLICOMMON_LIBRARY": jxl[5],
        "CIX_RUNTIME_CHARLS_LIBRARY": charls,
        "CIX_RUNTIME_OPENJPEG_LIBRARY": openjpeg,
    }
    for key, value in values.items():
        required_file(Path(value), key)
    command = [str(args.cmake), "-S", str(args.runtime_source),
               "-DCMAKE_INSTALL_PREFIX=/usr", "-DCIX_RUNTIME_CAPABILITY=full-engine"]
    command.extend(f"-D{key}={value}" for key, value in values.items())
    return command


def inspect_dynamic(readelf: Path, paths: list[Path]) -> dict[str, str]:
    inspected: dict[str, str] = {}
    for path in paths:
        output = call([str(readelf), "-d", str(path)]).stdout
        if "RUNPATH" not in output or "$ORIGIN" not in output:
            raise RuntimeError(f"missing $ORIGIN RUNPATH: {path}")
        inspected[str(path)] = output
    return inspected


def load_bridges(paths: list[Path]) -> None:
    # The scheduler calls this in an environment with loader overrides removed.
    for path in paths:
        ctypes.CDLL(str(path))


def main() -> None:
    if os.environ.get("CIX_RELEASE_LEASE") != "1":
        raise RuntimeError("root scheduler lease is required")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-source", type=Path, required=True)
    parser.add_argument("--cix", type=Path, required=True)
    parser.add_argument("--paq-dir", type=Path, required=True)
    parser.add_argument("--jxl-dir", type=Path, required=True)
    parser.add_argument("--spatial-dir", type=Path, required=True)
    parser.add_argument("--codec-dir", type=Path, required=True)
    parser.add_argument("--wrong-rpath-jxl-bridge", type=Path, required=True)
    parser.add_argument("--spatial-frame", type=Path, required=True)
    parser.add_argument("--spatial-plain", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--cmake", type=Path, default=Path("/bin/cmake"))
    parser.add_argument("--readelf", type=Path, default=Path("/bin/readelf"))
    args = parser.parse_args()
    if not args.runtime_source.is_absolute() or not args.runtime_source.is_dir():
        raise RuntimeError("runtime source must be an explicit absolute directory")
    for label, path in (("cix", args.cix), ("cmake", args.cmake), ("readelf", args.readelf),
                        ("wrong-RPATH JXL bridge", args.wrong_rpath_jxl_bridge),
                        ("spatial frame", args.spatial_frame), ("spatial plain", args.spatial_plain)):
        required_file(path, label)
    if args.work.exists():
        raise RuntimeError(f"work directory must not exist: {args.work}")
    args.work.mkdir(parents=True)
    build_negative, build_full = args.work / "negative", args.work / "full"
    stage, relocated = args.work / "stage", args.work / "relocated"
    good_jxl_bridge = args.jxl_dir / "libcix_jxl_bridge.so"
    inputs = [args.cix, good_jxl_bridge, args.spatial_dir / "libcix_spatial_bridge.so",
              *(args.paq_dir / name for name in PAQ_NAMES), *(args.jxl_dir / name for name in JXL_NAMES),
              *(args.codec_dir / name for name in COMPANION_NAMES[-2:]), args.wrong_rpath_jxl_bridge]
    before = {str(required_file(item, "runtime input")): sha256(item) for item in inputs}
    negative = cmake_args(args, args.cix, args.wrong_rpath_jxl_bridge) + ["-B", str(build_negative)]
    failed = subprocess.run(negative, text=True, capture_output=True, check=False)
    if failed.returncode == 0:
        raise RuntimeError("wrong-RPATH negative configuration unexpectedly succeeded")
    after_negative = {str(item): sha256(item) for item in inputs}
    if before != after_negative:
        raise RuntimeError("negative RPATH configuration changed a selected source input")
    full = cmake_args(args, args.cix, good_jxl_bridge) + ["-B", str(build_full)]
    call(full)
    install_env = clean_loader_env() | {"DESTDIR": str(stage)}
    call([str(args.cmake), "--install", str(build_full)], env=install_env)
    stage.rename(relocated)
    prefix = relocated / "usr"
    binary = prefix / "bin/cix"
    aliases = [prefix / "bin/uncix", prefix / "bin/cixcat"]
    if not binary.is_file() or any(not item.is_symlink() or os.readlink(item) != "cix" for item in aliases):
        raise RuntimeError("relocated tree lacks one cix binary with exact aliases")
    runtime_lib = prefix / "lib/cix"
    expected = list(PAQ_NAMES) + ["libcix_jxl_bridge.so", "libcix_spatial_bridge.so", *COMPANION_NAMES]
    real_files = sorted(path.name for path in runtime_lib.iterdir() if path.is_file() and not path.is_symlink())
    if real_files != sorted(expected):
        raise RuntimeError("relocated runtime lib/cix real files differ from exact selected artifacts")
    sonames = {
        "libjxl.so.0.12": "libjxl.so.0.12.0",
        "libjxl_threads.so.0.12": "libjxl_threads.so.0.12.0",
        "libjxl_cms.so.0.12": "libjxl_cms.so.0.12.0",
        "libbrotlidec.so.1": "libbrotlidec.so.1.2.0",
        "libbrotlienc.so.1": "libbrotlienc.so.1.2.0",
        "libbrotlicommon.so.1": "libbrotlicommon.so.1.2.0",
        "libcharls.so.2": "libcharls.so.2.4.2",
        "libopenjp2.so.7": "libopenjp2.so.2.5.0",
    }
    if any(not (runtime_lib / name).is_symlink() or os.readlink(runtime_lib / name) != target
           for name, target in sonames.items()):
        raise RuntimeError("relocated runtime companion SONAME links differ from staged contract")
    origin_inputs = [runtime_lib / name for name in ["libcix_jxl_bridge.so", "libcix_spatial_bridge.so", *JXL_NAMES]]
    dynamic = inspect_dynamic(args.readelf, origin_inputs)
    load_env = clean_loader_env()
    loader = [sys.executable, "-c", "import ctypes,sys; [ctypes.CDLL(p) for p in sys.argv[1:]]", *map(str, [runtime_lib / name for name in list(PAQ_NAMES) + ["libcix_jxl_bridge.so", "libcix_spatial_bridge.so"]])]
    call(loader, env=load_env)
    decoded = args.work / "decoded.bin"
    call([str(binary), "-d", "-o", str(decoded), str(args.spatial_frame)], env=load_env)
    if decoded.read_bytes() != args.spatial_plain.read_bytes():
        raise RuntimeError("cix -d did not restore the supplied spatial fixture")
    cat = call([str(aliases[1]), str(args.spatial_frame)], env=load_env, binary=True)
    if cat.stdout != args.spatial_plain.read_bytes():
        raise RuntimeError("cixcat alias did not restore the supplied spatial fixture")
    plan = {
        "paq": "Run the existing same-CIX PAQ bridge contract/worker fixtures against this exact relocated lib/cix directory, then archive-only decode each emitted PAQ frame.",
        "jxl": "Run the existing jxl_provider and spatial frame fixtures against this exact relocated lib/cix directory, then archive-only decode each emitted JXL frame.",
        "limits": "Keep each provider fixture under the frozen resource policy; record bridge, companion and output hashes in the scheduled receipt."
    }
    receipt = {"negative_rpath_preserved_inputs": before, "readelf_dynamic_sections": dynamic,
               "runtime_plan": plan, "relocated_prefix": str(prefix)}
    (args.work / "runtime-closure-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")

if __name__ == "__main__":
    main()
