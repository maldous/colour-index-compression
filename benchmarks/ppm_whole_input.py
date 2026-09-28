"""Diagnostic whole-input generic PPM tournament, not a CIX leaderboard result.

The experimental frame includes a version, length, CRC and PPM's own model
selector. No filename or benchmark label enters compression. This experiment
measures the cost of block resets before considering production integration.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time
import zlib


def encode(data, order):
    from cix.ppm import encode_ppm
    from cix.multinomial import vencode
    return (b'CIXP\x01' + vencode(len(data))
            + zlib.crc32(data).to_bytes(4, 'big')
            + encode_ppm(data, max_order=order))


def decode(frame):
    from cix.ppm import decode_ppm
    from cix.multinomial import vdecode
    if frame[:5] != b'CIXP\x01':
        raise ValueError('invalid experimental frame')
    size, offset = vdecode(frame, 5)
    crc = int.from_bytes(frame[offset:offset + 4], 'big')
    data = decode_ppm(frame[offset + 4:], source_length=size)
    if zlib.crc32(data) != crc:
        raise ValueError('checksum mismatch')
    return data


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--orders', type=int, nargs='+', default=[3, 5, 7])
    p.add_argument('--artifacts')
    args = p.parse_args()
    from benchmarks.fast_runtime import enable
    enable()
    from benchmarks.local_compare import source_digest
    digest = source_digest(Path(__file__).resolve().parents[1])
    # Append completed evidence immediately, so interruption loses no prior result.
    with Path(args.output).open('a') as out:
        for item in json.loads(Path(args.manifest).read_text()):
            data = Path(item['path']).read_bytes()
            sha = hashlib.sha256(data).hexdigest()
            if sha != item['sha256'] or len(data) != item['size']:
                raise ValueError('input manifest mismatch')
            for order in args.orders:
                start = time.perf_counter()
                frame = encode(data, order)
                elapsed = time.perf_counter() - start
                start = time.perf_counter()
                assert decode(frame) == data
                if args.artifacts:
                    target = Path(args.artifacts)
                    target.mkdir(parents=True, exist_ok=True)
                    (target / (sha + '-o' + str(order) + '.cixp')).write_bytes(frame)
                row = dict(file=Path(item['path']).name, original=len(data),
                           input_sha256=sha, source_tree_sha256=digest, order=order,
                           size=len(frame), round_trip=True, encode_seconds=elapsed,
                           decode_seconds=time.perf_counter() - start,
                           frame_sha256=hashlib.sha256(frame).hexdigest(),
                           experimental=True)
                out.write(json.dumps(row) + '\n')
                out.flush()
                print(json.dumps(row), flush=True)


if __name__ == '__main__':
    main()
