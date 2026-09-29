#!/usr/bin/env python3
"""Controlled single-run harness. Scheduling/aggregation are separate steps.

Every invocation has a fresh work directory and a neutral input basename.
The source is hard-linked without changing its bytes; no compressed cache is
reused. All command logs and failures remain under the run directory.
"""
import argparse
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

from measure_process import run

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = Path(os.environ.get('CIX_BASELINE_RUNTIME','/home/user/src/cix-baseline-runtime-20260929'))
PYTHON = os.environ.get('CIX_BASELINE_PYTHON','/home/user/src/cix-baseline-tools/python-venv/bin/python')
CIX_SHA = 'f26d32836c15cb1a5e37ebfddd5826c4b33ff8a6'


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(8 << 20), b''):
            h.update(block)
    return h.hexdigest()


def warm(path):
    with Path(path).open('rb') as f:
        while f.read(8 << 20):
            pass


def commands(algorithm, source, archive, restored, binaries):
    binary = binaries[algorithm]['path'] if algorithm != 'CIX' else PYTHON
    if algorithm == 'gzip':
        return [binary,'-9','-n','-c',str(source)], [binary,'-d','-c',str(archive)], True, True
    if algorithm == 'bzip2':
        return [binary,'-9','-c',str(source)], [binary,'-d','-c',str(archive)], True, True
    if algorithm == 'zstd':
        return [binary,'--ultra','-22','--long=27','-T1','-c',str(source)], [binary,'-d','-T1','-c',str(archive)], True, True
    if algorithm == 'xz':
        return [binary,'-9e','-T1','-c',str(source)], [binary,'-d','-T1','-c',str(archive)], True, True
    if algorithm == 'brotli':
        return [binary,'-q','11','-w','24','-c',str(source)], [binary,'-d','-c',str(archive)], True, True
    if algorithm == 'zpaq':
        # Always a new self-contained archive. Relative neutral member name.
        return [binary,'add',str(archive),source.name,'-method','5','-threads','1'], [binary,'extract',str(archive),source.name,'-to',str(restored),'-threads','1'], False, False
    if algorithm == 'paq8px':
        return [binary,'-12L','-simd','AVX2',str(source),str(archive)], [binary,'-d','-simd','AVX2',str(archive),str(restored)], False, False
    if algorithm == 'CIX':
        return [PYTHON,'-m','benchmarks.competitive_cli','encode',str(source),str(archive)], [PYTHON,'-m','benchmarks.competitive_cli','decode',str(archive),str(restored)], False, False
    raise ValueError(algorithm)


def isolated(command, directory, cix):
    """Mount only decoder/runtime files and this run, with no network or corpus."""
    venv = Path(PYTHON).parent.parent
    tools = Path('/home/user/src/cix-baseline-tools')
    mappings = [(str(RUNTIME),'/codec'),(str(venv),'/venv'),(str(tools),'/tools'),(str(directory),'/work')]
    def guest(arg):
        for host, target in mappings:
            if arg==host or arg.startswith(host+'/'):
                return target+arg[len(host):]
        return arg
    temporary=directory/'temporary'
    temporary.mkdir(mode=0o700,exist_ok=False)
    wrapper = ['bwrap','--unshare-user','--unshare-pid','--unshare-net','--die-with-parent',
               '--ro-bind','/usr','/usr','--symlink','usr/bin','/bin',
               '--ro-bind','/lib','/lib','--ro-bind','/lib64','/lib64',
               '--ro-bind','/etc/ld.so.cache','/etc/ld.so.cache',
               '--proc','/proc','--dev','/dev','--bind',str(temporary),'/tmp',
               '--ro-bind',str(RUNTIME),'/codec','--ro-bind',str(venv),'/venv',
               '--ro-bind',str(tools),'/tools','--bind',str(directory),'/work',
               '--chdir','/codec' if cix else '/work','--']
    timing_format='{"elapsed_seconds":%e,"user_seconds":%U,"system_seconds":%S,"peak_rss_kib":%M,"input_blocks":%I,"output_blocks":%O,"exit_code":%x}'
    return wrapper+['/usr/bin/time','-f',timing_format,'-o','/work/process-resources.json','--']+[guest(str(arg)) for arg in command]


