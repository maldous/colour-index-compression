#!/usr/bin/env python3
"""One predeclared replication wave for positive first domain configurations."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from benchmarks import domain_research as research

AREA = research.ROOT / research.REL


def prepare():
    plan = AREA / 'replication-v1.json'
    if plan.exists():
        return json.loads(plan.read_text())
    pilot = json.loads((AREA / 'pilot-v1.json').read_text())
    prior = json.loads(Path(pilot['waves'][0][0]).read_text())
    closure = list(prior['expected_build_sha256'])
    specs = [
        ('molecular', 'assets/pubchem-2d-replication/pubchem-2d-cids-176-180-239-280-6276-6322-784-887.sdf', 'original', 0),
        ('molecular', 'assets/pubchem-2d-replication/pubchem-2d-cids-176-180-239-280-6276-6322-784-887.sdf', 'hydrogen_slots_v1', 2),
        ('numeric', 'assets/noaa-water-level-202401-seattle.csv', 'original', 4),
        ('numeric', 'assets/noaa-water-level-202401-seattle.csv', 'numeric-delta-columns-v1', 6),
    ]
    cells = []
    for domain, asset, variant, cpu in specs:
        cell = research.prepare(AREA / asset, domain, variant, 'paq', closure, cpu, 300, owner='/root/domain_replication')
        assert cell['expected_build_sha256'] == prior['expected_build_sha256'], 'replication must use unchanged source closure'
        cells.append(str(AREA / 'cells' / (cell['cell_id'] + '.json')))
    value = {'schema': 1, 'cells': cells, 'status': 'PREDECLARED_NOT_RUN',
             'selection': 'Retest two positive pilot configurations on separately predeclared new assets; no configuration change or outcome screening.',
             'source_commit': pilot['source_commit'], 'protocols': ['molecular-replication-plan.json', 'numerical-replication-plan.json'],
             'repetitions': 1, 'resource_limits': 'four physical cores / 12 GB RAM / 4 GB temporary / zero swap; 300 seconds combined per cell',
             'promotion': 'Require repeat complete-size savings and independent exact restoration; unsupported input or loss remains evidence with no substitution.'}
    research.immutable(plan, value)
    return value


def run():
    plan = json.loads((AREA / 'replication-v1.json').read_text())
    rows = research.run_wave(plan['cells'])
    research.immutable(AREA / 'replication-v1-terminal.json', {'rows': rows})
    research.report()
    return rows


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('prepare', 'run'))
    args = parser.parse_args()
    print(json.dumps(prepare() if args.operation == 'prepare' else run(), sort_keys=True))
