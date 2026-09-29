#!/usr/bin/env python3
"""Independent Decimal checks. Never repair evidence to fit a headline."""
import argparse
from decimal import Decimal,localcontext
import json
from pathlib import Path


def check_local(rows):
    checked=0
    for row in rows:
        if row.get('status')!='VERIFIED':continue
        if row['original_sha256']!=row['decompressed_sha256']:
            raise AssertionError('Hash mismatch in a reported success')
        original=Decimal(row['original_bytes']);compressed=Decimal(row['compressed_bytes'])
        assert original>0 and compressed>0
        expected=dict(ratio=original/compressed,compressed_percent=100*compressed/original,
                      saving_percent=100*(1-compressed/original),bits_per_input_byte=8*compressed/original,
                      compression_MiB_s=original/1048576/Decimal(str(row['compression_seconds'])),
                      decompression_MiB_s=original/1048576/Decimal(str(row['decompression_seconds'])))
        for key,value in expected.items():
            if key not in row:raise AssertionError('Missing metric '+key)
            if abs(Decimal(str(row[key]))-value)>max(Decimal('1e-10'),abs(value)*Decimal('1e-12')):
                raise AssertionError(f'{row.get("dataset_id")}/{row.get("algorithm")}: {key} disagrees')
        checked+=1
    return checked


def check_reference(root):
    rows=json.loads((root/'tables/nnlcb-published-per-dataset.json').read_text())
    size={d['dataset_id']:Decimal(d['expected_bytes']) for d in json.loads((root/'tables/nnlcb-published-datasets.json').read_text())}
    disagreements=[]; truncation_compatible=0
    for row in rows:
        cs=Decimal(str(row['CS_reported_MegaBytes']));cr=Decimal(str(row['CR']))
        low=(cs-Decimal('.0005'))*1048576*8/size[row['dataset_id']]
        high=(cs+Decimal('.0005'))*1048576*8/size[row['dataset_id']]
        # Source display may truncate instead of rounding. Do not label this
        # distinction as a substantive source error without author evidence.
        wide_low=(cs-Decimal('.0005'))*1048576*8/size[row['dataset_id']]
        wide_high=(cs+Decimal('.001'))*1048576*8/size[row['dataset_id']]
        if wide_high>=cr-Decimal('.0005') and wide_low<=cr+Decimal('.001'):
            truncation_compatible+=1
        if high<cr-Decimal('.0005') or low>cr+Decimal('.0005'):
            disagreements.append(dict(algorithm=row['algorithm'],dataset_id=row['dataset_id'],
                published_CS_MegaBytes=row['CS_reported_MegaBytes'],published_CR=row['CR'],
                reconstructed_CR_interval_MiB=[str(low),str(high)],page=row['page']))
    return dict(rows=len(rows),CS_and_CR_compatible_with_binary_MiB=len(rows)-len(disagreements),
                compatible_allowing_rounding_or_truncation=truncation_compatible,
                disagreements_under_nearest_rounding=disagreements,note='Original tables are unchanged. Display rounding mode is unspecified. Nearest-rounding discrepancies alone are not treated as substantive benchmark errors; a second count allows truncation.')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);args=p.parse_args()
    with localcontext() as context:
        context.prec=50
        n=check_local(json.loads((args.root/'results.json').read_text()))
        result=dict(local_verified_rows_checked=n,published_reference_check=check_reference(args.root))
    (args.root/'tables/arithmetic-audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