def attach_inner_resources(timing, directory):
    """Namespace supervisor rusage excludes the real workload on this kernel.

Measure that workload with GNU time inside its namespace, retaining outer wall
and all outer supervisor data separately. Do not report supervisor RSS as CIX.
"""
    path=directory/'process-resources.json'
    if not path.exists():
        if timing['status']=='COMPLETED':raise ValueError('Missing inner resource measurement')
        timing['inner_resources_unavailable']='Workload did not exit cleanly before limit or namespace failure'
        return timing
    raw=path.read_text().splitlines()
    inner=next((json.loads(line) for line in reversed(raw) if line.startswith('{')),None)
    if inner is None:
        if timing['status']!='COMPLETED':
            timing['inner_resources_unavailable']='Workload or GNU time terminated before its final resource record; retain the observed timeout/failure and outer samples'
            return timing
        raise ValueError('Malformed GNU time resource log')
    timing['inner_process_resources']=inner
    for key in ('user_seconds','system_seconds','kernel_max_single_process_rss_bytes','cpu_utilization_percent','input_blocks','output_blocks'):
        timing['outer_namespace_supervisor_'+key]=timing[key]
    timing.update(user_seconds=inner['user_seconds'],system_seconds=inner['system_seconds'],
                  kernel_max_single_process_rss_bytes=inner['peak_rss_kib']*1024,
                  cpu_utilization_percent=100*(inner['user_seconds']+inner['system_seconds'])/timing['wall_seconds'],
                  input_blocks=inner['input_blocks'],output_blocks=inner['output_blocks'])
    return timing


