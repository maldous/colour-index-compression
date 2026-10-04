"""Ordinary CIX command for the integrated, explicitly bounded runtime."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import tempfile
import time

from . import __version__, engine


def _bounded_decode(data: bytes, max_output_bytes: int, memory_bytes: int) -> bytes:
    """Contain native-library allocations as well as Python output buffers."""
    previous = resource.getrlimit(resource.RLIMIT_AS)
    baseline = int(Path("/proc/self/statm").read_text().split()[0]) * os.sysconf("SC_PAGE_SIZE")
    limit = baseline + memory_bytes
    if previous[0] != resource.RLIM_INFINITY:
        limit = min(limit, previous[0])
    resource.setrlimit(resource.RLIMIT_AS, (limit, previous[1]))
    try:
        return engine.decode(data, max_output_bytes=max_output_bytes, memory_bytes=memory_bytes)
    except MemoryError as error:
        raise ValueError("decoder exceeded the declared allocation budget") from error
    finally:
        resource.setrlimit(resource.RLIMIT_AS, previous)


def memory(value: str) -> int:
    value = value.strip().upper()
    for suffix, multiplier in (("GIB", 1 << 30), ("MIB", 1 << 20), ("KIB", 1 << 10),
                               ("GB", 10**9), ("MB", 10**6), ("KB", 10**3), ("B", 1)):
        if value.endswith(suffix):
            return int(value[:-len(suffix)]) * multiplier
    return int(value)


def _atomic_write(path: Path, data: bytes, force: bool) -> None:
    path = path.absolute()
    with tempfile.NamedTemporaryFile(prefix="." + path.name + ".", dir=path.parent, delete=False) as out:
        temporary = Path(out.name)
        try:
            out.write(data)
            out.flush()
            os.fsync(out.fileno())
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    try:
        if force:
            os.replace(temporary, path)
        else:
            os.link(temporary, path)  # Exclusive commit without an overwrite race.
    finally:
        temporary.unlink(missing_ok=True)


def _native_stream(args: argparse.Namespace, profile: str) -> int:
    from .backends import _native_binary
    command = [str(_native_binary("uncix-native" if args.decompress else "cix-native")),
               "--memory", str(args.memory) + "B"]
    if args.decompress:
        command.append("-d")
    else:
        command += {"best": ["--best"], "fast": ["--fast"], "default": []}[profile]
        command += ["--threads", str(args.threads)]
    if args.stdout:
        command.append("-c")
    if args.output:
        command += ["-o", str(args.output)]
    if args.force:
        command.append("-f")
    if args.explain:
        command.append("--explain")
    command.append(args.input)
    if args.report:
        engine._save(args.report, {
            "schema": "cix-runtime-selection-v1", "status": "native-streaming-delegation",
            "reason": "non-seekable input or input exceeds bounded whole-input search",
            "specialist_coverage": "not evaluated on delegated streaming input",
            "command_profile": profile,
        })
    return subprocess.call(command)


def _argument_parser(program: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=program, description=
        "Lossless CIX compression with automatic content-derived models. "
        "This integrated candidate is awaiting full qualification.")
    profile = parser.add_mutually_exclusive_group()
    profile.add_argument("--best", action="store_true", help="complete generic and specialist archive search")
    profile.add_argument("--fast", action="store_true", help="native low-latency profile")
    parser.add_argument("-d", "--decompress", action="store_true")
    parser.add_argument("-c", "--stdout", action="store_true")
    parser.add_argument("-o", "--output", type=Path)
    parser.add_argument("-f", "--force", action="store_true")
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--memory", type=memory, default=engine.DEFAULT_MEMORY)
    parser.add_argument("--max-output", type=memory, default=engine.MAX_INPUT)
    parser.add_argument("--report", type=Path, help="complete candidate coverage and measured search report")
    parser.add_argument("--explain", action="store_true")
    parser.add_argument("--version", action="version", version="CIX " + __version__)
    parser.add_argument("input", nargs="?", default="-")
    return parser


def _validate_arguments(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    if args.stdout and args.output:
        parser.error("choose either standard output or an output file")
    if not 1 <= args.threads <= 4 or args.memory < (64 << 20) or args.max_output < 0:
        parser.error("invalid thread/memory/output bound")


def _profile(args: argparse.Namespace) -> str:
    if args.best:
        return "best"
    if args.fast:
        return "fast"
    return "default"


def _requires_native(args: argparse.Namespace, source: Path | None) -> bool:
    if not args.decompress and (source is None or not source.is_file() or source.stat().st_size > engine.MAX_INPUT):
        return True
    if args.decompress and source is not None and source.stat().st_size > engine.MAX_INPUT + (16 << 20):
        with source.open("rb") as stream:
            return stream.read(5) in {b"CIXG1", b"CIXG2", b"CIXZ1", b"CIXM6", b"CIXM5", b"CIXF1"}
    return False


def _read_input(parser: argparse.ArgumentParser, source: Path | None) -> bytes:
    if source is None:
        frame = sys.stdin.buffer.read(engine.MAX_INPUT + (16 << 20) + 1)
        if len(frame) > engine.MAX_INPUT + (16 << 20):
            parser.error("specialist archive input exceeds bounded reader; use a named file for native streaming archives")
        return frame
    if source.stat().st_size > engine.MAX_INPUT + (16 << 20):
        parser.error("archive exceeds bounded runtime reader")
    return source.read_bytes()


def _destination(parser: argparse.ArgumentParser, args: argparse.Namespace, source: Path | None) -> Path | None:
    destination = args.output
    if not args.stdout and destination is None:
        if source is None:
            args.stdout = True
        elif args.decompress:
            destination = source.with_suffix("") if source.suffix == ".cix" else Path(str(source) + ".out")
        else:
            destination = Path(str(source) + ".cix")
    if destination and source and destination.resolve() == source.resolve():
        parser.error("input and output must be different files")
    if destination and destination.exists() and not args.force:
        parser.error("output exists; use --force to replace it")
    return destination


def main(argv: list[str] | None = None) -> int:
    program = os.environ.get("CIX_RUNTIME_PROGRAM", "cix")
    parser = _argument_parser(program)
    args = parser.parse_args(argv)
    args.decompress = args.decompress or program in {"uncix", "cixcat"}
    args.stdout = args.stdout or program == "cixcat"
    _validate_arguments(parser, args)
    selected_profile = _profile(args)
    source = Path(args.input) if args.input != "-" else None
    if _requires_native(args, source):
        return _native_stream(args, selected_profile)
    data = _read_input(parser, source)
    destination = _destination(parser, args, source)
    started = time.perf_counter()
    if args.decompress:
        output = _bounded_decode(data, max_output_bytes=args.max_output, memory_bytes=args.memory)
        report = {"schema": "cix-runtime-decode-v1", "status": "completed",
                  "archive_bytes": len(data), "output_bytes": len(output),
                  "decode_wall_seconds": time.perf_counter()-started}
        if args.report:
            engine._save(args.report, report)
    else:
        output, report = engine.encode(data, profile=selected_profile, memory_bytes=args.memory,
                                       threads=args.threads, progress_path=args.report)
    if args.stdout:
        sys.stdout.buffer.write(output)
        sys.stdout.buffer.flush()
    elif destination:
        _atomic_write(destination, output, args.force)
    if args.explain:
        print(json.dumps(report, sort_keys=True), file=sys.stderr)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError) as error:
        print(f"cix: {error}", file=sys.stderr)
        raise SystemExit(1)
