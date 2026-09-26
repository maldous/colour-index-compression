#!/usr/bin/env python3
"""Physical native CIX Canterbury baseline.

Uses only the current native CIX codec. Every member is decompressed and byte-compared
before its compressed size is accepted.
"""

import bz2
import gzip
import lzma
import tarfile
import time
import urllib.request
from pathlib import Path

from cix.multinomial import ContextModel, StreamConfig, StreamEncoder, decompress

CORPUS_URL = "https://corpus.canterbury.ac.nz/resources/cantrbry.tar.gz"
EXPECTED = {
    "alice29.txt": 152089, "asyoulik.txt": 125179, "cp.html": 24603,
    "fields.c": 11150, "grammar.lsp": 3721, "kennedy.xls": 1029744,
    "lcet10.txt": 426754, "plrabn12.txt": 481861, "ptt5": 513216,
    "sum": 38240, "xargs.1": 4227,
}


def ratio(size, original):
    return 100.0 * size / original


def benchmark_config():
    # Broad enough to exercise the native portfolio, bounded enough to be a repeatable
    # standard gate. --extreme remains a separate research mode.
    return StreamConfig(
        min_block=4096,
        max_block=16384,
        probe_stride=1024,
        split_gain_bits=96.0,
        history_bytes=1 << 20,
        lz_window_bytes=1 << 20,
        lz_chain=32,
        context_beam=3,
        transform_beam=4,
        adaptive_beam=2,
        enable_chains=False,
        context_models=(
            ContextModel(1, 8),
            ContextModel(2, 8),
            ContextModel(2, 10),
            ContextModel(4, 10),
            ContextModel(6, 12),
        ),
    )


def main():
    work = Path("benchmark-work")
    work.mkdir(exist_ok=True)
    archive = work / "cantrbry.tar.gz"
    urllib.request.urlretrieve(CORPUS_URL, archive)

    dest = work / "canterbury-native-current"
    with tarfile.open(archive, "r:gz") as tf:
        tf.extractall(dest, filter="data")

    files = {
        p.name: p for p in dest.rglob("*")
        if p.is_file() and p.name in EXPECTED
    }
    missing = sorted(set(EXPECTED) - set(files))
    if missing:
        raise RuntimeError(f"missing Canterbury files: {missing}")

    totals = {"original": 0, "gzip": 0, "bzip2": 0, "xz": 0, "cix": 0}
    rows = []

    for name, expected_size in EXPECTED.items():
        data = files[name].read_bytes()
        if len(data) != expected_size:
            raise RuntimeError(
                f"{name}: expected {expected_size}, got {len(data)}"
            )

        started = time.perf_counter()
        encoder = StreamEncoder(benchmark_config())
        blob = encoder.feed(data) + encoder.finish()
        elapsed = time.perf_counter() - started

        restored = decompress(blob)
        if restored != data:
            raise RuntimeError(f"{name}: native CIX round-trip mismatch")

        gz = len(gzip.compress(data, 9))
        bz = len(bz2.compress(data, 9))
        xz = len(lzma.compress(data, preset=9))

        rows.append(
            (
                name, len(data), gz, bz, xz, len(blob), elapsed,
                ",".join(encoder.block_descriptions),
            )
        )
        totals["original"] += len(data)
        totals["gzip"] += gz
        totals["bzip2"] += bz
        totals["xz"] += xz
        totals["cix"] += len(blob)

        print(
            name,
            f"CIX={ratio(len(blob),len(data)):.2f}%",
            f"xz={ratio(xz,len(data)):.2f}%",
            f"{elapsed:.2f}s",
            flush=True,
        )

    out = [
        "# Current native CIX Canterbury baseline",
        "",
        "All CIX sizes are physical byte streams and round-trip verified.",
        "",
        "| file | gzip-9 | bzip2-9 | xz-9 | native CIX | seconds |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name, original, gz, bz, xz, cix, elapsed, descriptions in rows:
        out.append(
            f"| {name} | {ratio(gz,original):.2f}% | "
            f"{ratio(bz,original):.2f}% | {ratio(xz,original):.2f}% | "
            f"{ratio(cix,original):.2f}% | {elapsed:.2f} |"
        )

    original = totals["original"]
    out += [
        "",
        f"- Original: {original:,} bytes",
        f"- gzip-9 aggregate: {ratio(totals['gzip'],original):.2f}%",
        f"- bzip2-9 aggregate: {ratio(totals['bzip2'],original):.2f}%",
        f"- xz-9 aggregate: {ratio(totals['xz'],original):.2f}%",
        f"- native CIX aggregate: {ratio(totals['cix'],original):.2f}%",
        "",
        "## Winning block models",
    ]
    for name, _, _, _, _, _, _, descriptions in rows:
        out.append(f"- {name}: {descriptions}")

    Path("native-current-results.md").write_text("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
