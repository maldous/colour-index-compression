#!/usr/bin/env python3
"""Regenerate complete candidate tables from rehashed domain receipts."""
from __future__ import annotations
import csv
import json
from pathlib import Path
from benchmarks import domain_research as research


def main():
    report = research.report()
    area = research.ROOT / research.REL
    rows = []
    for source in report['rows']:
        control = source.get('control')
        control_bytes = control['archive_bytes'] if control else (source['complete_bytes'] if source['variant'] == 'original' else None)
        complete = source['complete_bytes']
        delta = complete - control_bytes if complete is not None and control_bytes is not None else None
        row = {
            'domain': source['domain'], 'input': Path(source['input']['path']).name,
            'input_sha256': source['input']['sha256'], 'original_bytes': source['input']['length'],
            'variant': source['variant'], 'backend': source['backend'],
            'control_bytes': control_bytes, 'complete_bytes': complete, 'delta_bytes': delta,
            'saving_vs_control_percent': -delta / control_bytes * 100 if delta is not None else None,
            'outer_header_bytes': source.get('header_bytes'), 'outer_metadata_bytes': source.get('metadata_bytes'),
            'backend_payload_bytes': source.get('payload_bytes'), 'transform_frame_bytes': source.get('transformed_bytes'),
            'verification': source['verification'], 'encode_seconds': source['encode_seconds'],
            'decode_seconds': source['decode_seconds'], 'encode_peak_rss_kib': source['encode_peak_process_rss_kib'],
            'decode_peak_rss_kib': source['decode_peak_process_rss_kib'],
            'sampled_cgroup_memory_bytes': source['memory_lower_bound_bytes'],
            'sampled_temporary_bytes': source['temporary_disk_high_water_bytes'],
            'cell_id': source['cell_id'], 'receipt': source['terminal_record'],
        }
        if complete is not None:
            assert row['outer_header_bytes'] + row['outer_metadata_bytes'] + row['backend_payload_bytes'] == complete
        rows.append(row)
    rows.sort(key=lambda r: (r['domain'], r['input'], r['variant'] != 'original', r['variant']))
    (area / 'results.json').write_text(json.dumps({'source_commit': json.loads((area / 'pilot-v1.json').read_text())['source_commit'],
        'formula': 'delta_bytes = complete_bytes - matched_control_bytes; saving_percent = -delta_bytes / matched_control_bytes * 100',
        'rows': rows}, indent=2) + '\n')
    with (area / 'results.csv').open('w', newline='') as out:
        writer = csv.DictWriter(out, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader(); writer.writerows(rows)
    text = ['# All domain candidates before selection', '',
            'Control: PAQ v216 `-4 -simd AVX2`, one CPU, identical input bytes and paid outer framing. '
            'Every row includes all physical archive bytes. Negative Δ means smaller. All figures apply only to the named input. '
            'JXL is a backend change, not evidence for a CIX rank coder. Timing is one exploratory measured command per phase.', '',
            '| Input / candidate | PAQ B | Complete B | Δ B | Encode / decode s | Peak RSS MiB encode / decode | Verification |',
            '|---|---:|---:|---:|---:|---:|---|']
    def fmt(value, digits=2):
        return f'{value:.{digits}f}' if isinstance(value, (int, float)) else '—'
    for r in rows:
        memory = ' / '.join(fmt(r[k] / 1024 if r[k] is not None else None, 1) for k in ('encode_peak_rss_kib', 'decode_peak_rss_kib'))
        timing = ' / '.join(fmt(r[k]) for k in ('encode_seconds', 'decode_seconds'))
        text.append(f"| {r['input']} / {r['variant']} | {r['control_bytes'] if r['control_bytes'] is not None else '—'} | {r['complete_bytes'] if r['complete_bytes'] is not None else '—'} | {r['delta_bytes'] if r['delta_bytes'] is not None else '—'} | {timing} | {memory} | {r['verification']} |")
    text += ['', 'Machine-readable `results.csv` and `results.json` include exact hashes, cell identities, payload/metadata costs and receipt paths. '
             'GNU-time Max RSS is the maximum recorded for a command or its children, not simultaneous process-tree RSS. '
             'Sampled cgroup memory and disk are separate. Decoder/runtime package size is not an archive-size claim. '
             'There is no portfolio selector or cross-dataset leaderboard in this report.', '']
    (area / 'CANDIDATE-TABLE.md').write_text('\n'.join(text))
    print(json.dumps({'rows': len(rows), 'verified': sum(r['verification'] == 'SHA256_MATCHED_REHASHED' for r in rows)}))


if __name__ == '__main__':
    main()
