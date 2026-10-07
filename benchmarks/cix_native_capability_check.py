#!/usr/bin/env python3
"""Native CLI restoration/malformed checks; no Python codec implementation."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary-dir", required=True, type=Path)
    parser.add_argument("--evidence", required=True, type=Path)
    args = parser.parse_args()
    binary = args.binary_dir.resolve()
    source = json.loads((binary / "native-release.json").read_text())
    fixtures = {"empty": b"", "tiny": b"CIX\0", "mixed": b"abcabcabc\0" * 128 + bytes(range(256)) * 4,
                "random": hashlib.shake_256(b"cix-frozen-capability-smoke-v1").digest(2048),
                "repetitive": b"x" * 4096}
    routes = ["raw", "runs", "composition", "lz", "predictor", "bwt", "stride", "phrases", "ppm", "mixture", "deflate"]
    rows = []
    for requested_id, route in enumerate(routes):
        selected = False
        for label, data in fixtures.items():
            enc = subprocess.run([str(binary / "cix"), "--best", "--stream", "--route", route,
                                  "--threads", "1", "-c", "-"], input=data, capture_output=True, check=True)
            dec = subprocess.run([str(binary / "uncix"), "-c", "-"], input=enc.stdout, capture_output=True, check=True)
            assert dec.stdout == data
            frame_ids = []
            pos = 13
            while enc.stdout[pos] != 255:
                frame_ids.append(enc.stdout[pos])
                pos += 41 + int.from_bytes(enc.stdout[pos + 5:pos + 9], "little")
            selected |= requested_id in frame_ids
            bad = bytearray(enc.stdout)
            bad[-1] ^= 1
            corrupt = subprocess.run([str(binary / "uncix"), "-t", "-"], input=bad, capture_output=True)
            trunc = subprocess.run([str(binary / "uncix"), "-t", "-"], input=enc.stdout[:-1], capture_output=True)
            assert corrupt.returncode and trunc.returncode
            rows.append({"requested_route": route, "actual_frame_route_ids": frame_ids, "fixture": label,
                         "input_bytes": len(data), "input_sha256": hashlib.sha256(data).hexdigest(),
                         "archive_bytes": len(enc.stdout), "archive_sha256": hashlib.sha256(enc.stdout).hexdigest(),
                         "fresh_decode_exact": True, "corrupt_exit": corrupt.returncode, "truncated_exit": trunc.returncode})
        assert selected, f"no fixture actually selected {route}; raw fallback cannot prove this mechanism"
    args.evidence.write_text(json.dumps({"source_revision": source["source_revision"],
        "encoder_sha256": hashlib.sha256((binary / "cix").read_bytes()).hexdigest(),
        "decoder_sha256": hashlib.sha256((binary / "uncix").read_bytes()).hexdigest(),
        "scope": "Correctness only. Every requested route wins at least one nonempty fixture. Empty/raw fallbacks are identified explicitly.",
        "rows": rows}, indent=2) + "\n")
    print(f"{len(rows)} fresh native round trips; {len(rows) * 2} corrupt/truncated rejections; all {len(routes)} route IDs actually selected")


if __name__ == "__main__":
    main()
