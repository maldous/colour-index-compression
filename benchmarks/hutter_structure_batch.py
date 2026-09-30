"""Run the predeclared remaining structural screens; never reads holdouts."""
import copy
import hashlib
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from benchmarks.hutter_bounded_runner import run


def main():
    folder = ROOT / 'docs/research/2026-09-30-wikipedia-structure'
    template = json.loads((folder / 'dev0-original-paq.manifest.json').read_text())
    manifests = folder / 'remaining-manifests'
    manifests.mkdir(exist_ok=True)
    # No random content or external models; exact fixed synthetic grammar.
    page = (b'<page><title>Topic %04d</title><id>%06d</id><revision>'
            b'<timestamp>2006-03-01T12:00:00Z</timestamp><text xml:space="preserve">'
            b'{{Infobox|name=example}} A &amp; B. [[Earlier title]]  007\n'
            b'</text></revision></page>\n')
    synthetic = b'<mediawiki>\n' + b''.join(page % (i, i) for i in range(140)) + b'</mediawiki>'
    synth_path = folder / 'synthetic-pages.bin'
    if synth_path.exists() and synth_path.read_bytes() != synthetic:
        raise ValueError('synthetic fixture changed')
    synth_path.write_bytes(synthetic)
    sources = [('dev100M', Path(template['input']['path']), 100000000, 32768),
               ('dev400M', Path(template['input']['path']), 400000000, 32768),
               ('synthetic', synth_path, 0, len(synthetic))]
    jobs = []
    for name, source, offset, length in sources:
        with source.open('rb') as stream:
            stream.seek(offset)
            data = stream.read(length)
        assert len(data) == length
        for mode in ('original', 'B', 'C', 'D'):
            m = copy.deepcopy(template)
            m['hypothesis'] = 'The frozen structural representation reduces complete physical bytes versus identical original-byte PAQ.'
            m['mechanism'] = {'original':'control', 'B':'local closing-tag prediction',
                              'C':'shared typed streams', 'D':'shared page skeletons'}[mode]
            m['input'] = dict(path=str(source), offset=offset, length=length,
                              sha256=hashlib.sha256(data).hexdigest())
            m['configuration']['mode'] = mode
            m['configuration']['execution_boundary'] = 'parent and child explicitly pinned CPU6'
            m['initial_state'] = 'empty; no warm-up; deterministic synthetic generation when applicable'
            m['promotion_criteria'] = 'All exact; >=0.5% aggregate development saving and >=2/3 region wins; never promote from synthetic alone.'
            m['build_paths'] = sorted(set(m['build_paths'] + ['benchmarks/hutter_structure_batch.py']))
            command = m['encode_command']
            command[command.index('--mode') + 1] = mode
            path = manifests / f'{name}-{mode}-cpu6.json'
            if path.exists() and json.loads(path.read_text()) != m:
                raise ValueError('immutable manifest mismatch')
            path.write_text(json.dumps(m, indent=2) + '\n')
            jobs.append((name, mode, path))
    # All source identities/configurations are fixed before any measurement.
    rows = []
    header = struct.Struct('>8sBQQI')
    for name, mode, path in jobs:
        result = run(path, folder / 'results', ROOT)
        if result['status'] == 'REUSED_VERIFIED':
            result = json.loads(Path(result['receipt']).read_text())
        if result['status'] != 'VERIFIED_SCREENING':
            raise RuntimeError(f'{name}/{mode} failed; inspect retained receipt')
        archive = Path(result['artifacts']['archive']).read_bytes()
        _, _, original, transformed, metadata_length = header.unpack_from(archive)
        meta = json.loads(archive[header.size:header.size+metadata_length])
        row = dict(dataset=name, mode=mode, original_bytes=original, total_bytes=len(archive),
                   paq_payload_bytes=len(archive)-header.size-metadata_length,
                   metadata_bytes=metadata_length, framing_bytes=header.size,
                   transform_bytes=transformed, transform_accounting=meta,
                   phases=result['phases'], input=result['identity']['input'],
                   verification=result['verification'], archive_sha256=result['archive_sha256'],
                   receipt=result.get('receipt'), experiment_id=result['experiment_id'])
        rows.append(row)
        (folder / 'remaining-comparison.json').write_text(json.dumps(rows, indent=2) + '\n')
        print(json.dumps({k:row[k] for k in ('dataset','mode','total_bytes','metadata_bytes','framing_bytes')}), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
