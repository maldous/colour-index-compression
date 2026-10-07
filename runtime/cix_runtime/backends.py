"""Pinned native-backend adapters for the integrated CIX runtime.

This module deliberately has no dependency on benchmark, results, corpus, or
certificate paths. Backends are resolved from the installed closure only.
"""
from __future__ import annotations

import os
from pathlib import Path
import resource
import subprocess
import tempfile
from typing import Callable, Mapping

CIXP = b"CIXP\x01"
PAQ_MAGIC = b"paq8px"
PAQ_IDS = {"v215": 1, "v216": 2}
ID_PAQ = {value: key for key, value in PAQ_IDS.items()}
BACKEND_NAMES = ("v215", "v216", "joint-discount", "store-state")
DEFAULT_TIMEOUT_SECONDS = 43_200
NATIVE_BEST_DEFAULT_MEMORY = 8_000_000_000
# PAQ streams do not expose a stable, independently validated allocation field.
# Admit them only with this conservative per-child address-space allowance.
PAQ_DECODE_MINIMUM_MEMORY = 4_500_000_000


def _root() -> Path:
    configured = os.environ.get("CIX_BACKEND_ROOT")
    if configured:
        return Path(configured).resolve()
    return Path(__file__).resolve().parents[2] / "libexec" / "cix"


def _binary_name(version: str) -> str:
    if version not in BACKEND_NAMES:
        raise ValueError(f"unsupported PAQ backend: {version}")
    return f"paq8px-{version}"


def paq_binary(version: str) -> str:
    """Return an installed PAQ backend without consulting research paths."""
    binary = _root() / _binary_name(version)
    if not binary.is_file() or not os.access(binary, os.X_OK):
        raise RuntimeError(f"required PAQ backend is unavailable: {version}")
    return str(binary)


def _resource_policy(memory_bytes: int, max_output_bytes: int) -> Callable[[], None]:
    """Return a child-only resource policy for a bounded decoder invocation."""
    def apply() -> None:
        resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
        resource.setrlimit(resource.RLIMIT_FSIZE, (max_output_bytes, max_output_bytes))
    return apply


def _write_diagnostics(stderr: bytes) -> None:
    target = os.environ.get("CIX_CANDIDATE_DIAGNOSTICS")
    if not target:
        return
    path = Path(target)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("ab") as handle:
        handle.write(stderr)
        if stderr and not stderr.endswith(b"\n"):
            handle.write(b"\n")


def _run(
    command: list[str],
    *,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    env: Mapping[str, str] | None = None,
    memory_bytes: int | None = None,
    max_output_bytes: int | None = None,
    diagnostics: bool = False,
) -> None:
    """Run one direct backend child within its caller's process group.

    The candidate worker owns the process group and kills it on a deadline.
    This helper deliberately neither creates nor kills a separate process group.
    """
    if (memory_bytes is None) != (max_output_bytes is None):
        raise ValueError("decoder resource limits require memory and output bounds")
    environment = os.environ.copy()
    if env:
        environment.update(env)
    process = subprocess.Popen(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        env=environment,
        preexec_fn=(
            _resource_policy(memory_bytes, max_output_bytes)
            if memory_bytes is not None and max_output_bytes is not None
            else None
        ),
    )
    try:
        _, stderr = process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired as error:
        process.kill()
        _, stderr = process.communicate()
        if diagnostics:
            _write_diagnostics(stderr)
        raise RuntimeError("native backend timed out; outer candidate process group remains responsible for descendants") from error
    if diagnostics:
        _write_diagnostics(stderr)
    if process.returncode:
        message = stderr.decode(errors="replace").strip()
        raise RuntimeError(f"native backend failed ({process.returncode}): {message or 'no diagnostic'}")


def _wrap(blob: bytes, version: str) -> bytes:
    if not blob.startswith(PAQ_MAGIC) or len(blob) < len(PAQ_MAGIC):
        raise ValueError("PAQ backend produced an invalid stream")
    return CIXP + bytes([PAQ_IDS[version]]) + blob[len(PAQ_MAGIC):]


