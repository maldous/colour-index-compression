#!/usr/bin/env python3
"""Generate the deterministic body-line fixture used by the first body screen."""
from __future__ import annotations
import argparse, hashlib
from pathlib import Path

def generate() -> bytes:
    out = bytearray(b"<mediawiki>\n")
    for page in range(160):
        out.extend(f"<page><title>P{page}</title><text>\n".encode())
        for row in range(3):
            out.extend(f"{{{{Infobox|name=[[Entity {page % 9}]]|url=https://example.org/{page % 7}|value={page * 17 + row}}}}} repeated fixed descriptive words for line eligibility\n".encode())
        out.extend(b"</text></page>\n")
    out.extend(b"<page><text>raw incomplete boundary")
    return bytes(out)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("output", type=Path)
    a = p.parse_args()
    data=generate(); a.output.write_bytes(data); print(hashlib.sha256(data).hexdigest(), len(data))
if __name__ == "__main__": main()
