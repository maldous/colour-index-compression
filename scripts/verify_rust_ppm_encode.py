#!/usr/bin/env python3
"""Verify canonical Rust PPM v3-v5 encoding against the frozen Python reference."""
from __future__ import annotations

import json
import os
import random
import struct
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = "80b95427725ecf59d626b2982d50f6349abd56e1"
MAGIC = b"CIXPPE2\0"


def _assert_frozen_python() -> None:
    for relative in ("cix/ppm.py", "cix/multinomial.py"):
        frozen = subprocess.run(
            ["git", "show", f"{REFERENCE}:{relative}"],
            cwd=ROOT,
            check=True,
            stdout=subprocess.PIPE,
        ).stdout
        if (ROOT / relative).read_bytes() != frozen:
            raise AssertionError(
                f"{relative} differs from frozen reference {REFERENCE}"
            )


@dataclass(frozen=True)
class Fixture:
    kind: int  # 0 fixed escape; 1 SEE; 2 Python-compatible portfolio
    order: int
    method: int | None
    update: bool | None
    secondary: bool | None
    prefix: bytes
    source: bytes
    expected: bytes


def _fixtures() -> list[Fixture]:
    from cix.ppm import decode_ppm, encode_ppm

    rng = random.Random(0xC1_05)
    tiny = b"abracadabra|aba|"
    mixed = (
        rng.randbytes(96)
        + b"prediction by partial matching|abracadabra|" * 14
        + bytes(range(128))
    )
    history = b"shared recurring PPM history|abracadabra|" * 120
    datasets = ((b"", b""), (b"history|", tiny), (history, mixed))
    fixtures: list[Fixture] = []

    def add_fixed(
        prefix: bytes, source: bytes, order: int, method: int, update: bool
    ) -> None:
        expected = encode_ppm(
            source,
            max_order=order,
            prefix_history=prefix,
            escape_method=method,
            update_exclusion=update,
            secondary_escape=False,
        )
        fixtures.append(
            Fixture(0, order, method, update, False, prefix, source, expected)
        )

    def add_see(prefix: bytes, source: bytes, order: int, update: bool) -> None:
        expected = encode_ppm(
            source,
            max_order=order,
            prefix_history=prefix,
            update_exclusion=update,
            secondary_escape=True,
        )
        fixtures.append(
            Fixture(1, order, None, update, True, prefix, source, expected)
        )

    def add_best(
        prefix: bytes,
        source: bytes,
        order: int,
        method: int | None,
        update: bool | None,
        secondary: bool | None,
    ) -> None:
        expected = encode_ppm(
            source,
            max_order=order,
            prefix_history=prefix,
            escape_method=method,
            update_exclusion=update,
            secondary_escape=secondary,
        )
        fixtures.append(
            Fixture(2, order, method, update, secondary, prefix, source, expected)
        )

    for update in (False, True):
        add_fixed(b"", b"", 0, 0, update)
        add_fixed(b"", tiny, 3, 0, update)
        for method in range(4):
            add_fixed(b"history|", tiny, 3, method, update)
            for order in (0, 4, 8):
                add_fixed(history, mixed, order, method, update)

    for update in (False, True):
        add_see(b"history|", tiny, 3, update)
        for order in (0, 4, 8):
            add_see(history, mixed, order, update)

    # Exercise SEE rescaling and the frozen 65,536-byte history horizon.
    add_see(b"\0" * 800, b"\0" * 520 + rng.randbytes(160), 4, True)
    bounded_history = b"discarded|" * 800 + bytes(range(256)) * 256
    add_see(bounded_history, bytes(range(64)) * 3, 8, True)

    for prefix, source in datasets:
        order = 0 if not source else 4
        add_best(prefix, source, order, None, None, None)
        add_best(prefix, source, order, None, None, False)
        add_best(prefix, source, order, None, None, True)
    add_best(history, mixed, 5, 2, None, None)
    add_best(history, mixed, 5, 3, True, False)
    add_best(history, mixed, 5, None, False, True)

    for fixture in fixtures:
        assert decode_ppm(
            fixture.expected,
            source_length=len(fixture.source),
            prefix_history=fixture.prefix,
        ) == fixture.source
    return fixtures


def _option(value: bool | None) -> int:
    return 2 if value is None else int(value)


def _write_fixtures(path: Path, fixtures: list[Fixture]) -> None:
    out = bytearray(MAGIC)
    out += struct.pack("<I", len(fixtures))
    for fixture in fixtures:
        out += bytes(
            (
                fixture.kind,
                fixture.order,
                255 if fixture.method is None else fixture.method,
                _option(fixture.update),
                _option(fixture.secondary),
            )
        )
        out += struct.pack(
            "<III",
            len(fixture.prefix),
            len(fixture.source),
            len(fixture.expected),
        )
        out += fixture.prefix + fixture.source + fixture.expected
    path.write_bytes(out)


def _read_rust_payloads(path: Path, fixtures: list[Fixture]) -> None:
    from cix.ppm import decode_ppm

    data = path.read_bytes()
    assert data[:8] == MAGIC
    count = struct.unpack_from("<I", data, 8)[0]
    assert count == len(fixtures)
    pos = 12
    for fixture in fixtures:
        length = struct.unpack_from("<I", data, pos)[0]
        pos += 4
        payload = data[pos : pos + length]
        pos += length
        assert payload == fixture.expected
        assert decode_ppm(
            payload,
            source_length=len(fixture.source),
            prefix_history=fixture.prefix,
        ) == fixture.source
    assert pos == len(data)


