#!/usr/bin/env python3
"""Verify the checked-in CIXI1 copies against their frozen qualification source."""
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SOURCE = ROOT / "docs/research/2026-10-04-automatic-specialised-models/qualification/dev-images-1"
FILES = {
    "jls.cix": "01-spatial-jls.cix",
    "jls-input.bin": "01-u8range.bin",
    "j2k.cix": "02-spatial-j2k.cix",
    "j2k-input.bin": "02-highbit.bin",
}
for local, source in FILES.items():
    copied = Path(__file__).with_name(local).read_bytes()
    original = (SOURCE / source).read_bytes()
    if copied != original:
        raise SystemExit(f"fixture mismatch: {local}")
    print(local, sha256(copied).hexdigest())
