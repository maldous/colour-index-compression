#!/usr/bin/env python3
"""Cross-check the native CIXM6 mode-5 encoder against the frozen Python reference."""
from __future__ import annotations

import os
import random
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = "80b95427725ecf59d626b2982d50f6349abd56e1"


def build_harness(directory: Path) -> Path:
    crate = directory / "transform-encode-fixture"
    src = crate / "src"
    src.mkdir(parents=True)
    rank = (ROOT / "rust/cix-native/src/rank.rs").as_posix()
    transform = (ROOT / "rust/cix-native/src/transform.rs").as_posix()
    (crate / "Cargo.toml").write_text(
        """[package]
name = "transform-encode-fixture"
version = "0.0.0"
edition = "2021"

[dependencies]
num-bigint = "0.4"
num-traits = "0.2"
""",
        encoding="utf-8",
    )
    (src / "main.rs").write_text(
        f'''use std::io::{{self, Read, Write}};
#[path = "{rank}"] mod rank;
#[path = "{transform}"] mod transform;

fn main() {{
    let args: Vec<String> = std::env::args().collect();
    let mut input = Vec::new();
    io::stdin().read_to_end(&mut input).unwrap();
    let encoded = match args.get(1).map(String::as_str) {{
        Some("id") => {{
            let id: u8 = args[2].parse().unwrap();
            transform::encode_id(&input, id).unwrap()
        }}
        Some("auto") => {{
            let beam: usize = args[2].parse().unwrap();
            let (payload, name) = transform::encode(&input, beam).unwrap();
            eprintln!("{{name}}");
            payload
        }}
        _ => panic!("expected id ID or auto BEAM"),
    }};
    io::stdout().write_all(&encoded).unwrap();
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
    return crate / "target/release/transform-encode-fixture"


def run_harness(binary: Path, source: bytes, kind: str, value: int) -> tuple[bytes, str]:
    result = subprocess.run(
        [str(binary), kind, str(value)],
        input=source,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode:
        raise AssertionError(result.stderr.decode(errors="replace"))
    return result.stdout, result.stderr.decode().strip()


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
    from cix.transforms import (
        SPECS,
        apply_transform,
        decode_transform_block,
        encode_transform_block,
    )

    rng = random.Random(0xC105)
    inputs = [
        bytes(range(256)) * 2 + b"odd-tail!",
        b"ABCD0123/ABCD0123/" * 37 + bytes(range(131)),
        b"".join(
            struct.pack("<Q", (index**3 - 97 * index) & ((1 << 64) - 1))
            for index in range(97)
        )
        + b"tail!",
        bytes(rng.randrange(256) for _ in range(2057)),
    ]
    with tempfile.TemporaryDirectory(prefix="cix-transform-encode-") as temp:
        binary = build_harness(Path(temp))
        for case, source in enumerate(inputs):
            for spec in SPECS:
                expected = bytes((1, spec.id)) + encode_type_class_known_n(
                    apply_transform(source, spec)
                )
                actual, diagnostic = run_harness(binary, source, "id", spec.id)
                assert not diagnostic
                assert actual == expected, (case, spec.id, spec.name)
                assert decode_transform_block(actual, source_length=len(source)) == source

            for beam in (1, 6, 32):
                expected, expected_name = encode_transform_block(source, beam=beam)
                actual, actual_name = run_harness(binary, source, "auto", beam)
                assert (actual, actual_name) == (expected, expected_name), (
                    case,
                    beam,
                    actual_name,
                    expected_name,
                )
                assert decode_transform_block(actual, source_length=len(source)) == source
    print(
        f"verified {len(inputs) * len(SPECS)} canonical explicit mode-5 encodings, "
        f"{len(inputs) * 3} canonical beam selections, and Python decoding "
        f"against frozen reference {REFERENCE}"
    )


if __name__ == "__main__":
    main()