def _unwrap(frame: bytes) -> tuple[str, bytes]:
    if len(frame) < len(CIXP) + 1 or frame[:len(CIXP)] != CIXP:
        raise ValueError("invalid CIXP frame")
    version = ID_PAQ.get(frame[len(CIXP)])
    if version is None:
        raise ValueError("unsupported CIXP backend identifier")
    return version, PAQ_MAGIC + frame[len(CIXP) + 1:]


def encode_paq(data: bytes, version: str = "v216", options: str = "-8", *, timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS) -> bytes:
    """Encode a fresh input with pinned PAQ v215/v216 and return a CIXP frame."""
    if version not in PAQ_IDS:
        raise ValueError("encode_paq supports v215 or v216")
    with tempfile.TemporaryDirectory(prefix="cix-paq-") as folder:
        root = Path(folder)
        source = root / "source.bin"
        archive = root / f"stream.paq8px{version[1:]}"
        source.write_bytes(data)
        _run([paq_binary(version), options, "-simd", "AVX2", str(source), str(archive)], timeout_seconds=timeout_seconds)
        return _wrap(archive.read_bytes(), version)


def decode_paq(frame: bytes, max_output_bytes: int, memory_bytes: int, *, timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS) -> bytes:
    """Decode a CIXP frame under pre-write output and address-space bounds."""
    if max_output_bytes < 0 or memory_bytes <= 0:
        raise ValueError("invalid decode limits")
    version, blob = _unwrap(frame)
    if memory_bytes < PAQ_DECODE_MINIMUM_MEMORY:
        raise ValueError("PAQ decode memory limit is below the conservative 4.5 GB admission")
    with tempfile.TemporaryDirectory(prefix="cix-paq-") as folder:
        root = Path(folder)
        archive, output = root / f"stream.paq8px{version[1:]}", root / "decoded.bin"
        archive.write_bytes(blob)
        _run(
            [paq_binary(version), "-d", "-simd", "AVX2", str(archive), str(output)],
            timeout_seconds=timeout_seconds,
            memory_bytes=memory_bytes,
            max_output_bytes=max_output_bytes,
        )
        if not output.is_file() or output.stat().st_size > max_output_bytes:
            raise ValueError("PAQ decoded output exceeds the archive admission limit")
        return output.read_bytes()


def _native_binary(name: str) -> Path:
    binary = _root() / name
    if not binary.is_file() or not os.access(binary, os.X_OK):
        raise RuntimeError(f"required native CIX backend is unavailable: {name}")
    return binary


def native_encode(data: bytes, profile: str = "best", memory_bytes: int = NATIVE_BEST_DEFAULT_MEMORY, threads: int = 1, *, timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS) -> bytes:
    """Run the pinned native CIX backend as a complete archive candidate."""
    if profile not in {"fast", "default", "best"} or threads < 1 or memory_bytes <= 0:
        raise ValueError("invalid native backend settings")
    with tempfile.TemporaryDirectory(prefix="cix-native-") as folder:
        root = Path(folder)
        source, archive = root / "source.bin", root / "archive.cix"
        source.write_bytes(data)
        command = [str(_native_binary("cix-native"))]
        if profile == "fast":
            command.append("--fast")
        elif profile == "best":
            command.append("--best")
        command.extend(["--explain", "--memory", f"{memory_bytes}B", "--threads", str(threads), "-f", "-o", str(archive), str(source)])
        _run(command, timeout_seconds=timeout_seconds, diagnostics=True)
        return archive.read_bytes()


def native_decode(frame: bytes, max_output_bytes: int, memory_bytes: int, *, timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS) -> bytes:
    """Decode native CIX under pre-write output and address-space bounds."""
    if max_output_bytes < 0 or memory_bytes <= 0:
        raise ValueError("invalid decode limits")
    with tempfile.TemporaryDirectory(prefix="cix-native-") as folder:
        root = Path(folder)
        archive, output = root / "archive.cix", root / "decoded.bin"
        archive.write_bytes(frame)
        _run(
            [str(_native_binary("uncix-native")), "-d", "--memory", f"{memory_bytes}B", "-f", "-o", str(output), str(archive)],
            timeout_seconds=timeout_seconds,
            memory_bytes=memory_bytes,
            max_output_bytes=max_output_bytes,
        )
        if not output.is_file() or output.stat().st_size > max_output_bytes:
            raise ValueError("native decoded output exceeds the archive admission limit")
        return output.read_bytes()
