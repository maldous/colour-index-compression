#!/usr/bin/env python3
"""Cross-check Rust CIXM6 mode 13 encoding against the frozen Python coder."""
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
CRATE = ROOT / "rust/cix-native"
UNCIX = Path(os.environ.get("CIX_NATIVE_BIN", CRATE / "target/release")) / "uncix"
HISTORY_LIMIT = 4096
WORKING_MEMORY = 3 * 1024 * 1024


def u32(value: int) -> bytes:
    return struct.pack("<I", value)


def operations() -> list[tuple[str, int | None, bytes]]:
    """Mix selected blocks with raw and non-mode-13 observations."""
    rng = random.Random(130_013)
    order2 = bytearray()
    for i in range(5500):
        order2.append((i * 17 + (i // 7) * 29 + order2[-1] if order2 else i) & 255)
    return [
        ("raw", None, (b"persistent seed alphabet 0123456789\n" * 180) + bytes(range(256))),
        ("encode", 0, rng.randbytes(3072) + b"order zero learned tail" * 40),
        ("other", None, b"R" * 2800 + b"U" * 1700 + b"N" * 900),
        ("encode", 1, b"ABRACADABRA context learns transitions\n" * 160),
        ("other", None, (b"rescale-state-" + bytes(range(32))) * 620),
        ("encode", 2, bytes(order2)),
        ("best", None, (b"best model selection follows prior observations\n" * 150)),
        ("encode", 0, b"post-rescale order zero check\n" * 190),
    ]


def make_tape(ops: list[tuple[str, int | None, bytes]]) -> bytes:
    tape = bytearray(u32(HISTORY_LIMIT))
    for kind, model_id, data in ops:
        tag = {"raw": 0, "other": 1, "encode": 2, "best": 3}[kind]
        tape.append(tag)
        if kind == "encode":
            assert model_id is not None
            tape.append(model_id)
        tape += u32(len(data))
        tape += data
    tape.append(255)
    return bytes(tape)


def rust_harness(tape: bytes) -> bytes:
    rank = (CRATE / "src/rank.rs").as_posix()
    stateful = (CRATE / "src/stateful.rs").as_posix()
    source = f'''\
#[path = "{rank}"] mod rank;
#[path = "{stateful}"] mod stateful;
use std::io::{{Read, Write}};

fn take_u32(data: &[u8], pos: &mut usize) -> usize {{
    let end = *pos + 4;
    let value = u32::from_le_bytes(data[*pos..end].try_into().unwrap()) as usize;
    *pos = end;
    value
}}

fn retain(history: &mut Vec<u8>, data: &[u8], limit: usize) {{
    history.extend_from_slice(data);
    if history.len() > limit {{ history.drain(..history.len() - limit); }}
}}

fn main() {{
    let mut tape = Vec::new();
    std::io::stdin().read_to_end(&mut tape).unwrap();
    let mut pos = 0usize;
    let history_limit = take_u32(&tape, &mut pos);
    let mut encode_history = Vec::new();
    let mut decode_history = Vec::new();
    let mut encoder = stateful::PersistentAdaptiveStates::new();
    let mut decoder = stateful::PersistentAdaptiveStates::new();
    let mut records = Vec::new();
    loop {{
        let tag = tape[pos]; pos += 1;
        if tag == 255 {{ break; }}
        let requested = if tag == 2 {{ let value = tape[pos] as usize; pos += 1; Some(value) }} else {{ None }};
        let n = take_u32(&tape, &mut pos);
        let data = &tape[pos..pos+n]; pos += n;
        if tag >= 2 {{
            let (model_id, payload) = match requested {{
                Some(model_id) => (model_id, encoder.encode(model_id, data, &encode_history, {WORKING_MEMORY}).unwrap()),
                None => encoder.encode_best(data, &encode_history, {WORKING_MEMORY}).unwrap(),
            }};
            assert_eq!(encoder.model_spec(model_id), Some(match model_id {{ 0 => (0, 8), 1 => (1, 8), 2 => (2, 10), _ => unreachable!() }}));
            let estimate = encoder.estimate_bits(model_id, data, &encode_history, {WORKING_MEMORY}).unwrap();
            let restored = decoder.decode(&payload, data.len(), &decode_history, {WORKING_MEMORY}).unwrap();
            assert_eq!(restored, data);
            records.push(tag);
            records.push(model_id as u8);
            records.extend_from_slice(&estimate.to_le_bytes());
            records.extend_from_slice(&(payload.len() as u32).to_le_bytes());
            records.extend_from_slice(&payload);
        }}
        encoder.observe(data, &encode_history).unwrap();
        decoder.observe(data, &decode_history).unwrap();
        retain(&mut encode_history, data, history_limit);
        retain(&mut decode_history, data, history_limit);
    }}
    assert!(encoder.encode(stateful::MODEL_COUNT, b"x", &encode_history, {WORKING_MEMORY}).is_err());
    assert!(encoder.estimate_bits(stateful::MODEL_COUNT, b"x", &encode_history, {WORKING_MEMORY}).is_err());
    assert!(encoder.encode(2, b"x", &encode_history, 0).is_err());
    std::io::stdout().write_all(&records).unwrap();
}}
'''
    with tempfile.TemporaryDirectory(prefix="cix-mode13-encode-") as td:
        temp = Path(td)
        (temp / "src").mkdir()
        (temp / "Cargo.toml").write_text(
            '[package]\nname="cix-mode13-encode-check"\nversion="0.0.0"\nedition="2021"\n'
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
        return result.stdout


def retain(history: bytearray, data: bytes) -> None:
    history += data
    if len(history) > HISTORY_LIMIT:
        del history[:-HISTORY_LIMIT]


def frame(mode: int, data: bytes, payload: bytes, vencode) -> bytes:
    return bytes((mode,)) + vencode(len(data)) + vencode(len(payload)) + payload


def main() -> None:
    sys.path.insert(0, str(ROOT))
    from cix.multinomial import decompress, vencode
    from cix.runs import encode_run_block
    from cix.stateful import make_persistent_states

    ops = operations()
    records = rust_harness(make_tape(ops))
    pos = 0
    states = make_persistent_states()
    decode_states = make_persistent_states()
    history = bytearray()
    decode_history = bytearray()
    archive_body = bytearray()
    source = bytearray()
    encoded_count = 0

    for kind, requested, data in ops:
        if kind in ("encode", "best"):
            tag = records[pos]
            model_id = records[pos + 1]
            estimate = struct.unpack_from("<d", records, pos + 2)[0]
            payload_len = struct.unpack_from("<I", records, pos + 10)[0]
            payload = records[pos + 14 : pos + 14 + payload_len]
            pos += 14 + payload_len
            assert tag == (2 if kind == "encode" else 3)

            candidates = [bytes((i,)) + state.encode(data, bytes(history)) for i, state in enumerate(states)]
            expected_id = requested if requested is not None else min(range(len(candidates)), key=lambda i: len(candidates[i]))
            assert model_id == expected_id, "Rust persistent model selection differs from Python"
            assert payload == candidates[model_id], "Rust persistent arithmetic bytes differ from Python"
            expected_estimate = states[model_id].estimate_bits(data, bytes(history))
            assert abs(estimate - expected_estimate) <= 1e-9 * max(1.0, expected_estimate)
            restored = decode_states[model_id].decode(payload[1:], len(data), bytes(decode_history))
            assert restored == data, "Python could not decode Rust mode 13 payload"
            archive_body += frame(13, data, payload, vencode)
            encoded_count += 1
        elif kind == "raw":
            archive_body += frame(0, data, data, vencode)
        else:
            run_payload, _ = encode_run_block(data)
            archive_body += frame(12, data, run_payload, vencode)

        prefix = bytes(history)
        decode_prefix = bytes(decode_history)
        for state in states:
            state.observe(data, prefix)
        for state in decode_states:
            state.observe(data, decode_prefix)
        retain(history, data)
        retain(decode_history, data)
        source += data

    assert pos == len(records)
    archive = (
        b"CIXM6"
        + vencode(HISTORY_LIMIT)
        + bytes(archive_body)
        + bytes((255,))
        + vencode(len(source))
        + struct.pack("<I", zlib.crc32(source))
    )
    assert decompress(archive) == source, "Python archive decoder rejected Rust mode 13 payloads"
    if UNCIX.exists():
        result = subprocess.run(
            [str(UNCIX), "--memory", "16MiB", "-c", "-"],
            input=archive,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if result.returncode:
            raise AssertionError(result.stderr.decode(errors="replace"))
        assert result.stdout == source, "current Rust CLI decoder rejected Rust mode 13 payloads"

    print(
        f"verified {encoded_count} Rust mode 13 payloads: canonical Python bytes, "
        "models 0/1/2, best-model selection, raw/other observations, rescaling, and cross-decode"
    )


if __name__ == "__main__":
    main()