def quiet_research():
    active = []
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():continue
        try:
            cmd = (p/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
            state = (p/'stat').read_text().rsplit(')',1)[1].split()[0]
            executable=(p/'exe').resolve().name
            research_cwd = str((p/'cwd').resolve()) == '/home/user/src/colour-index-compression'
            workload=(executable.startswith('python') and ('-m benchmarks.' in cmd or '/benchmarks/' in cmd)) or executable.startswith('paq8px')
            if (research_cwd or '/home/user/src/colour-index-compression/' in cmd) and workload and state not in ('T','t','Z'):
                # The harness itself may reference the qualified Python path;
                # only prior research process command roles match these tests.
                if '-m benchmarks.competitive_cli' not in cmd and 'run_benchmark.py' not in cmd:
                    active.append(dict(pid=int(p.name),state=state,command=cmd))
        except (OSError,ValueError,IndexError):pass
    return active


def rotate_source_if_needed(dataset, original, directory, required, result):
    """Free only our reproducible XML materialisation, keeping its public source.

    This is a storage operation after compression, not a source transformation.
    The restored bytes must regain the same path/hash before any next run.
    """
    if shutil.disk_usage(directory).free>=required:return False
    sources=dataset.get('source_artifacts',[])
    if dataset.get('dataset_id')!='WIKIPEDIA-20260901' or len(sources)!=1:return False
    source=sources[0];compressed=Path(source['destination'])
    if source['status']!='VERIFIED DOWNLOAD' or not compressed.is_file():return False
    if compressed==original or compressed.stat().st_size!=source['bytes']:return False
    if digest(compressed)!=source['sha256']:raise ValueError('Canonical recovery source changed')
    result['rolling_source_storage']=dict(original=str(original),original_sha256=dataset['sha256'],
        canonical_recovery_source=str(compressed),source_sha256=source['sha256'],
        reason='Retain verified public bzip2 source, remove only its reproducible XML materialisation to make room for the complete normal decoded output. Reconstitute the exact same SHA-256 before the next compressor.')
    original.unlink()
    return True


def cleanup_payloads(directory, result):
    """Retain logs/hashes, never leave large failed payloads to bias later tools."""
    source=directory/'input.bin'
    if source.exists():source.unlink()  # neutral hardlink, never the source path
    large=result.get('original_bytes',0)>100_000_000
    removed=[]
    for scratch in [directory/'temporary',directory/'decoder-only/temporary']:
        if scratch.exists():
            files=[p for p in scratch.rglob('*') if p.is_file() and not p.is_symlink()]
            removed.extend(dict(path=str(p.relative_to(directory)),bytes=p.stat().st_size,sha256=digest(p),role='disposable temporary payload') for p in files)
            shutil.rmtree(scratch)
    if large:
        for relative in ('archive.bin','archive.zpaq','decoder-only/archive.bin','decoder-only/archive.zpaq','decoder-only/restored.bin'):
            p=directory/relative
            if p.is_file():
                removed.append(dict(path=relative,bytes=p.stat().st_size,sha256=digest(p),role='large payload retained by hash and command; verification status remains in result'))
                p.unlink()
    if removed:
        (directory/'payload-retention.json').write_text(json.dumps(removed,indent=2)+'\n')


def benchmark(dataset, algorithm, directory, *, repetition, warmup, smoke=False):
    directory = directory.absolute()
    directory.mkdir(parents=True,exist_ok=False)
    result = dict(dataset_id=dataset['dataset_id'],dataset_name=dataset.get('name',dataset['dataset_id']),
                  algorithm=algorithm,profile='high-compression-v1',repetition=repetition,warmup=warmup,
                  smoke_only=smoke,cix_commit=CIX_SHA if algorithm=='CIX' else None,
                  started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  input_manifest=dataset,status='STARTED')
    result_path = directory/'result.json'
    def persist():result_path.write_text(json.dumps(result,indent=2)+'\n')
    persist()
    measurement_lock=None
    rotated=False
    original=None
    try:
        # A single lock covers all normal harness invocations in this evidence
        # checkout, including direct CLI calls and the resumable suite.
        if not smoke:
            measurement_lock=(ROOT/'raw/measurement.lock').open('a')
            # R&D uses this same exclusive lock. Waiting for its atomic batch is
            # outside all phase timers and must not become a failed measurement.
            fcntl.flock(measurement_lock,fcntl.LOCK_EX)
        active = quiet_research()
        if active and not smoke:
            result.update(status='NOT STARTED',failure_reason='Research has not reached a quiet checkpoint',active_research=active)
            return result
        original = Path(dataset['path']).absolute()
        actual_hash = digest(original)
        actual_size = original.stat().st_size
        assert actual_hash == dataset['sha256'] and actual_size == dataset['obtained_bytes'], 'Input manifest mismatch'
        result.update(original_bytes=actual_size,original_sha256=actual_hash)
        free = shutil.disk_usage(directory).free
        # Check restoration separately after actual archive size is known.
        needed = min(actual_size,1<<30) + (5 << 30)
        if free < needed:
            result.update(status='RESOURCE LIMIT',failure_reason=f'Disk preflight: {free} free bytes; {needed} required for initial output and 5 GiB reserve. A live guard also enforces the reserve.')
            return result
        binaries = {r['algorithm']:r for r in json.loads((ROOT/'manifests/compressor-binaries.json').read_text())}
        if algorithm != 'CIX':
            assert digest(binaries[algorithm]['path']) == binaries[algorithm]['sha256'], 'Compressor binary changed'
            result['compressor_identity'] = binaries[algorithm]
        else:
            from freeze_python_environment import snapshot
            python_manifest=json.loads((ROOT/'manifests/frozen-python-environment.json').read_text())
            assert digest(PYTHON)==python_manifest['python_binary_sha256'], 'Python interpreter changed'
            assert snapshot(Path(PYTHON).parent.parent)==python_manifest['files'], 'Frozen Python dependencies changed'
            manifest = json.loads((RUNTIME/'SOURCE-MANIFEST.json').read_text())
            assert manifest['source_revision']==CIX_SHA
            for name, sha in manifest['files'].items():assert digest(RUNTIME/name)==sha, 'Frozen source changed: '+name
            build = json.loads((ROOT/'manifests/cix-fresh-build.json').read_text())
            for name, sha in build['binaries'].items():assert digest(RUNTIME/name)==sha, 'Frozen binary changed: '+name
            result['compressor_identity'] = build
        source = directory/'input.bin'
        os.link(original, source)
        archive = directory/('archive.zpaq' if algorithm=='zpaq' else 'archive.bin')
        decoder_directory = directory/'decoder-only'
        decoder_directory.mkdir()
        restored = decoder_directory/'restored.bin'
        enc, dec, enc_stdout, dec_stdout = commands(algorithm,source,archive,restored,binaries)
        cwd = RUNTIME if algorithm=='CIX' else directory
        extra = {'CUDA_VISIBLE_DEVICES':'','PYTHONNOUSERSITE':'1','PYTHONPATH':'','PYTHONDONTWRITEBYTECODE':'1'}
        phase_options = dict(timeout_seconds=36*3600,memory_bytes=48<<30,cpu=2,env_extra=extra,disk_path=directory,disk_reserve_bytes=5<<30)
        # A smoke invocation tests plumbing only; it never contributes to results.
        if smoke and algorithm=='paq8px':enc[1]='-1'
        if smoke:phase_options['timeout_seconds']=180
        enc=isolated(enc,directory,algorithm=='CIX')
        decoder_archive=decoder_directory/archive.name
        dec=[str(decoder_archive) if arg==str(archive) else arg for arg in dec]
        dec=isolated(dec,decoder_directory,algorithm=='CIX')
        result.update(compression_command=enc,decompression_command=dec,
                      cache='Sequential pre-read immediately before each phase; no global cache drop',
                      memory_definition='Kernel wait4 ru_maxrss: largest process RSS, bytes; process-tree summed RSS sampled separately every 50ms')
        warm(source)
        encoding = attach_inner_resources(run(enc,cwd,archive if enc_stdout else directory/'encode.stdout.log',directory/'encode.stderr.log',**phase_options),directory)
        (directory/'encode.timing.json').write_text(json.dumps(encoding,indent=2)+'\n')
        result['compression'] = {k:v for k,v in encoding.items() if k!='samples'}
        if encoding['status']!='COMPLETED':
            result.update(status=encoding['status'],failure_reason='Compression did not complete; see raw phase log')
            return result
        if not archive.is_file():raise ValueError('No physical archive produced')
        result.update(compressed_bytes=archive.stat().st_size,compressed_sha256=digest(archive))
        # Neutral source link must be gone before rotating a very large source.
        source.unlink()
        rotated=rotate_source_if_needed(dataset,original,directory,actual_size+(5<<30),result)
        persist()
        if shutil.disk_usage(directory).free < actual_size+(5<<30):
            result.update(status='RESOURCE LIMIT',failure_reason='Compression completed but insufficient disk remains for a full restored file plus5GiB reserve; unverified archive is not a ranked result')
            return result
        # The decoder's namespace contains the archive, never the original.
        os.link(archive,decoder_archive)
        warm(archive)
        decoding = attach_inner_resources(run(dec,cwd,restored if dec_stdout else directory/'decode.stdout.log',directory/'decode.stderr.log',**phase_options),decoder_directory)
        (directory/'decode.timing.json').write_text(json.dumps(decoding,indent=2)+'\n')
        result['decompression'] = {k:v for k,v in decoding.items() if k!='samples'}
        if decoding['status']!='COMPLETED':
            result.update(status=decoding['status'],failure_reason='Decompression did not complete; see raw phase log')
            return result
        if not restored.is_file():raise ValueError('No restored file produced')
        result['decompressed_sha256'] = digest(restored)
        result['restored_bytes'] = restored.stat().st_size
        if result['decompressed_sha256'] != actual_hash or result['restored_bytes']!=actual_size:
            result.update(status='HASH MISMATCH',failure_reason='SHA-256 or length mismatch')
            return result
        result.update(status='VERIFIED',verification='SHA-256 and exact byte count')
        # Only this verified run's disposable restored output and neutral input
        # hard link are removed. The original dataset is preserved; large
        # verified archives follow the disclosed disk-retention policy below.
        if rotated:
            assert not original.exists()
            restored.rename(original)
            result['rolling_source_storage']['restored_as_canonical_input']=True
        else:restored.unlink()
        decoder_archive.unlink()
        result['archive_retained'] = actual_size <= 100_000_000
        if not result['archive_retained']:
            archive.unlink()
            result['archive_retention_note']='Verified archive removed after hashing and full reconstruction to conserve disk. Exact command and source hashes permit regeneration; raw measurements remain preserved.'
        return result
    except Exception as exc:
        result.update(status='FAILED',failure_reason=repr(exc))
        return result
    finally:
        try:
            cleanup_payloads(directory,result)
            if rotated and original is not None and not original.exists():
                # A failed decoder must not deprive later tools of their input.
                # Recovery from the pinned Wikimedia download is outside timers.
                from prepare_public_inputs import prepare_wikipedia
                restored_input=prepare_wikipedia(original.parent.parent,False)
                if restored_input['sha256']!=dataset['sha256']:raise ValueError('Canonical source recovery hash mismatch')
                result['rolling_source_storage']['recovered_from_public_source_after_failure']=True
        except Exception as exc:
            result['storage_recovery_error']=repr(exc)
        result['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
        persist()
        if measurement_lock is not None:measurement_lock.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset-manifest',type=Path,required=True)
    parser.add_argument('--dataset-id',required=True)
    parser.add_argument('--algorithm',choices=['gzip','bzip2','zstd','xz','brotli','zpaq','paq8px','CIX'],required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--repetition',type=int,default=1)
    parser.add_argument('--warmup',action='store_true')
    parser.add_argument('--smoke-only',action='store_true')
    args=parser.parse_args()
    rows=json.loads(args.dataset_manifest.read_text())
    data=next(d for d in rows if d['dataset_id']==args.dataset_id)
    result=benchmark(data,args.algorithm,args.output,repetition=args.repetition,warmup=args.warmup,smoke=args.smoke_only)
    print(json.dumps({k:v for k,v in result.items() if k not in ('input_manifest','compressor_identity','compression','decompression')}))
    sys.exit(0 if result['status']=='VERIFIED' else 1)


if __name__=='__main__':main()
