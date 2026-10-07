#!/usr/bin/env python3
"""Compare exact bounded PPM search with the exhaustive incumbent tournament."""
import argparse
import hashlib
import json
from pathlib import Path
import statistics
import time

from cix.ppm import (
    ESCAPE_METHODS, _encode_ppm_method, _encode_ppm_see, decode_ppm, encode_ppm,
)


def exhaustive(data, history, order):
    candidates = [
        _encode_ppm_method(data, max_order=order, prefix_history=history,
                           escape_method=method, update_exclusion=variant)
        for variant in (False, True) for method in ESCAPE_METHODS
    ] + [
        _encode_ppm_see(data, max_order=order, prefix_history=history,
                        update_exclusion=variant)
        for variant in (False, True)
    ]
    return min(candidates, key=len)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('files', nargs='+')
    p.add_argument('--output', default='results/ppm-search.json')
    p.add_argument('--repeats', type=int, default=3)
    args = p.parse_args()
    rows = []
    for name in args.files:
        source = Path(name).read_bytes()
        history, data = source[:16384], source[16384:20480]
        if not data:
            midpoint = len(source) // 2
            history, data = source[:midpoint], source[midpoint:midpoint + 4096]
        times = {'exhaustive': [], 'bounded': []}
        blobs = {}
        for trial in range(args.repeats):
            methods = ['exhaustive', 'bounded']
            if trial % 2:
                methods.reverse()
            for method in methods:
                started = time.perf_counter()
                blob = (exhaustive(data, history, 4) if method == 'exhaustive'
                        else encode_ppm(data, max_order=4, prefix_history=history))
                times[method].append(time.perf_counter() - started)
                blobs[method] = blob
            assert blobs['exhaustive'] == blobs['bounded']
            assert decode_ppm(blob, source_length=len(data), prefix_history=history) == data
        medians = {k: statistics.median(v) for k, v in times.items()}
        row = dict(file=name, source_sha256=hashlib.sha256(source).hexdigest(),
                   source_bytes=len(data), history_bytes=len(history), size=len(blob),
                   byte_identical=True, round_trip=True, timings=times,
                   median_seconds=medians, speedup=medians['exhaustive']/medians['bounded'])
        rows.append(row)
        print(json.dumps(row), flush=True)
        Path(args.output).write_text(json.dumps(rows, indent=2) + '\n')


if __name__ == '__main__':
    main()
