#!/usr/bin/env python3
"""Exercise the bounded Rust CIXM6 selector end to end at every effort."""
from __future__ import annotations

import random
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "rust/cix-native/target/release"


def run(*args: object, data: bytes | None = None) -> subprocess.CompletedProcess:
    result = subprocess.run(
        [str(arg) for arg in args],
        input=data,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode:
        raise AssertionError(result.stderr.decode(errors="replace"))
    return result


def modes(archive: bytes) -> list[int]:
    pos = 5

    def varint() -> int:
        nonlocal pos
        value = shift = 0
        while True:
            byte = archive[pos]
            pos += 1
            value |= (byte & 127) << shift
            if byte < 128:
                return value
            shift += 7

    varint()  # declared history limit
    found = []
    while pos < len(archive):
        mode = archive[pos]
        pos += 1
        if mode == 255:
            break
        varint()  # source bytes
        size = varint()
        found.append(mode)
        pos += size
        if pos > len(archive):
            raise AssertionError("truncated selected CIXM6 payload")
    return found


def main() -> None:
    subprocess.run(
        ["cargo", "build", "--release", "--bins", "--manifest-path", str(ROOT / "rust/cix-native/Cargo.toml")],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    sys.path.insert(0, str(ROOT))
    from cix.multinomial import decompress

    rng = random.Random(613)
    cases = {
        "empty": b"",
        "tiny": b"six cix",
        "random": rng.randbytes(4096),
        "repetitive": (b"six-format-stream\0" * 256),
        "mixed": (bytes(range(64)) * 48) + (b"ABC" * 512),
        "repeated-blocks": (b"fixed independent frame\0" * 171)[:4096] * 2,
    }
    checked = 0
    selected_modes: set[int] = set()
    with tempfile.TemporaryDirectory(prefix="cixm6-selector-") as temp:
        source = Path(temp) / "source.bin"
        for level in range(1, 10):
            for label, data in cases.items():
                source.write_bytes(data)
                archive = run(
                    BIN / "cix",
                    f"-{level}",
                    "--format",
                    "cixm6",
                    "--block-size",
                    "4KiB",
                    "--memory",
                    "2MiB",
                    "-c",
                    source,
                ).stdout
                assert archive.startswith(b"CIXM6")
                assert decompress(archive) == data, (level, label, modes(archive))
                assert run(BIN / "uncix", "-c", "-", data=archive).stdout == data
                selected_modes.update(modes(archive))
                checked += 1
    assert selected_modes <= set(range(21))
    print(
        f"verified {checked} Rust CIXM6 archives across efforts 1–9 and six input classes; "
        f"Python and Rust restored every input; selected modes {sorted(selected_modes)}"
    )


if __name__ == "__main__":
    main()
