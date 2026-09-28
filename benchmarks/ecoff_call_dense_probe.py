"""Discriminate call models on complete objects with many alternate targets."""
import argparse
import concurrent.futures
import json
from pathlib import Path
from benchmarks import ecoff_call_entries_probe as paq, ecoff_call_brotli_probe as brotli
from benchmarks.competitive_codec import sha

REGIONS = [(43270656, 253952), (50919936, 114688), (51126272, 49152)]


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--output', required=True)
    p.add_argument('--backend', choices=['paq', 'brotli'], default='paq'); p.add_argument('--jobs', type=int, default=2)
    p.add_argument('--modes', nargs='+', type=int, default=[0, 1, 5]); args = p.parse_args()
    root = Path(args.output).resolve(); root.mkdir(parents=True, exist_ok=True); digest = sha(Path(__file__).read_bytes())
    if args.backend == 'paq':
        worker = paq.worker; specs = [(o, n, m, '-4', str(root)) for o, n in REGIONS for m in args.modes]
    else:
        worker = brotli.worker; specs = [(o, n, m, True, str(root)) for o, n in REGIONS for m in args.modes]
    with concurrent.futures.ProcessPoolExecutor(args.jobs, max_tasks_per_child=1) as pool:
        rows = list(pool.map(worker, specs))
    if sha(Path(__file__).read_bytes()) != digest:
        raise ValueError('call-region driver changed')
    report = dict(complete=True, diagnostic_only=True, selection='objects with many alternate-entry calls; exploratory, not held out',
                  driver_sha256=digest, regions=REGIONS, rows=rows)
    (root / 'complete.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
