"""Privileged read-only process check. Report only target matches, no arguments."""
import datetime
import json
import os
from pathlib import Path
from verify import TARGET

needle = os.fsencode(str(TARGET))
matches = []
errors = []
count = 0
for proc in Path('/proc').iterdir():
    if not proc.name.isdigit():
        continue
    pid = int(proc.name)
    try:
        count += 1
        for name in ['cwd', 'root', 'exe']:
            try:
                value = os.fsencode(os.readlink(proc/name))
                if value == needle or value.startswith(needle+b'/'):
                    matches.append({'pid':pid,'kind':name})
            except FileNotFoundError:
                pass
        for fd in (proc/'fd').iterdir():
            try:
                value = os.fsencode(os.readlink(fd))
                if value == needle or value.startswith(needle+b'/'):
                    matches.append({'pid':pid,'kind':'fd'})
            except FileNotFoundError:
                pass
        if needle in (proc/'maps').read_bytes():
            matches.append({'pid':pid,'kind':'maps'})
        if needle in (proc/'cmdline').read_bytes():
            matches.append({'pid':pid,'kind':'command-reference'})
    except FileNotFoundError:
        continue
    except (PermissionError, OSError) as error:
        errors.append({'pid':pid,'errno':error.errno})
result = {'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'target':str(TARGET),'processes_checked':count,'target_matches':matches,'inspection_errors':errors}
print(json.dumps(result,indent=2))
raise SystemExit(0 if not matches and not errors else 1)
