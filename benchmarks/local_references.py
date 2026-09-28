#!/usr/bin/env python3
"""Round-trip-verified local reference compressors for materialized corpus bytes."""
import argparse
import bz2
import gzip
import hashlib
import json
import lzma
from pathlib import Path
import platform
import time
import zlib

import brotli
import zstandard


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest', default='results/corpus-manifest.json')
    p.add_argument('--output', default='results/tier1-references.jsonl')
    args = p.parse_args()
    versions = dict(python=platform.python_version(), zlib=zlib.ZLIB_RUNTIME_VERSION,
                    brotli=brotli.__version__, zstandard=zstandard.__version__)
    codecs = {
        'gzip-9': (lambda b: gzip.compress(b, compresslevel=9, mtime=0), gzip.decompress),
        'bzip2-9': (lambda b: bz2.compress(b, compresslevel=9), bz2.decompress),
        'xz-9': (lambda b: lzma.compress(b, preset=9), lzma.decompress),
        'brotli-11': (lambda b: brotli.compress(b, quality=11), brotli.decompress),
        'zstd-19': (lambda b: zstandard.ZstdCompressor(level=19).compress(b),
                    zstandard.ZstdDecompressor().decompress),
    }
    with Path(args.output).open('w') as out:
        for item in json.loads(Path(args.manifest).read_text()):
            data = Path(item['path']).read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            if digest != item['sha256']:
                raise RuntimeError('corpus changed')
            row = dict(corpus=item['corpus'], file=Path(item['path']).name,
                       original=len(data), sha256=digest, versions=versions, codecs={})
            for name, (encode, decode) in codecs.items():
                started = time.perf_counter()
                blob = encode(data)
                encode_seconds = time.perf_counter() - started
                started = time.perf_counter()
                assert decode(blob) == data
                row['codecs'][name] = dict(size=len(blob), encode_seconds=encode_seconds,
                                          decode_seconds=time.perf_counter() - started,
                                          round_trip=True)
            out.write(json.dumps(row) + '\n'); out.flush()
            print(row['corpus'], row['file'], flush=True)


if __name__ == '__main__':
    main()
