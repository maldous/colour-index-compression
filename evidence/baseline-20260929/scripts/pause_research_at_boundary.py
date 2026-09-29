"""Pause explicitly identified CIX queues after their current file completes.

No signal is sent to the current atomic experiment. After its verified result
exists, stop the queue and any newly started successor without deleting state.
The recorded process start times protect against PID reuse. Resume is explicit.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import signal
import time


def info(pid):
    try:
        raw=Path(f'/proc/{pid}/stat').read_text();tail=raw[raw.rindex(')')+2:].split()
        return dict(pid=pid,ppid=int(tail[1]),start_ticks=int(tail[19]),state=tail[0],
                    command=Path(f'/proc/{pid}/cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace'))
    except (FileNotFoundError,ProcessLookupError):return None


def descendants(pid):
    processes=[info(int(p.name)) for p in Path('/proc').iterdir() if p.name.isdigit()]
    found={pid};changed=True
    while changed:
        changed=False
        for p in processes:
            if p and p['ppid'] in found and p['pid'] not in found:found.add(p['pid']);changed=True
    return [p for p in processes if p and p['pid'] in found]


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--plan',type=Path,required=True)
    parser.add_argument('--state',type=Path,required=True);parser.add_argument('--resume',action='store_true')
    args=parser.parse_args()
    if args.resume:
        state=json.loads(args.state.read_text())
        for row in state['queues']:
            for old in reversed(row.get('stopped_processes',[])):
                current=info(old['pid'])
                if current and current['start_ticks']==old['start_ticks']:os.kill(old['pid'],signal.SIGCONT)
        state['resumed_at']=datetime.now(timezone.utc).isoformat();args.state.write_text(json.dumps(state,indent=2)+'\n');return
    queues=json.loads(args.plan.read_text())['queues'];state=dict(queues=queues,created_at=datetime.now(timezone.utc).isoformat())
    while any(not row.get('checkpoint_complete') for row in queues):
        for row in queues:
            if row.get('checkpoint_complete'):continue
            current=info(row['pid'])
            if not current or current['start_ticks']!=row['start_ticks']:
                row.update(checkpoint_complete=True,queue_exited=True);continue
            marker=Path(row['verified_result'])
            if not marker.exists():continue
            proof=json.loads(marker.read_text())
            if not proof.get('round_trip'):raise ValueError('current experiment did not verify')
            os.kill(row['pid'],signal.SIGSTOP)
            stopped=descendants(row['pid'])
            for process in stopped:
                current=info(process['pid'])
                if current and current['start_ticks']==process['start_ticks']:
                    try:os.kill(process['pid'],signal.SIGSTOP)
                    except ProcessLookupError:pass
            row.update(checkpoint_complete=True,stopped_processes=stopped,paused_at=datetime.now(timezone.utc).isoformat())
        state['updated_at']=datetime.now(timezone.utc).isoformat()
        temp=args.state.with_suffix('.tmp');temp.write_text(json.dumps(state,indent=2)+'\n');temp.replace(args.state)
        time.sleep(1)


if __name__=='__main__':main()
