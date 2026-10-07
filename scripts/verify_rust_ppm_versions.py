#!/usr/bin/env python3
"""Verify Rust PPM payload decoding against the frozen Python reference."""
from __future__ import annotations

import json
import os
import random
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = "80b95427725ecf59d626b2982d50f6349abd56e1"


def _assert_frozen_python() -> None:
    for relative in ("cix/ppm.py", "cix/multinomial.py"):
        frozen = subprocess.run(
            ["git", "show", f"{REFERENCE}:{relative}"],
            cwd=ROOT,
            check=True,
            stdout=subprocess.PIPE,
        ).stdout
        if (ROOT / relative).read_bytes() != frozen:
            raise AssertionError(f"{relative} differs from frozen reference {REFERENCE}")


def _fixtures() -> list[tuple[bytes, bytes, bytes]]:
    from cix.ppm import decode_ppm, encode_ppm

    rng = random.Random(29)
    data = (
        rng.randbytes(128)
        + b"abacabacadabra|prediction by partial matching|" * 18
        + bytes(range(256))
    )
    history = b"dabra\0shared recurring PPM history|" * 96
    fixtures: list[tuple[bytes, bytes, bytes]] = []

    # Version 2 has the same bitstream law as v3 but starts with empty tables
    # and only seeds the history register. With no prefix, replacing the v3
    # version byte produces a canonical legacy-v2 fixture.
    for order in (0, 1, 4, 8):
        for method in range(4):
            payload = encode_ppm(
                data,
                max_order=order,
                escape_method=method,
                update_exclusion=False,
                secondary_escape=False,
            )
            payload = bytes((2,)) + payload[1:]
            fixtures.append((b"", data, payload))

    for version, update_exclusion in ((3, False), (4, True)):
        for order in (0, 4, 8):
            for method in range(4):
                payload = encode_ppm(
                    data,
                    max_order=order,
                    prefix_history=history,
                    escape_method=method,
                    update_exclusion=update_exclusion,
                    secondary_escape=False,
                )
                assert payload[0] == version
                fixtures.append((history, data, payload))

    for update_exclusion in (False, True):
        for order in (0, 1, 4, 8):
            payload = encode_ppm(
                data,
                max_order=order,
                prefix_history=history,
                update_exclusion=update_exclusion,
                secondary_escape=True,
            )
            assert payload[:1] == b"\x05"
            fixtures.append((history, data, payload))

    # Drive SEE beyond its 256-event rescale threshold.
    see_data = b"\0" * 520 + rng.randbytes(180)
    see_payload = encode_ppm(
        see_data,
        max_order=4,
        prefix_history=b"\0" * 800,
        update_exclusion=True,
        secondary_escape=True,
    )
    fixtures.append((b"\0" * 800, see_data, see_payload))

    # Only the final 65,536 history bytes may train a fresh block model.
    bounded_history = b"discarded-prefix|" * 600 + bytes(range(256)) * 256
    bounded_data = bytes(range(64)) * 4
    bounded_payload = encode_ppm(
        bounded_data,
        max_order=8,
        prefix_history=bounded_history,
        escape_method=2,
        update_exclusion=True,
        secondary_escape=False,
    )
    fixtures.append((bounded_history, bounded_data, bounded_payload))

    for prefix, source, payload in fixtures:
        assert decode_ppm(
            payload,
            source_length=len(source),
            prefix_history=prefix,
        ) == source
    return fixtures


def _write_fixture_file(path: Path, fixtures: list[tuple[bytes, bytes, bytes]]) -> None:
    out = bytearray(b"CIXPPM1\0")
    out += struct.pack("<I", len(fixtures))
    for prefix, source, payload in fixtures:
        out += struct.pack("<III", len(prefix), len(source), len(payload))
        out += prefix
        out += source
        out += payload
    path.write_bytes(out)


def main() -> None:
    _assert_frozen_python()
    sys.path.insert(0, str(ROOT))
    fixtures = _fixtures()
    versions = {payload[0] for _, _, payload in fixtures}
    assert versions == {2, 3, 4, 5}

    with tempfile.TemporaryDirectory(prefix="cix-rust-ppm-") as directory:
        harness = Path(directory)
        fixture_path = harness / "fixtures.bin"
        _write_fixture_file(fixture_path, fixtures)
        source_root = ROOT / "rust/cix-native/src"
        (harness / "src").mkdir()
        (harness / "Cargo.toml").write_text(
            "[package]\nname = \"cix-ppm-verify\"\nversion = \"0.0.0\"\n"
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
    use std::fs;

    fn u32_at(data: &[u8], pos: &mut usize) -> usize {
        let end = *pos + 4;
        let value = u32::from_le_bytes(data[*pos..end].try_into().unwrap()) as usize;
        *pos = end;
        value
    }

    #[test]
    fn frozen_python_payloads_decode_exactly() {
        let data = fs::read(std::env::var("CIX_PPM_FIXTURES").unwrap()).unwrap();
        assert_eq!(&data[..8], b"CIXPPM1\0");
        let mut pos = 8;
        let count = u32_at(&data, &mut pos);
        for _ in 0..count {
            let prefix_len = u32_at(&data, &mut pos);
            let source_len = u32_at(&data, &mut pos);
            let payload_len = u32_at(&data, &mut pos);
            let prefix = &data[pos..pos + prefix_len];
            pos += prefix_len;
            let source = &data[pos..pos + source_len];
            pos += source_len;
            let payload = &data[pos..pos + payload_len];
            pos += payload_len;
            assert_eq!(
                ppm::decode_with_history(payload, source_len, prefix).unwrap(),
                source
            );
        }
        assert_eq!(pos, data.len());
    }

    #[test]
    fn malformed_headers_are_rejected() {
        let invalid: &[&[u8]] = &[
            b"",
            &[5, 1],
            &[6, 0, 0, 0],
            &[4, 9, 0, 0],
            &[4, 1, 4, 0],
            &[5, 1, 2, 0],
            &[3, 1, 0, 0, 0],
            &[3, 1, 0, 8],
            &[3, 1, 0, 0x80],
            &[3, 1, 0, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80,
              0x80, 0x80, 0x80, 0x80, 0x00],
        ];
        for payload in invalid {
            assert!(ppm::decode(payload, 0).is_err(), "accepted {payload:?}");
        }
    }
}
''',
            encoding="utf-8",
        )
        env = dict(os.environ, CIX_PPM_FIXTURES=str(fixture_path))
        subprocess.run(
            [
                "cargo", "test", "--release", "--lib", "-j", "2",
                "--manifest-path", str(harness / "Cargo.toml"),
            ],
            cwd=harness,
            env=env,
            check=True,
        )

    print(
        f"verified {len(fixtures)} frozen Python PPM payloads across versions 2-5; "
        "escape methods 0-3, update exclusion, SEE rescaling, orders 0-8, "
        "warm prefix history, the 65,536-byte training bound, and malformed headers"
    )


if __name__ == "__main__":
    main()
