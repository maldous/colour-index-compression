#!/usr/bin/env python3
"""Extract authoritative NNLCB tables without silently correcting source values."""
import csv
import hashlib
import json
from pathlib import Path
import re
import statistics

ROOT = Path(__file__).resolve().parents[1]


def save(name, rows):
    (ROOT / 'tables' / (name + '.json')).write_text(json.dumps(rows, indent=2) + '\n')
    if rows:
        with (ROOT / 'tables' / (name + '.csv')).open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)


def main():
    readme = (ROOT / 'sources/nnlcb-README.md').read_text()
    aggregate = []
    keys = ['WavgCR', 'AvgCR', 'WavgSSP', 'AvgSSP', 'CRP', 'TotalCT_hours', 'TotalDT_hours', 'AvgCPM_reported_GB', 'AvgDPM_reported_GB']
    for line in readme.splitlines():
        if not line.startswith('|'):
            continue
        cells = [x.strip() for x in line.strip('|').split('|')]
        if len(cells) == 10:
            try:
                values = [float(x.replace('*', '')) for x in cells[1:]]
            except ValueError:
                continue
            aggregate.append(dict(algorithm=cells[0], **dict(zip(keys, values)), source='sources/nnlcb-README.md', environment='published NNLCB'))
    assert len(aggregate) == 16
    save('nnlcb-published-aggregates', aggregate)

    datasets = []
    for line in readme.splitlines():
        if not re.match(r'^\|D\d+\|', line):
            continue
        cells = [x.strip() for x in line.strip('|').split('|')]
        match = re.fullmatch(r'\[([^]]+)\]\((.+)\)', cells[1])
        assert match
        datasets.append(dict(dataset_id=cells[0], name=match[1], data_type=cells[2], expected_bytes=int(cells[3]),
                             source_url=match[2], published_description=cells[4], definition_source='sources/nnlcb-README.md'))
    assert [x['dataset_id'] for x in datasets] == [f'D{i}' for i in range(1, 29)]
    save('nnlcb-published-datasets', datasets)

    pages = (ROOT / 'sources/nnlcb-supplement.txt').read_text().split('\f')
    values = []
    llm = []
    for page_number, page in enumerate(pages, 1):
        match = re.search(r'Table (\d+): Experimental Results Obtained by Running (.+?) on Benchmark Datasets', page)
        if not match:
            continue
        table, algorithm = int(match[1]), match[2].strip()
        for line in page.splitlines():
            cells = line.split()
            if len(cells) != 7 or not re.fullmatch(r'D\d+', cells[0]):
                continue
            try:
                numeric = [float(v) for v in cells[1:]]
            except ValueError:
                continue
            values.append(dict(algorithm=algorithm, dataset_id=cells[0],
                **dict(zip(['CS_reported_MegaBytes', 'CR', 'CT_minutes', 'CPM_reported_MegaBytes', 'DT_minutes', 'DPM_reported_MegaBytes'], numeric)),
                source='sources/nnlcb-supplement.pdf', page=page_number, table=table, environment='published NNLCB'))
        if table == 2:
            current = None
            for line in page.splitlines():
                stripped = line.strip()
                if stripped in ('Cmix', 'LLMZip'):
                    current = stripped
                cells = stripped.split()
                if len(cells) == 7 and re.fullmatch('enwik[3-6]', cells[0]):
                    llm.append(dict(algorithm=current, dataset=cells[0], original_bytes=10**int(cells[0][-1]),
                                    compressed_bytes=int(cells[1]), CR=float(cells[2]), CT_minutes=float(cells[3]),
                                    CPM_reported_MegaBytes=float(cells[4]), DT_minutes=float(cells[5]), DPM_reported_MegaBytes=float(cells[6]),
                                    source='sources/nnlcb-supplement.pdf', page=page_number, table=3, environment='published NNLCB'))
    assert len(values) == 16 * 28 + 15 + 18, len(values)
    assert len(llm) == 8
    assert len({(r['algorithm'], r['dataset_id']) for r in values}) == len(values)
    save('nnlcb-published-per-dataset', values)
    save('nnlcb-published-llmzip-prefixes', llm)

    # Diagnose, never overwrite, discrepancies between rounded published tables
    # and formula-based reconstruction. CS is labelled MegaBytes but CR agrees
    # with a 2**20 byte multiplier, not 10**6, within printed rounding.
    audit = []
    for published in aggregate:
        rows = [r for r in values if r['algorithm'].lower() == published['algorithm'].lower()]
        assert len(rows) == 28, published['algorithm']
        cr = [r['CR'] for r in rows]
        size = [r['CS_reported_MegaBytes'] for r in rows]
        before = {d['dataset_id']: d['expected_bytes'] for d in datasets}
        weighted_after = sum(c*s for c,s in zip(cr,size))/sum(size)
        weighted_before = sum(r['CR']*before[r['dataset_id']] for r in rows)/sum(before.values())
        cv = statistics.pstdev(cr)/statistics.mean(cr)*100
        audit.append(dict(algorithm=published['algorithm'], published_WavgCR=published['WavgCR'],
                          reconstructed_WavgCR_compressed_weights=weighted_after,
                          diagnostic_WavgCR_original_weights=weighted_before,
                          published_CRP=published['CRP'], reconstructed_CRP_equation3=cv,
                          diagnostic_CV_div_sqrt_N=cv/(28**0.5),
                          reconstructed_AvgCR=statistics.mean(cr), published_AvgCR=published['AvgCR'],
                          reconstructed_TotalCT_hours=sum(r['CT_minutes'] for r in rows)/60,
                          published_TotalCT_hours=published['TotalCT_hours']))
    save('nnlcb-reference-reconciliation', audit)
    sources = []
    for p in sorted((ROOT / 'sources').iterdir()):
        if p.is_file():
            sources.append(dict(path=str(p.relative_to(ROOT)), bytes=p.stat().st_size, sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
    (ROOT / 'manifests/external-source-hashes.json').write_text(json.dumps(sources, indent=2)+'\n')
    print(json.dumps(dict(aggregate_rows=len(aggregate), dataset_rows=len(datasets), per_dataset_rows=len(values), prefix_rows=len(llm))))


if __name__ == '__main__':
    main()
