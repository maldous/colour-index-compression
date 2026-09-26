#!/usr/bin/env python3
import bz2, gzip, lzma, math, os, tarfile, urllib.request
from collections import Counter
from pathlib import Path

import numpy as np

CORPUS_URL = "https://corpus.canterbury.ac.nz/resources/cantrbry.tar.gz"
BLOCKS = (15, 31, 63, 127, 255)
FOOTER_BITS = 256
TRANSFORM_SELECTOR_BITS = 8
EXPECTED = {
    "alice29.txt": 152089, "asyoulik.txt": 125179, "cp.html": 24603,
    "fields.c": 11150, "grammar.lsp": 3721, "kennedy.xls": 1029744,
    "lcet10.txt": 426754, "plrabn12.txt": 481861, "ptt5": 513216,
    "sum": 38240, "xargs.1": 4227,
}
LOGCOMB = {
    n: np.array([math.log2(math.comb(n, k)) for k in range(n // 2 + 1)])
    for n in BLOCKS
}

def enum_cost(bits, n):
    bits = np.asarray(bits, dtype=np.uint8)
    pad = (-len(bits)) % n
    if pad:
        bits = np.pad(bits, (0, pad))
    blocks = bits.reshape(-1, n)
    ones = blocks.sum(axis=1).astype(np.int16)
    maj = (ones > n // 2).astype(np.int16)
    k = np.minimum(ones, n - ones)
    ids = maj * (n // 2 + 1) + k
    counts = np.bincount(ids)
    counts = counts[counts > 0]
    p = counts / counts.sum()
    header = float(-(counts * np.log2(p)).sum())
    return float(LOGCOMB[n][k].sum() + header + pad)

def best_backend(bits):
    return min((enum_cost(bits, n), n) for n in BLOCKS)

def cheap_entropy(bits):
    if not len(bits):
        return 0.0
    p = float(np.mean(bits))
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return len(bits) * (-p*math.log2(p) - (1-p)*math.log2(1-p))

def candidates(data):
    a = np.frombuffer(data, dtype=np.uint8)
    raw = np.unpackbits(a)
    yield "identity", raw, 0

    # Bit-level predictors.
    for lag in (1, 2, 3, 4, 8, 16, 24, 32, 64):
        if lag < len(raw):
            x = raw.copy()
            x[lag:] = raw[lag:] ^ raw[:-lag]
            yield f"bit-xor-{lag}", x, 8

    # Byte-level correlation/repetition predictors.
    for lag in list(range(1, 65)) + ( [96, 128, 192, 256] if len(a) > 256 else [] ):
        if lag < len(a):
            x = a.copy()
            x[lag:] = a[lag:] ^ a[:-lag]
            yield f"byte-xor-{lag}", np.unpackbits(x), 12

    # Delta predictors for local numeric structure.
    for lag in (1, 2, 4, 8, 16, 32):
        if lag < len(a):
            x = a.copy()
            x[lag:] = ((a[lag:].astype(np.int16) - a[:-lag].astype(np.int16)) & 255).astype(np.uint8)
            yield f"byte-sub-{lag}", np.unpackbits(x), 10

    # Bit-plane representation.
    if len(a):
        yield "bitplane8", np.unpackbits(a).reshape(-1, 8).T.reshape(-1), 4

    # 32-bit delta + byte shuffle for integer-like streams.
    usable = (len(data) // 4) * 4
    if usable >= 8:
        w = np.frombuffer(data[:usable], dtype="<u4")
        d = np.empty_like(w)
        d[0] = w[0]
        d[1:] = w[1:] - w[:-1]
        db = np.frombuffer(d.tobytes(), dtype=np.uint8).reshape(-1, 4)
        shuffled = db.T.reshape(-1)
        tail = np.frombuffer(data[usable:], dtype=np.uint8)
        out = np.concatenate((shuffled, tail))
        yield "delta32-shuffle", np.unpackbits(out), 8

def cix_model(data, shortlist=12):
    # Search cheaply, exact-score only the most promising candidates.
    scored = []
    for name, bits, meta in candidates(data):
        scored.append((cheap_entropy(bits) + meta, name, bits, meta))
    scored.sort(key=lambda x: x[0])
    best = (len(data) * 8 + 1, "raw", None)
    for _, name, bits, meta in scored[:shortlist]:
        cost, block = best_backend(bits)
        cost += FOOTER_BITS + TRANSFORM_SELECTOR_BITS + meta
        if cost < best[0]:
            best = (cost, name, block)
    return best

def ratio(size_bytes, original):
    return 100.0 * size_bytes / original

def main():
    work = Path("benchmark-work")
    work.mkdir(exist_ok=True)
    archive = work / "cantrbry.tar.gz"
    urllib.request.urlretrieve(CORPUS_URL, archive)
    with tarfile.open(archive, "r:gz") as tf:
        tf.extractall(work / "canterbury")

    # Tar contains files directly or under a directory depending on mirror/version.
    files = {}
    for p in (work / "canterbury").rglob("*"):
        if p.is_file() and p.name in EXPECTED:
            files[p.name] = p
    missing = sorted(set(EXPECTED) - set(files))
    if missing:
        raise RuntimeError(f"Missing Canterbury files: {missing}")

    rows = []
    total_orig = total_gz = total_bz = total_xz = 0
    total_cix_bits = 0.0

    for name in EXPECTED:
        data = files[name].read_bytes()
        if len(data) != EXPECTED[name]:
            raise RuntimeError(f"{name}: expected {EXPECTED[name]} bytes, got {len(data)}")
        gz = len(gzip.compress(data, compresslevel=9))
        bz = len(bz2.compress(data, compresslevel=9))
        xz = len(lzma.compress(data, preset=9))
        cix_bits, transform, block = cix_model(data)
        cix_bytes = math.ceil(cix_bits / 8)

        rows.append((name, len(data), gz, bz, xz, cix_bytes, transform, block))
        total_orig += len(data); total_gz += gz; total_bz += bz; total_xz += xz
        total_cix_bits += cix_bits

    out = []
    out.append("# Canterbury benchmark\n")
    out.append("CIX is a **modelled enumerative size**, not yet a physical archive. gzip/bzip2/xz are physical byte outputs.\n")
    out.append("| file | original | gzip-9 | bzip2-9 | xz-9 | CIX model | CIX transform | block |")
    out.append("|---|---:|---:|---:|---:|---:|---|---:|")
    for name, orig, gz, bz, xz, cix, transform, block in rows:
        out.append(
            f"| {name} | {orig} | {ratio(gz,orig):.2f}% | {ratio(bz,orig):.2f}% | "
            f"{ratio(xz,orig):.2f}% | {ratio(cix,orig):.2f}% | {transform} | {block or '-'} |"
        )
    cix_total_bytes = math.ceil(total_cix_bits / 8)
    out.append("")
    out.append(f"- Total original: {total_orig:,} bytes")
    out.append(f"- gzip-9 aggregate: {ratio(total_gz,total_orig):.2f}%")
    out.append(f"- bzip2-9 aggregate: {ratio(total_bz,total_orig):.2f}%")
    out.append(f"- xz-9 aggregate: {ratio(total_xz,total_orig):.2f}%")
    out.append(f"- CIX model aggregate: {ratio(cix_total_bytes,total_orig):.2f}%")
    out.append("")
    out.append("## Interpretation")
    out.append("- Raw fallback is included.")
    out.append("- Footer/selector/transform metadata are charged in the CIX estimate.")
    out.append("- Combinatorial rank and symbol-stream costs are still entropy-model estimates; a real rANS/range-coded bitstream is required before production claims.")
    out.append("- This test intentionally exposes dictionary/text weaknesses rather than hiding them behind a conventional compressor.")

    Path("benchmark-results.md").write_text("\n".join(out) + "\n")
    print("\n".join(out))

if __name__ == "__main__":
    main()
