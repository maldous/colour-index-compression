"""Root dispatch of already-frozen sequential performance cells."""
import json
from pathlib import Path
import subprocess
import sys

AREA=Path(__file__).resolve().parent
cells=sys.argv[1:]
assert cells
for cell in cells:
    spec=AREA/'jobs'/('perf-'+cell.lower()+'-v1.json')
    assert spec.is_file()
    print('START '+cell, flush=True)
    with (AREA/('perf-'+cell.lower()+'-launch.txt')).open('x') as output:
        result=subprocess.run([sys.executable,str(AREA/'schedule.py'),str(spec)],stdout=output)
    print('FINISH '+cell+' exit '+str(result.returncode),flush=True)
    if result.returncode and not cell.startswith('P'):
        raise SystemExit(result.returncode)