def main() -> None:
    _assert_frozen_python()
    sys.path.insert(0, str(ROOT))
    fixtures = _fixtures()
    with tempfile.TemporaryDirectory(prefix="cix-rust-ppm-encode-") as directory:
        harness = Path(directory)
        fixture_path = harness / "fixtures.bin"
        output_path = harness / "rust-payloads.bin"
        _write_fixtures(fixture_path, fixtures)
        source_root = ROOT / "rust/cix-native/src"
        (harness / "src").mkdir()
        (harness / "Cargo.toml").write_text(
            "[package]\nname = \"cix-ppm-encode-verify\"\nversion = \"0.0.0\"\n"
            "edition = \"2021\"\n\n[dependencies]\nnum-bigint = \"0.4\"\n"
            "num-traits = \"0.2\"\n",
            encoding="utf-8",
        )
        (harness / "src/lib.rs").write_text(
            "#![allow(dead_code)]\n"
            f"#[path = {json.dumps(str(source_root / 'rank.rs'))}] mod rank;\n"
            f"#[path = {json.dumps(str(source_root / 'ppm.rs'))}] mod ppm;\n"
            r'''
#[cfg(test)]
mod tests {
    use super::ppm;
    use std::{env, fs};

    fn byte(data: &[u8], pos: &mut usize) -> u8 {
        let value = data[*pos];
        *pos += 1;
        value
    }

    fn u32_at(data: &[u8], pos: &mut usize) -> usize {
        let end = *pos + 4;
        let value = u32::from_le_bytes(data[*pos..end].try_into().unwrap()) as usize;
        *pos = end;
        value
    }

    fn bool_option(value: u8) -> Option<bool> {
        match value {
            0 => Some(false),
            1 => Some(true),
            2 => None,
            _ => panic!("invalid boolean option"),
        }
    }

    #[test]
    fn frozen_python_encodings_are_canonical() {
        let data = fs::read(env::var("CIX_PPM_ENCODE_FIXTURES").unwrap()).unwrap();
        assert_eq!(&data[..8], b"CIXPPE2\0");
        let mut pos = 8;
        let count = u32_at(&data, &mut pos);
        let mut emitted = Vec::from(&b"CIXPPE2\0"[..]);
        emitted.extend_from_slice(&(count as u32).to_le_bytes());
        for _ in 0..count {
            let kind = byte(&data, &mut pos);
            let order = byte(&data, &mut pos) as usize;
            let method_raw = byte(&data, &mut pos);
            let update = bool_option(byte(&data, &mut pos));
            let secondary = bool_option(byte(&data, &mut pos));
            let prefix_len = u32_at(&data, &mut pos);
            let source_len = u32_at(&data, &mut pos);
            let expected_len = u32_at(&data, &mut pos);
            let prefix = &data[pos..pos + prefix_len];
            pos += prefix_len;
            let source = &data[pos..pos + source_len];
            pos += source_len;
            let expected = &data[pos..pos + expected_len];
            pos += expected_len;
            let method = (method_raw != 255).then_some(method_raw);
            let payload = match kind {
                0 => ppm::encode_fixed(source, order, prefix, method.unwrap(), update.unwrap()),
                1 => ppm::encode_secondary(source, order, prefix, update.unwrap()),
                2 => ppm::encode_best(source, order, prefix, method, update, secondary),
                _ => panic!("invalid fixture kind"),
            }
            .unwrap();
            assert_eq!(payload, expected);
            assert_eq!(
                ppm::decode_with_history(&payload, source_len, prefix).unwrap(),
                source
            );
            if kind == 0 && prefix.is_empty() && method == Some(0) && update == Some(false) {
                assert_eq!(ppm::encode(source, order).unwrap(), payload);
            }
            emitted.extend_from_slice(&(payload.len() as u32).to_le_bytes());
            emitted.extend_from_slice(&payload);
        }
        assert_eq!(pos, data.len());
        fs::write(env::var("CIX_PPM_ENCODE_OUTPUT").unwrap(), emitted).unwrap();
    }

    #[test]
    fn invalid_encoder_options_are_rejected() {
        assert!(ppm::encode_fixed(b"x", 9, b"", 0, false).is_err());
        assert!(ppm::encode_fixed(b"x", 1, b"", 4, false).is_err());
        assert!(ppm::encode_secondary(b"x", 9, b"", false).is_err());
        assert!(ppm::encode_best(b"x", 1, b"", Some(4), None, None).is_err());
    }
}
''',
            encoding="utf-8",
        )
        env = dict(
            os.environ,
            CIX_PPM_ENCODE_FIXTURES=str(fixture_path),
            CIX_PPM_ENCODE_OUTPUT=str(output_path),
        )
        subprocess.run(
            [
                "cargo",
                "test",
                "--release",
                "--lib",
                "-j",
                "2",
                "--manifest-path",
                str(harness / "Cargo.toml"),
            ],
            cwd=harness,
            env=env,
            check=True,
        )
        _read_rust_payloads(output_path, fixtures)

    fixed = sum(fixture.kind == 0 for fixture in fixtures)
    see = sum(fixture.kind == 1 for fixture in fixtures)
    selected = sum(fixture.kind == 2 for fixture in fixtures)
    print(
        f"verified {fixed} fixed v3/v4 candidates, {see} v5 SEE candidates, and "
        f"{selected} exact portfolio selections against frozen Python {REFERENCE}; "
        "both decoders restored every Rust payload"
    )


if __name__ == "__main__":
    main()
