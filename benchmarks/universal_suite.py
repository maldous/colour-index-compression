#!/usr/bin/env python3
"""Cross-corpus universal compression gate.

The same CIX configuration is applied to every file. No filename, extension, corpus name,
or file category is passed into the encoder.

Reporting follows the Canterbury Corpus conventions:
- Canterbury: fixed aggregate is meaningful.
- Calgary: fixed aggregate is meaningful.
- Artificial: report members individually; no aggregate claim.
- Large: report fixed members individually; no overall average claim.
"""

from __future__ import annotations

import argparse
import bz2
import gzip
import json
import lzma
import tarfile
import time
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path

try:
    import brotli
except ImportError:
    brotli = None

try:
    import zstandard as zstd
except ImportError:
    zstd = None

from cix.cli import config_for_level
from cix.multinomial import StreamEncoder, decompress


CORPORA = {
    "canterbury": "https://corpus.canterbury.ac.nz/resources/cantrbry.tar.gz",
    "calgary": "https://corpus.canterbury.ac.nz/resources/calgary.tar.gz",
    "artificial": "https://corpus.canterbury.ac.nz/resources/artificl.tar.gz",
    "large": "https://corpus.canterbury.ac.nz/resources/large.tar.gz",
}

AGGREGATE_CORPORA = {"canterbury", "calgary"}


@dataclass
class Result:
    corpus: str
    file: str
    original: int
    cix: int
    gzip: int
    bzip2: int
    xz: int
    brotli: int | None
    zstd: int | None
    cix_seconds: float
    models: list[str]


def ratio(size: int, original: int) -> float:
    return 100.0 * size / original if original else 100.0


def download_and_extract(name: str, work: Path) -> list[Path]:
    archive = work / f"{name}.tar.gz"
    destination = work / name
    if not archive.exists():
        urllib.request.urlretrieve(CORPORA[name], archive)
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, "r:gz") as tf:
        tf.extractall(destination, filter="data")
    return sorted(p for p in destination.rglob("*") if p.is_file())


def compress_one(corpus: str, path: Path, level: int) -> Result:
    data = path.read_bytes()
    config = config_for_level(level)

    started = time.perf_counter()
    encoder = StreamEncoder(config)
    blob = encoder.feed(data) + encoder.finish()
    elapsed = time.perf_counter() - started

    restored = decompress(blob)
    if restored != data:
        raise RuntimeError(f"round-trip mismatch for {corpus}/{path.name}")

    brotli_size = (
        len(brotli.compress(data, quality=11))
        if brotli is not None else None
    )
    zstd_size = (
        len(zstd.ZstdCompressor(level=19).compress(data))
        if zstd is not None else None
    )

    return Result(
        corpus=corpus,
        file=path.name,
        original=len(data),
        cix=len(blob),
        gzip=len(gzip.compress(data, 9)),
        bzip2=len(bz2.compress(data, 9)),
        xz=len(lzma.compress(data, preset=9)),
        brotli=brotli_size,
        zstd=zstd_size,
        cix_seconds=elapsed,
        models=list(encoder.block_descriptions),
    )


def render(results: list[Result]) -> str:
    lines = [
        "# CIX universal cross-corpus benchmark",
        "",
        "The identical format-agnostic CIX policy is used for every member.",
        "",
    ]

    for corpus in CORPORA:
        subset = [r for r in results if r.corpus == corpus]
        if not subset:
            continue

        lines += [
            f"## {corpus}",
            "",
            "| file | CIX | gzip-9 | bzip2-9 | xz-9 | Brotli-11 | zstd-19 | CIX seconds |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]

        for r in subset:
            brotli_cell = (
                f"{ratio(r.brotli,r.original):.2f}%"
                if r.brotli is not None else "—"
            )
            zstd_cell = (
                f"{ratio(r.zstd,r.original):.2f}%"
                if r.zstd is not None else "—"
            )
            lines.append(
                f"| {r.file} | {ratio(r.cix,r.original):.2f}% | "
                f"{ratio(r.gzip,r.original):.2f}% | "
                f"{ratio(r.bzip2,r.original):.2f}% | "
                f"{ratio(r.xz,r.original):.2f}% | "
                f"{brotli_cell} | {zstd_cell} | {r.cix_seconds:.2f} |"
            )

        if corpus in AGGREGATE_CORPORA:
            original = sum(r.original for r in subset)
            lines += [
                "",
                f"- Aggregate CIX: {ratio(sum(r.cix for r in subset),original):.2f}%",
                f"- Aggregate gzip-9: {ratio(sum(r.gzip for r in subset),original):.2f}%",
                f"- Aggregate bzip2-9: {ratio(sum(r.bzip2 for r in subset),original):.2f}%",
                f"- Aggregate xz-9: {ratio(sum(r.xz for r in subset),original):.2f}%",
            ]
            if all(r.brotli is not None for r in subset):
                lines.append(
                    f"- Aggregate Brotli-11: "
                    f"{ratio(sum(r.brotli for r in subset if r.brotli is not None),original):.2f}%"
                )
            if all(r.zstd is not None for r in subset):
                lines.append(
                    f"- Aggregate zstd-19: "
                    f"{ratio(sum(r.zstd for r in subset if r.zstd is not None),original):.2f}%"
                )
        else:
            lines += [
                "",
                "- No aggregate is claimed for this corpus; member results are reported individually.",
            ]

        lines.append("")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--corpora",
        nargs="+",
        choices=tuple(CORPORA),
        default=["canterbury", "calgary", "artificial"],
    )
    parser.add_argument("--level", type=int, default=6, choices=range(1, 10))
    parser.add_argument("--work", default="benchmark-work/universal")
    args = parser.parse_args()

    work = Path(args.work)
    work.mkdir(parents=True, exist_ok=True)
    results: list[Result] = []

    for corpus in args.corpora:
        for path in download_and_extract(corpus, work):
            result = compress_one(corpus, path, args.level)
            results.append(result)
            print(
                corpus,
                path.name,
                f"CIX={ratio(result.cix,result.original):.2f}%",
                f"xz={ratio(result.xz,result.original):.2f}%",
                f"{result.cix_seconds:.2f}s",
                flush=True,
            )
            Path("universal-progress.json").write_text(
                json.dumps([asdict(r) for r in results], indent=2)
            )

    Path("universal-results.md").write_text(render(results) + "\n")
    Path("universal-results.json").write_text(
        json.dumps([asdict(r) for r in results], indent=2)
    )


if __name__ == "__main__":
    main()
