#!/usr/bin/env python3
"""Capture benchmark-relevant machine state; never dump credentials/environment."""
import argparse
import datetime
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess


def command(argv):
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=20)
        return dict(command=argv, exit_code=p.returncode, stdout=p.stdout, stderr=p.stderr)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return dict(command=argv, error=str(exc))


def capture(storage):
    files = ['/proc/meminfo','/proc/loadavg','/proc/swaps','/etc/os-release',
             '/sys/class/dmi/id/sys_vendor','/sys/class/dmi/id/product_name',
             '/sys/class/dmi/id/product_version','/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor',
             '/sys/devices/system/cpu/intel_pstate/no_turbo']
    out = dict(captured_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
               platform=platform.platform(), python=platform.python_version(),
               cpu_affinity=sorted(os.sched_getaffinity(0)),
               filesystem_path=str(storage.absolute()), disk_usage_bytes=dict(zip(('total','used','free'), shutil.disk_usage(storage))),
               files={f:Path(f).read_text() for f in files if Path(f).is_file() and os.access(f,os.R_OK)})
    out['commands'] = [command(c) for c in [
        ['lscpu','--json'], ['lsblk','-J','-o','NAME,MODEL,SIZE,ROTA,TYPE,FSTYPE,MOUNTPOINTS'],
        ['findmnt','-J','-T',str(storage)], ['uname','-a'], ['g++','--version'],
        ['cmake','--version'], ['ldd','--version'], ['nvidia-smi','--query-gpu=name,memory.total,memory.used,utilization.gpu','--format=csv']]]
    out['cache_policy'] = 'Warm source pre-read for every measured phase; no global cache drop. Larger-than-RAM inputs cannot be fully cached and are labelled capacity-limited.'
    out['background_processes'] = command(['ps','-eo','pid,ppid,stat,pcpu,pmem,comm','--sort=-pcpu'])
    return out


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path)
    parser.add_argument('--storage',type=Path,default=Path.cwd())
    args=parser.parse_args()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(capture(args.storage),indent=2)+'\n')
