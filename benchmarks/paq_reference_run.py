"""Local PAQ reference measurement with physical archives and exact restoration.

No network or CI calls. A successful JSON record exists only after a separate
extraction and byte comparison. Interrupted artifacts are retained, never scored.
"""
import argparse,concurrent.futures,datetime,hashlib,json,os,subprocess,time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1<<20),b''):h.update(chunk)
    return h.hexdigest()

def equal(a,b):
    with Path(a).open('rb') as x,Path(b).open('rb') as y:
        while True:
            left,right=x.read(1<<20),y.read(1<<20)
            if left!=right:return False
            if not left:return True

def atomic(path,value):
    temp=path.with_suffix(path.suffix+'.tmp');temp.write_text(json.dumps(value,indent=2)+'\n');temp.replace(path)

def measured(command,folder,phase,status):
    metrics=folder/(phase+'.metrics');log=folder/(phase+'.log')
    start=time.perf_counter()
    with log.open('wb') as output:
        proc=subprocess.Popen(['/usr/bin/time','-f','%e %M','-o',str(metrics),*command],cwd=ROOT,stdout=output,stderr=subprocess.STDOUT,env={**os.environ,'OMP_NUM_THREADS':'1'})
        atomic(folder/'status.json',dict(**status,phase=phase,pid=proc.pid,command=command,started_at=datetime.datetime.now(datetime.timezone.utc).isoformat()))
        code=proc.wait()
    elapsed=time.perf_counter()-start
    if code:
        atomic(folder/'status.json',dict(**status,phase='failed',failed_phase=phase,returncode=code))
        raise RuntimeError(f'{phase} failed ({code}); see {log}')
    values=metrics.read_text().strip().split()
    return dict(wall_seconds=elapsed,process_elapsed_seconds=float(values[-2]),peak_rss_kib=int(values[-1]))

def run(item,args,policy):
    source=ROOT/item['path'];name=source.name
    if source.stat().st_size!=item['size'] or digest(source)!=item['sha256']:raise ValueError('input manifest mismatch')
    folder=(ROOT/args.output/name).resolve();folder.mkdir(parents=True,exist_ok=True)
    archive=folder/('stream.paq8px'+args.version[1:]);restored=folder/'restored.bin';record=folder/'result.json'
    identity=dict(input_sha256=item['sha256'],original=item['size'],policy=policy)
    if record.exists():
        old=json.loads(record.read_text())
        if old['identity']!=identity or not old['round_trip'] or digest(archive)!=old['archive_sha256'] or archive.stat().st_size!=old['size']:raise ValueError('cached reference mismatch')
        return old
    if archive.exists() or restored.exists():raise ValueError(f'unverified artifact exists in {folder}; inspect before retry')
    status=dict(file=name,identity=identity)
    enc=measured([args.binary,args.options,'-simd',args.simd,str(source),str(archive)],folder,'encode',status)
    if not archive.read_bytes().startswith(b'paq8px'):raise ValueError('missing physical PAQ stream')
    dec=measured([args.binary,'-d','-simd',args.simd,str(archive),str(restored)],folder,'decode',status)
    if not equal(source,restored):raise ValueError('byte-for-byte restoration failed')
    row=dict(identity=identity,file=name,corpus=item.get('corpus','silesia'),original=item['size'],size=archive.stat().st_size,archive_sha256=digest(archive),restored_sha256=digest(restored),round_trip=True,encode=enc,decode=dec,external_reference=True,completed_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
    atomic(record,row);atomic(folder/'status.json',dict(**status,phase='complete',size=row['size']))
    restored.unlink()
    print(json.dumps(dict(file=name,size=row['size'],round_trip=True,encode=enc,decode=dec)),flush=True)
    return row

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',default='results/silesia-manifest.json');p.add_argument('--output',required=True);p.add_argument('--version',choices=('v215','v216'),required=True);p.add_argument('--options',default='-12L');p.add_argument('--simd',default='AVX2');p.add_argument('--jobs',type=int,default=1);p.add_argument('--only',nargs='*');p.add_argument('--order',nargs='*');args=p.parse_args()
    args.binary=str((ROOT/'benchmark-work/references'/('paq8px-'+args.version)/'build-local/paq8px').resolve())
    provenance=json.loads((ROOT/'benchmark-work/references'/(args.version+'-source.json')).read_text())
    policy=dict(version=args.version,options=args.options,simd=args.simd,binary_sha256=digest(args.binary),source=provenance,runner_sha256=digest(Path(__file__)),revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
    fix=ROOT/'benchmark-work/references'/f'{args.version}-build-fix.json'
    if fix.exists():policy['build_fix']=json.loads(fix.read_text())
    items=json.loads((ROOT/args.manifest).read_text())
    if args.only:items=[i for i in items if Path(i['path']).name in args.only]
    if args.order:
        order={name:i for i,name in enumerate(args.order)};items.sort(key=lambda i:order.get(Path(i['path']).name,len(order)))
    out=ROOT/args.output;out.mkdir(parents=True,exist_ok=True)
    atomic(out/'run.json',dict(policy=policy,items=items,jobs=args.jobs,started_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),manager_pid=os.getpid()))
    start=time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(args.jobs) as pool:rows=list(pool.map(lambda i:run(i,args,policy),items))
    atomic(out/'complete.json',dict(complete=True,members=len(rows),total=sum(r['size'] for r in rows),wall_seconds=time.perf_counter()-start,policy=policy,rows=rows))

if __name__=='__main__':main()
