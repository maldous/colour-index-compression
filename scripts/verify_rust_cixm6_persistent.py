#!/usr/bin/env python3
"""Verify frozen Python CIXM5/CIXM6 mode 13 persistent-model parity."""
from __future__ import annotations

import argparse
import os
import random
import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CRATE = ROOT / "rust/cix-native"
BIN = Path(os.environ.get("CIX_NATIVE_BIN", CRATE / "target/release"))
HISTORY_LIMIT = 1 << 20


def run(*args: str, data: bytes = b"", ok: bool = True) -> subprocess.CompletedProcess[bytes]:
    result = subprocess.run(args, input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if ok and result.returncode:
        raise AssertionError(f"{args}: {result.stderr.decode(errors='replace')}")
    if not ok and result.returncode == 0:
        raise AssertionError(f"unexpected success: {args}")
    return result


def frame(mode: int, source: bytes, payload: bytes, vencode) -> bytes:
    return bytes((mode,)) + vencode(len(source)) + vencode(len(payload)) + payload


def fixtures():
    sys.path.insert(0, str(ROOT))
    from cix.multinomial import vencode
    from cix.stateful import make_persistent_states

    rng = random.Random(13_013)
    states = make_persistent_states()
    history = bytearray()
    blocks: list[tuple[int, bytes, bytes]] = []

    def append_raw(data: bytes) -> None:
        blocks.append((0, data, data))
        observe(data)

    def append_persistent(model_id: int, data: bytes) -> None:
        prefix = bytes(history)
        payload = bytes((model_id,)) + states[model_id].encode(data, prefix)
        blocks.append((13, data, payload))
        observe(data)

    def observe(data: bytes) -> None:
        prefix = bytes(history)
        for state in states:
            state.observe(data, prefix)
        history.extend(data)
        if len(history) > HISTORY_LIMIT:
            del history[:-HISTORY_LIMIT]

    append_raw((b"persistent seed alphabet 0123456789\n" * 180) + bytes(range(256)))
    append_persistent(0, rng.randbytes(3072) + b"order zero learned tail" * 40)
    append_raw((b"ABRACADABRA\0" * 400) + bytes(range(64)) * 8)
    append_persistent(1, (b"ABRACADABRA context learns transitions\n" * 160))

    # Cross STATE_LIMIT and exercise the reference's single end-of-block halving.
    append_raw((b"rescale-state-" + bytes(range(32))) * 620)
    order2 = bytearray()
    for i in range(5500):
        order2.append((i * 17 + (i // 7) * 29 + order2[-1] if order2 else i) & 255)
    append_persistent(2, bytes(order2))
    append_persistent(0, b"post-rescale order zero check\n" * 190)

    source = b"".join(data for _, data, _ in blocks)
    body = b"".join(frame(mode, data, payload, vencode) for mode, data, payload in blocks)
    footer = bytes((255,)) + vencode(len(source)) + struct.pack("<I", zlib.crc32(source))
    archive = b"CIXM6" + vencode(HISTORY_LIMIT) + body + footer

    tape = bytearray(struct.pack("<I", HISTORY_LIMIT))
    for mode, data, payload in blocks:
        if mode == 0:
            tape += bytes((0,)) + struct.pack("<I", len(data)) + data
        else:
            tape += bytes((1,)) + struct.pack("<II", len(data), len(payload)) + payload
    tape.append(255)
    return archive, source, bytes(tape), blocks


def verify_module(tape: bytes, expected: bytes) -> None:
    rank = (CRATE / "src/rank.rs").as_posix()
    stateful = (CRATE / "src/stateful.rs").as_posix()
    source = f'''\
#[path = "{rank}"] mod rank;
#[path = "{stateful}"] mod stateful;
use std::io::{{Read, Write}};

fn u32le(data: &[u8], pos: &mut usize) -> usize {{
    let end = *pos + 4;
    let value = u32::from_le_bytes(data[*pos..end].try_into().unwrap()) as usize;
    *pos = end;
    value
}}

fn main() {{
    let mut tape = Vec::new();
    std::io::stdin().read_to_end(&mut tape).unwrap();
    let mut pos = 0usize;
    let history_limit = u32le(&tape, &mut pos);
    let mut history = Vec::new();
    let mut output = Vec::new();
    let mut states = stateful::PersistentAdaptiveStates::new();
    loop {{
        let tag = tape[pos]; pos += 1;
        if tag == 255 {{ break; }}
        let n = u32le(&tape, &mut pos);
        let block = if tag == 0 {{
            let value = tape[pos..pos+n].to_vec(); pos += n; value
        }} else {{
            let payload_n = u32le(&tape, &mut pos);
            let payload = &tape[pos..pos+payload_n]; pos += payload_n;
            states.decode(payload, n, &history, stateful::WORKING_MEMORY_BOUND).unwrap()
        }};
        states.observe(&block, &history).unwrap();
        output.extend_from_slice(&block);
        history.extend_from_slice(&block);
        if history.len() > history_limit {{
            history.drain(..history.len()-history_limit);
        }}
    }}
    assert!(states.decode(&[], 1, &history, stateful::WORKING_MEMORY_BOUND).is_err());
    assert!(states.decode(&[3], 1, &history, stateful::WORKING_MEMORY_BOUND).is_err());
    assert!(states.decode(&[0, 0], 1, &history, 0).is_err());
    std::io::stdout().write_all(&output).unwrap();
}}
'''
    with tempfile.TemporaryDirectory(prefix="cix-mode13-module-") as td:
        temp = Path(td)
        (temp / "src").mkdir()
        (temp / "Cargo.toml").write_text(
            '[package]\nname="cix-mode13-check"\nversion="0.0.0"\nedition="2021"\n'
            '[dependencies]\nnum-bigint="0.4"\nnum-traits="0.2"\n'
        )
        (temp / "src/main.rs").write_text(source)
        env = dict(os.environ)
        env["CARGO_BUILD_JOBS"] = "2"
        result = subprocess.run(
            ["cargo", "run", "--quiet", "--release", "--offline", "--manifest-path", str(temp / "Cargo.toml")],
            input=tape,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )
        if result.returncode:
            raise AssertionError(result.stderr.decode(errors="replace"))
        assert result.stdout == expected, "isolated Rust mode 13 decoder differs from Python"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--module-only", action="store_true")
    args = parser.parse_args()
    archive, expected, tape, blocks = fixtures()

    from cix.multinomial import decompress, vencode

    assert decompress(archive) == expected
    verify_module(tape, expected)

    if not args.module_only:
        env = dict(os.environ)
        env["CARGO_BUILD_JOBS"] = "4"
        subprocess.run(
            ["cargo", "build", "--release", "--manifest-path", str(CRATE / "Cargo.toml")],
            check=True,
            env=env,
        )
        uncix = str(BIN / "uncix")
        for magic in (b"CIXM6", b"CIXM5"):
            candidate = magic + archive[5:]
            assert run(uncix, "--memory", "16MiB", "-c", "-", data=candidate).stdout == expected

        missing_id = b"CIXM6" + vencode(HISTORY_LIMIT) + frame(13, b"x", b"", vencode)
        run(uncix, "--memory", "16MiB", "-c", "-", data=missing_id, ok=False)
        unknown_id = b"CIXM6" + vencode(HISTORY_LIMIT) + frame(13, b"x", b"\x03\x01", vencode)
        run(uncix, "--memory", "16MiB", "-c", "-", data=unknown_id, ok=False)
        mode13_payload = next(payload for mode, _, payload in blocks if mode == 13)
        corrupt = b"CIXM6" + vencode(HISTORY_LIMIT) + frame(13, b"x", mode13_payload[:-1], vencode)
        run(uncix, "--memory", "16MiB", "-c", "-", data=corrupt, ok=False)
        run(uncix, "--memory", "16MiB", "-c", "-", data=archive[:-3], ok=False)

    print("verified CIXM5/CIXM6 mode 13 persistent models 0/1/2 against frozen Python")


if __name__ == "__main__":
    main()
