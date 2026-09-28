"""Standalone experimental CIX portfolio encoder and decoder.

Run from the repository root with the pinned local native dependencies installed.
Encoding never consults corpus files, saved benchmark streams or their hashes.
Every encoded stream is independently decoded before the destination is written.
"""
import argparse
import json
import resource
import time
from pathlib import Path
from benchmarks import competitive_ecoff as codec
from benchmarks.competitive_codec import sha


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('encode', 'decode'))
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    if args.destination.exists():
        parser.error('destination already exists; choose a new path')
    data = args.source.read_bytes()
    start = time.perf_counter()
    if args.operation == 'encode':
        output, selection = codec.encode(data)
        seconds = time.perf_counter()-start
        verify_start = time.perf_counter()
        restored = codec.decode(output)
        if restored != data:
            raise ValueError('independent full-stream restoration failed')
        verification_seconds = time.perf_counter()-verify_start
        extra = dict(selection=selection, round_trip=True, verify_seconds=verification_seconds)
    else:
        output = codec.decode(data)
        seconds = time.perf_counter()-start
        extra = dict(source_frame_decoded=True)
    # Exclusive creation also prevents a late overwrite if another process
    # creates the destination while an expensive encode is running.
    with args.destination.open('xb') as out:
        out.write(output)
    print(json.dumps(dict(policy=codec.NAME, operation=args.operation,
        source_bytes=len(data), output_bytes=len(output), source_sha256=sha(data),
        output_sha256=sha(output), seconds=seconds,
        peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        child_peak_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
        **extra), indent=2))


if __name__ == '__main__':
    main()
