#!/usr/bin/env python3
"""Benchmark one standard-corpus member with the universal CIX policy."""

from __future__ import annotations

import argparse
import bz2
import gzip
import json
import lzma
import tarfile
import time
import urllib.request
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path

import brotli
import zstandard as zstd

from cix.cli import config_for_level
from cix.multinomial import StreamEncoder, decompress

CORPORA = {
    "canterbury": "https://corpus.canterbury.ac.nz/resources/cantrbry.tar.gz",
    "calgary": "https://corpus.canterbury.ac.nz/resources/calgary.tar.gz",
    "artificial": "https://corpus.canterbury.ac.nz/resources/artificl.tar.gz",
    "large": "https://corpus.canterbury.ac.nz/resources/large.tar.gz",
    "silesia": "https://mattmahoney.net/dc/silesia.zip",
}


@dataclass
class Result:
    corpus: str
    file: str
    original: int
    cix: int
    gzip: int
    bzip2: int
    xz: int
    brotli: int
    zstd: int
    cix_seconds: float
    cix_decode_seconds: float
    models: list[str]


def ratio(size: int, original: int) -> float:
    return 100.0 * size / original if original else 100.0


def member_bytes(corpus: str, member_name: str, work: Path) -> bytes:
    if corpus == "silesia":
        archive = work / "silesia.zip"
        if not archive.exists():
            urllib.request.urlretrieve(CORPORA[corpus], archive)
        with zipfile.ZipFile(archive) as zf:
            matches = [
                info for info in zf.infolist()
                if not info.is_dir() and Path(info.filename).name == member_name
            ]
            if len(matches) != 1:
                raise RuntimeError(
                    f"{corpus}/{member_name}: expected exactly one archive member, "
                    f"found {len(matches)}"
                )
            return zf.read(matches[0])

    archive = work / f"{corpus}.tar.gz"
    if not archive.exists():
        urllib.request.urlretrieve(CORPORA[corpus], archive)

    with tarfile.open(archive, "r:gz") as tf:
        matches = [
            member for member in tf.getmembers()
            if member.isfile() and Path(member.name).name == member_name
        ]
        if len(matches) != 1:
            raise RuntimeError(
                f"{corpus}/{member_name}: expected exactly one archive member, "
                f"found {len(matches)}"
            )
        stream = tf.extractfile(matches[0])
        if stream is None:
            raise RuntimeError(f"cannot read {corpus}/{member_name}")
        return stream.read()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", required=True, choices=tuple(CORPORA))
    parser.add_argument("--member", required=True)
    parser.add_argument("--level", type=int, default=6, choices=range(1, 10))
    parser.add_argument("--work", default="benchmark-work/universal-members")
    parser.add_argument("--out", default="universal-members")
    args = parser.parse_args()

    work = Path(args.work)
    work.mkdir(parents=True, exist_ok=True)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    data = member_bytes(args.corpus, args.member, work)
    config = config_for_level(args.level)

    started = time.perf_counter()
    encoder = StreamEncoder(config)
    blob = encoder.feed(data) + encoder.finish()
    encode_seconds = time.perf_counter() - started

    started = time.perf_counter()
    restored = decompress(blob)
    decode_seconds = time.perf_counter() - started
    if restored != data:
        raise RuntimeError(f"round-trip mismatch for {args.corpus}/{args.member}")

    result = Result(
        corpus=args.corpus,
        file=args.member,
        original=len(data),
        cix=len(blob),
        gzip=len(gzip.compress(data, 9)),
        bzip2=len(bz2.compress(data, 9)),
        xz=len(lzma.compress(data, preset=9)),
        brotli=len(brotli.compress(data, quality=11)),
        zstd=len(zstd.ZstdCompressor(level=19).compress(data)),
        cix_seconds=encode_seconds,
        cix_decode_seconds=decode_seconds,
        models=list(encoder.block_descriptions),
    )

    safe = "".join(
        character if character.isalnum() or character in "._-" else "_"
        for character in args.member
    )
    path = out_dir / f"{args.corpus}--{safe}.json"
    path.write_text(json.dumps(asdict(result), indent=2))

    print(
        args.corpus,
        args.member,
        f"CIX={ratio(result.cix,result.original):.2f}%",
        f"gzip={ratio(result.gzip,result.original):.2f}%",
        f"bzip2={ratio(result.bzip2,result.original):.2f}%",
        f"xz={ratio(result.xz,result.original):.2f}%",
        f"brotli={ratio(result.brotli,result.original):.2f}%",
        f"zstd={ratio(result.zstd,result.original):.2f}%",
        f"encode={encode_seconds:.2f}s",
        f"decode={decode_seconds:.2f}s",
        flush=True,
    )


if __name__ == "__main__":
    main()
