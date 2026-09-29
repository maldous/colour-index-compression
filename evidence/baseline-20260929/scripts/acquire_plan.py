#!/usr/bin/env python3
"""Execute pinned public source acquisitions; preserves all failures for review."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import sys


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan',type=Path)
    parser.add_argument('storage',type=Path)
    parser.add_argument('--jobs',type=int,default=2)
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    def acquire(row):
        command=[sys.executable,str(root/'scripts/acquire.py'),row['url'],str(args.storage/row['filename']),
                 '--record',str(root/'raw'/('acquire-'+row['dataset_id']+'.json'))]
        for key in ('bytes','sha256','sha1','md5'):
            if key in row:command += ['--'+key,str(row[key])]
        result=subprocess.run(command,capture_output=True,text=True)
        output=dict(dataset_id=row['dataset_id'],command=command,exit_code=result.returncode,stdout=result.stdout,stderr=result.stderr)
        (root/'raw'/('acquire-'+row['dataset_id']+'-command.json')).write_text(json.dumps(output,indent=2)+'\n')
        print(row['dataset_id'],result.returncode,flush=True)
        return output
    with ThreadPoolExecutor(args.jobs) as pool:
        list(pool.map(acquire,json.loads(args.plan.read_text())))


if __name__=='__main__':main()
