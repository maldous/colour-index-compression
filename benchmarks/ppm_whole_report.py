"""Verify the complete prerequisite PPM tournament and assemble selected frames."""
import hashlib
import json
from pathlib import Path


def main():
    from benchmarks.fast_runtime import enable
    enable()
    from benchmarks.ppm_whole_input import decode
    from cix.multinomial import decompress
    root = Path('results/leaderboard')
    experiment = root / 'ppm-whole-tier1'
    manifest = json.loads(Path('results/corpus-manifest.json').read_text())
    rows = [json.loads(line) for path in experiment.glob('results-*.jsonl')
            for line in path.read_text().splitlines()]
    assert len(rows) == 87
    # Canterbury ptt5 and Calgary pic contain identical bytes; retain both labels.
    assert len({(r['file'], r['input_sha256'], r['order']) for r in rows}) == 87
    output = []
    target = experiment / 'selected'
    target.mkdir(exist_ok=True)
    for item in manifest:
        data = Path(item['path']).read_bytes()
        sha = hashlib.sha256(data).hexdigest()
        assert sha == item['sha256'] and len(data) == item['size']
        name = Path(item['path']).name
        label = item['corpus'] + '-' + name
        old = json.loads((root / 'tier1' / (label + '.json')).read_text())
        blob = (root / 'tier1' / (label + '.cixm')).read_bytes()
        assert old['round_trip'] and old['identity']['input_sha256'] == sha
        assert len(blob) == old['size'] and hashlib.sha256(blob).hexdigest() == old['compressed_sha256']
        candidates = [('incumbent', blob)]
        trials = [r for r in rows if r['input_sha256'] == sha and r['file'] == name]
        assert {r['order'] for r in trials} == {3, 5, 7}
        for row in sorted(trials, key=lambda r: r['order']):
            assert row['round_trip'] and row['source_tree_sha256'] == old['identity']['source_tree_sha256']
            frame = (experiment / 'artifacts' / (sha + '-o' + str(row['order']) + '.cixp')).read_bytes()
            assert len(frame) == row['size'] and hashlib.sha256(frame).hexdigest() == row['frame_sha256']
            candidates.append(('ppm-o' + str(row['order']), frame))
        mode, chosen = min(candidates, key=lambda pair: len(pair[1]))
        restored = decompress(chosen) if mode == 'incumbent' else decode(chosen)
        assert restored == data
        (target / (label + '.cix-experimental')).write_bytes(chosen)
        row = dict(corpus=item['corpus'], file=name, original=len(data), incumbent=old['size'],
                   selected=len(chosen), saved=old['size'] - len(chosen), mode=mode,
                   round_trip=True, sha256=hashlib.sha256(chosen).hexdigest())
        output.append(row)
        print(json.dumps(row), flush=True)
    aggregates = {}
    for corpus in ('canterbury', 'calgary'):
        members = [r for r in output if r['corpus'] == corpus]
        aggregates[corpus] = {k: sum(r[k] for r in members)
                             for k in ('original', 'incumbent', 'selected', 'saved')}
    report = dict(complete=True, experimental=True,
        policy='Exact physical minimum of frozen level-3 CIX and whole-input PPM orders 3,5,7; incumbent wins ties. Distinct self-identifying magic; no additional selector.',
        limitation='Production decoder does not yet accept experimental PPM frames. Whole-input contexts need a generic memory bound before Silesia.',
        members=output, aggregates=aggregates)
    Path('docs/research/2026-09-28-whole-ppm-tier1.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(aggregates), flush=True)


if __name__ == '__main__':
    main()
