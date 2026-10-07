"""Bounded affinity control for one explicitly selected local pilot manager.

ProcessPool replacements inherit a broad mask and may share the same fast core.
Give each live worker a distinct requested CPU, including its native children.
Never act outside the validated manager's current process tree. Exit when that
manager finishes or the duration expires; this is not a persistent service.
"""
import argparse
import datetime
import json
import os
from pathlib import Path
import time


def identity(pid):
    p=Path('/proc')/str(pid)
    fields=(p/'stat').read_text().rsplit(')',1)[1].split()
    return dict(pid=pid,parent=int(fields[1]),start_ticks=int(fields[19]),command=(p/'cmdline').read_bytes().replace(b'\0',b' ').decode())


def children(pid):
    found=set()
    for task in (Path('/proc')/str(pid)/'task').glob('*'):
        try:found.update(int(x) for x in (task/'children').read_text().split())
        except FileNotFoundError:pass
    return found


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manager',type=int,required=True)
    p.add_argument('--cpus',type=int,nargs='+',required=True);p.add_argument('--seconds',type=int,default=1800)
    p.add_argument('--journal',type=Path,required=True);args=p.parse_args()
    if len(args.cpus)!=len(set(args.cpus)) or not 1<=args.seconds<=3600:raise ValueError('invalid bounded scheduler configuration')
    owner=identity(args.manager)
    if ' -m benchmarks.paq_gp_alphabet_probe ' not in owner['command']:raise ValueError('unexpected pilot manager')
    journal=args.journal.open('x');assigned={};started=time.monotonic();stopped='duration reached'
    def record(obj):journal.write(json.dumps(dict(at=datetime.datetime.now(datetime.timezone.utc).isoformat(),**obj))+'\n');journal.flush()
    record(dict(event='start',manager=owner,cpus=args.cpus,duration_seconds=args.seconds))
    while time.monotonic()-started<args.seconds:
        try:
            now=identity(args.manager)
            if now!=owner:stopped='manager identity changed';break
        except FileNotFoundError:stopped='manager exited';break
        workers={}
        for pid in children(args.manager):
            try:
                info=identity(pid)
                if 'multiprocessing.spawn' in info['command']:workers[pid]=info
            except FileNotFoundError:pass
        assigned={pid:cpu for pid,cpu in assigned.items() if pid in workers}
        if len(workers)>len(args.cpus):raise ValueError('more workers than requested dedicated CPUs')
        for pid,info in sorted(workers.items()):
            if pid not in assigned:assigned[pid]=next(c for c in args.cpus if c not in assigned.values())
            descendants={pid};front=[pid]
            while front:
                parent=front.pop()
                for child in children(parent):
                    try:
                        item=identity(child)
                        if item['parent']==parent and child not in descendants:descendants.add(child);front.append(child)
                    except FileNotFoundError:pass
            for child in descendants:
                for task in (Path('/proc')/str(child)/'task').glob('*'):
                    try:
                        tid=int(task.name);before=sorted(os.sched_getaffinity(tid));after=[assigned[pid]]
                        if before!=after:
                            os.sched_setaffinity(tid,set(after));record(dict(event='pin',worker=info,pid=child,tid=tid,before=before,after=sorted(os.sched_getaffinity(tid))))
                    except ProcessLookupError:pass
        time.sleep(5)
    record(dict(event='stop',reason=stopped));journal.close();print(stopped,flush=True)


if __name__=='__main__':main()
