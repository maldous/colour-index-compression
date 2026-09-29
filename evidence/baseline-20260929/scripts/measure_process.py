#!/usr/bin/env python3
"""Wall/CPU/I/O measurement with process-tree sampling and explicit limits.

No shell is involved. Output files use exclusive creation. os.wait4 measures
child resource usage; a separate sampler records simultaneous RSS summed over
the process tree. The latter can double-count shared pages and miss peaks
between samples, so it is labelled a sampled quantity, not cgroup peak memory.
"""
import datetime
import json
import os
from pathlib import Path
import signal
import shutil
import subprocess
import threading
import time


def machine_state():
    """Small read-only snapshots expose background load, swap and host I/O."""
    paths=('/proc/loadavg','/proc/meminfo','/proc/stat','/proc/diskstats')
    return {path:Path(path).read_text() for path in paths}


def process_tree(root_pid):
    seen, pending, resident = set(), [root_pid], 0
    while pending:
        pid = pending.pop()
        if pid in seen:
            continue
        seen.add(pid)
        entry = Path('/proc') / str(pid)
        try:
            stat = (entry/'stat').read_text().rsplit(')',1)[1].split()
            resident += max(0,int(stat[21])) * os.sysconf('SC_PAGE_SIZE')
            for task in (entry/'task').iterdir():
                pending.extend(int(child) for child in (task/'children').read_text().split())
        except (OSError, ValueError, IndexError):
            pass
    return resident, sorted(seen)


def run(command, cwd, stdout_path, stderr_path, *, timeout_seconds, memory_bytes,
        cpu, sample_seconds=0.05, env_extra=None,disk_path=None,disk_reserve_bytes=0):
    stdout_path, stderr_path = Path(stdout_path), Path(stderr_path)
    if stdout_path.exists() or stderr_path.exists():
        raise FileExistsError('Never overwrite a previous phase log or output')
    record = dict(command=command,cwd=str(cwd),started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  timeout_seconds=timeout_seconds,memory_limit_bytes=memory_bytes,cpu_affinity=[cpu],
                  rss_sample_interval_seconds=sample_seconds,
                  environment_overrides={'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1', **(env_extra or {})},
                  machine_state_before=machine_state(),disk_reserve_bytes=disk_reserve_bytes,
                  disk_path=str(disk_path) if disk_path else None)
    env = dict(os.environ, **record['environment_overrides'])
    done = threading.Event()
    samples = []
    limit = []
    # Native exec wrappers avoid a Python preexec_fn/fork copy inflating the
    # measured peak RSS of small native compressors. Wrapper startup counts.
    invocation = ['taskset','--cpu-list',str(cpu),'prlimit',
                  f'--as={memory_bytes}:{memory_bytes}','--core=0','--',*command]
    record['resource_wrapper_command'] = invocation
    with stdout_path.open('xb') as stdout, stderr_path.open('xb') as stderr:
        start = time.perf_counter()
        proc = subprocess.Popen(invocation,cwd=cwd,stdout=stdout,stderr=stderr,stdin=subprocess.DEVNULL,
                                env=env,start_new_session=True)
        def sample():
            while not done.is_set():
                elapsed = time.perf_counter()-start
                rss, family = process_tree(proc.pid)
                samples.append((elapsed,rss,len(family)))
                why = 'TIMEOUT' if elapsed >= timeout_seconds else 'RESOURCE LIMIT' if rss > memory_bytes else None
                if disk_path is not None and shutil.disk_usage(disk_path).free<disk_reserve_bytes:
                    why='RESOURCE LIMIT';record['disk_reserve_reached']=True
                if why and not limit:
                    limit.append(why)
                    try: os.killpg(proc.pid,signal.SIGKILL)
                    except ProcessLookupError: pass
                done.wait(sample_seconds)
        thread = threading.Thread(target=sample,daemon=True)
        thread.start()
        _, status, usage = os.wait4(proc.pid,0)
        elapsed = time.perf_counter()-start
        proc.returncode = os.waitstatus_to_exitcode(status)
        done.set(); thread.join()
    record.update(finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  exit_code=proc.returncode,status=limit[0] if limit else 'COMPLETED' if proc.returncode==0 else 'FAILED',
                  wall_seconds=elapsed,user_seconds=usage.ru_utime,system_seconds=usage.ru_stime,
                  cpu_utilization_percent=100*(usage.ru_utime+usage.ru_stime)/elapsed,
                  kernel_max_single_process_rss_bytes=usage.ru_maxrss*1024,
                  sampled_process_tree_peak_rss_bytes=max((s[1] for s in samples),default=0),
                  input_blocks=usage.ru_inblock,output_blocks=usage.ru_oublock,
                  minor_faults=usage.ru_minflt,major_faults=usage.ru_majflt,
                  voluntary_context_switches=usage.ru_nvcsw,involuntary_context_switches=usage.ru_nivcsw,
                  samples=samples,machine_state_after=machine_state())
    return record
