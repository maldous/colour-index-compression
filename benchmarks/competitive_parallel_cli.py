"""Bounded local parallel execution for byte-identical CIX work.

This command deliberately does not replace ``competitive_cli`` or the frozen
Hutter baseline.  It is an opt-in research tool: it retains whole-input
candidates and serial physical-size selection, but may evaluate independent
candidates on separate CPUs.  ``joint`` parallelises independent bounded PPM
blocks while producing the exact normal joint frame.  Neither profile splits a
PAQ stream, and therefore neither makes PAQ8px's adaptive coder multicore.
"""
import argparse
import json
import os
import resource
import time
from pathlib import Path

from benchmarks import competitive_codec as codec


def parse_cpus(value):
    result=[]
    for item in value.split(','):
        if '-' in item:
            first,last=item.split('-',1)
            result.extend(range(int(first),int(last)+1))
        elif item:
            result.append(int(item))
    if not result or len(result)!=len(set(result)):
        raise argparse.ArgumentTypeError('CPUs must be a non-empty, non-overlapping list/range')
    return tuple(result)


def memory_bound(source_bytes, workers, budget, per_worker, paq_worker):
    # The input itself is copied into each spawned candidate process.  PAQ has
    # a separately conservative working-set allowance; only one PAQ candidate
    # may exist in this ordinary portfolio.
    generic=workers*(source_bytes+per_worker)
    paq=max(0,paq_worker-(source_bytes+per_worker))
    required=generic+paq
    if required>budget:
        raise ValueError('requested workers exceed the declared memory budget: '
                         f'need at least {required} bytes, budget is {budget}')
    return required


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation',choices=('encode','decode'))
    parser.add_argument('source',type=Path)
    parser.add_argument('destination',type=Path)
    parser.add_argument('--profile',choices=('ordinary','joint'),default='ordinary')
    parser.add_argument('--workers',type=int)
    parser.add_argument('--cpus',type=parse_cpus,
                        help='dedicated local CPUs, e.g. 16-31; defaults to current affinity')
    parser.add_argument('--memory-budget-bytes',type=int,default=24_000_000_000)
    parser.add_argument('--per-worker-bytes',type=int,default=1_500_000_000)
    parser.add_argument('--paq-worker-bytes',type=int,default=6_000_000_000)
    parser.add_argument('--paq',choices=('none','v215-8','v216-8'),default='none')
    args=parser.parse_args()
    if args.destination.exists():
        parser.error('destination already exists; choose a new path')
    if min(args.memory_budget_bytes,args.per_worker_bytes,args.paq_worker_bytes)<=0:
        parser.error('memory bounds must be positive')
    data=args.source.read_bytes()
    started=time.perf_counter()
    verified=False
    if args.operation=='decode':
        output=codec.decode(data)
        selection=None
        cpus=[]
        memory_required=None
    else:
        if args.workers is None:
            parser.error('--workers is required for parallel encoding')
        cpus=args.cpus if args.cpus is not None else tuple(sorted(os.sched_getaffinity(0)))
        if args.workers>len(cpus):
            parser.error('workers cannot exceed requested CPUs')
        if args.profile=='ordinary':
            policy=None if args.paq=='none' else (args.paq[:4],'-8')
            memory_required=memory_bound(len(data),args.workers,args.memory_budget_bytes,
                                         args.per_worker_bytes,args.paq_worker_bytes if policy else 0)
            output,selection=codec.encode_parallel(data,workers=args.workers,cpus=cpus,paq=policy)
        else:
            if args.paq!='none':
                parser.error('--paq applies only to the ordinary candidate profile')
            from benchmarks.joint_parallel_encode import encode as encode_joint
            output=encode_joint(data,jobs=args.workers,cpus=cpus)
            selection=dict(selected='joint-parallel-blocks',trials=[])
            # The bounded work queue holds at most one block and 64 KiB history
            # per worker; this bound does not include native allocator state.
            memory_required=args.workers*(1048576+65536)
    elapsed=time.perf_counter()-started
    if args.operation=='encode':
        restored=codec.decode(output)
        if restored!=data:
            raise ValueError('parallel archive failed exact restoration')
        verified=True
    with args.destination.open('xb') as out:
        out.write(output)
    print(json.dumps(dict(operation=args.operation,profile=args.profile,
        source_bytes=len(data),output_bytes=len(output),source_sha256=codec.sha(data),
        output_sha256=codec.sha(output),round_trip=verified,seconds=elapsed,
        workers=args.workers,cpus=list(cpus),memory_budget_bytes=args.memory_budget_bytes,
        conservative_memory_required_bytes=memory_required,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        selection=selection,
        limitation='PAQ is one sequential adaptive candidate; this command does not parallelize it or alter its stream. The joint profile is byte-identical to joint_bounded, not the p26 portfolio.'),indent=2))


if __name__=='__main__':
    main()
