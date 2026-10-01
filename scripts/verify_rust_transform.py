#!/usr/bin/env python3
"""Verify every frozen CIXM6 mode-5 transform against its Rust decoder."""
from __future__ import annotations

import os
import random
import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = "80b95427725ecf59d626b2982d50f6349abd56e1"


def build_archive(payload: bytes, source: bytes) -> bytes:
    from cix.multinomial import vencode

    return (
        b"CIXM6"
        + vencode(1 << 20)
        + bytes((5,))
        + vencode(len(source))
        + vencode(len(payload))
        + payload
        + bytes((255,))
        + vencode(len(source))
        + struct.pack("<I", zlib.crc32(source))
    )


def build_harness(directory: Path) -> Path:
    crate = directory / "transform-fixture"
    src = crate / "src"
    src.mkdir(parents=True)
    rank = (ROOT / "rust/cix-native/src/rank.rs").as_posix()
    transform = (ROOT / "rust/cix-native/src/transform.rs").as_posix()
    (crate / "Cargo.toml").write_text(
        """[package]
name = "transform-fixture"
version = "0.0.0"
edition = "2021"

[dependencies]
crc32fast = "1"
num-bigint = "0.4"
num-traits = "0.2"
""",
        encoding="utf-8",
    )
    (src / "main.rs").write_text(
        f'''use std::io::{{self, Read, Write}};
#[path = "{rank}"] mod rank;
#[path = "{transform}"] mod transform;

fn varint(data: &[u8], pos: &mut usize) -> Result<usize, String> {{
    let mut value = 0usize;
    for shift in (0..35).step_by(7) {{
        let byte = *data.get(*pos).ok_or("truncated varint")?;
        *pos += 1;
        value |= ((byte & 127) as usize).checked_shl(shift).ok_or("varint overflow")?;
        if byte < 128 {{ return Ok(value); }}
    }}
    Err("oversized varint".into())
}}

fn run(data: &[u8]) -> Result<Vec<u8>, String> {{
    if data.get(..5) != Some(b"CIXM6") {{ return Err("bad magic".into()); }}
    let mut pos = 5;
    let _history = varint(data, &mut pos)?;
    if data.get(pos) != Some(&5) {{ return Err("not a mode-5 frame".into()); }}
    pos += 1;
    let source_length = varint(data, &mut pos)?;
    let payload_length = varint(data, &mut pos)?;
    let end = pos.checked_add(payload_length).ok_or("payload overflow")?;
    let payload = data.get(pos..end).ok_or("truncated payload")?;
    pos = end;
    if data.get(pos) != Some(&255) {{ return Err("missing footer".into()); }}
    pos += 1;
    if varint(data, &mut pos)? != source_length {{ return Err("length mismatch".into()); }}
    let crc_end = pos.checked_add(4).ok_or("CRC overflow")?;
    let crc: [u8; 4] = data.get(pos..crc_end).ok_or("truncated CRC")?.try_into().unwrap();
    if crc_end != data.len() {{ return Err("trailing archive bytes".into()); }}
    let out = transform::decode(payload, source_length)?;
    if crc32fast::hash(&out) != u32::from_le_bytes(crc) {{ return Err("CRC mismatch".into()); }}
    Ok(out)
}}

fn main() {{
    let mut data = Vec::new();
    io::stdin().read_to_end(&mut data).unwrap();
    match run(&data) {{
        Ok(out) => io::stdout().write_all(&out).unwrap(),
        Err(error) => {{ eprintln!("{{error}}"); std::process::exit(1); }}
    }}
}}
''',
        encoding="utf-8",
    )
    subprocess.run(
        [
            "cargo",
            "build",
            "--quiet",
            "--release",
            "--manifest-path",
            str(crate / "Cargo.toml"),
        ],
        check=True,
        env={**os.environ, "CARGO_BUILD_JOBS": "2"},
    )
    return crate / "target/release/transform-fixture"


def invoke(
    binary: Path, archive: bytes, *, ok: bool = True, error: str | None = None
) -> bytes:
    result = subprocess.run(
        [str(binary)], input=archive, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    if ok and result.returncode:
        raise AssertionError(result.stderr.decode(errors="replace"))
    if not ok and not result.returncode:
        raise AssertionError("malformed transform fixture decoded successfully")
    if error is not None and error not in result.stderr.decode(errors="replace"):
        raise AssertionError(
            f"expected {error!r}, got {result.stderr.decode(errors='replace')!r}"
        )
    return result.stdout


def main() -> None:
    subprocess.run(
        [
            "git",
            "diff",
            "--exit-code",
            REFERENCE,
            "--",
            "cix/transforms.py",
            "cix/multinomial.py",
        ],
        cwd=ROOT,
        check=True,
    )
    sys.path.insert(0, str(ROOT))
    from cix.multinomial import encode_type_class_known_n
    from cix.multinomial import vdecode
    from cix.transforms import SPECS, apply_transform

    rng = random.Random(505)
    structured = b"".join(
        struct.pack("<Q", (index * index * 17 - index * 91) & ((1 << 64) - 1))
        for index in range(97)
    ) + b"tail!"
    repeated = (b"four byte key/sequence/four byte key/sequence/" * 40) + bytes(
        rng.randrange(256) for _ in range(211)
    )

    with tempfile.TemporaryDirectory(prefix="cix-transform-fixture-") as temp:
        binary = build_harness(Path(temp))
        archives = []
        for spec in SPECS:
            source = repeated if spec.id == 33 else structured
            transformed = apply_transform(source, spec)
            payload = bytes((1, spec.id)) + encode_type_class_known_n(transformed)
            archive = build_archive(payload, source)
            assert invoke(binary, archive) == source, spec
            archives.append(archive)

        malformed = bytearray(archives[0])
        _, payload_start = vdecode(archives[0], 5)
        assert archives[0][payload_start] == 5
        _, payload_start = vdecode(archives[0], payload_start + 1)
        _, payload_start = vdecode(archives[0], payload_start)
        malformed[payload_start] = 2
        invoke(
            binary,
            bytes(malformed),
            ok=False,
            error="unknown transform block version",
        )

        malformed = bytearray(archives[0])
        malformed[payload_start + 1] = 32
        invoke(binary, bytes(malformed), ok=False, error="unknown transform ID")

        invoke(binary, archives[0][:-1], ok=False)

    print(
        f"verified {len(SPECS)} Python-generated CIXM6 mode-5 transform frames "
        "and malformed version, ID, and truncation rejection"
    )


if __name__ == "__main__":
    main()
