"""Receipt-only complete-cost attribution; no encoding or input selection."""
import json, math
from pathlib import Path
AREA=Path(__file__).resolve().parent

def m6_account(path):
    b=path if isinstance(path,bytes) else Path(path).read_bytes(); assert b[:5]==b'CIXM6'; q=5
    def var():
        nonlocal q
        v=s=0
        while True:
            x=b[q];q+=1;v|=(x&127)<<s
            if not x&128:return v
            s+=7
    history=var(); header=q; frames=[]
    while b[q]!=255:
        start=q; mode=b[q];q+=1;n=var();size=var();meta=q-start
        frames.append(dict(mode=mode,source_bytes=n,metadata_bytes=meta,payload_bytes=size))
        q+=size
    foot=q;q+=1;n=var();q+=4;assert q==len(b)
    return dict(complete_bytes=len(b),header_bytes=header,history_limit=history,
                footer_bytes=q-foot,source_bytes=n,frames=frames,
                payload_bytes=sum(f['payload_bytes'] for f in frames),
                framing_bytes=header+q-foot+sum(f['metadata_bytes'] for f in frames))

def ordinal_ranks(values):
    return [sum(z<v for z in values)+(sum(z==v for z in values)-1)/2 for v in values]

def correlation(a,b):
    a=ordinal_ranks(a);b=ordinal_ranks(b)
    ma=sum(a)/len(a);mb=sum(b)/len(b)
    va=sum((x-ma)**2 for x in a);vb=sum((x-mb)**2 for x in b)
    return sum((x-ma)*(y-mb) for x,y in zip(a,b))/math.sqrt(va*vb) if va*vb else None

def analyse(data):
    def enrich(v):
        if isinstance(v,dict):
            if 'time_receipt' in v:
                raw=Path(v['time_receipt']).read_text()
                for name,label in [('user_seconds','User time (seconds):'),('system_seconds','System time (seconds):'),('max_rss_kib','Maximum resident set size (kbytes):')]:
                    v[name]=float(next(line.rsplit(':',1)[1].strip() for line in raw.splitlines() if label in line))
            for child in list(v.values()):enrich(child)
        elif isinstance(v,list):
            for child in v:enrich(child)
    enrich(data)
    rows=data['rows'];controls=data['bare_controls']; by={r['descriptor']['name']:r for r in rows}
    def cost(name,backend):return by[name]['backends'][backend]['bytes']
    ordinary=min((f'mask{i}' for i in range(8)),key=lambda n:(cost(n,'m6'),n))
    A=controls['bare_m6']['bytes'];G=controls['bare_zstd']['bytes'];E=cost('E','m6');F=cost('E','zstd')
    bank={}
    for backend in ('native','zstd','m6'):
        ordered=sorted(rows,key=lambda r:(r['backends'][backend]['bytes'],r['descriptor']['name']))
        bank[backend]=dict(best=ordered[0]['descriptor'],bytes=ordered[0]['backends'][backend]['bytes'],
                           order=[r['descriptor']['name'] for r in ordered],
                           cross_costs={b:ordered[0]['backends'][b]['bytes'] for b in ('native','zstd','m6')})
    proxy=[]; minimum=min(cost(r['descriptor']['name'],'m6') for r in rows)
    for k in (1,2,3,5,15):
        names=bank['native']['order'][:k];chosen=min(names,key=lambda n:(cost(n,'m6'),n))
        proxy.append(dict(k=k,names=names,chosen=chosen,complete_bytes=cost(chosen,'m6'),
                          retains_a_minimizer=cost(chosen,'m6')==minimum,regret_bytes=cost(chosen,'m6')-minimum,
                          regret_if_bare_fallback_omitted=cost(chosen,'m6')-min(minimum,A),
                          selection_with_bare_fallback_bytes=min(cost(chosen,'m6'),A)))
    inner={}
    for name,r in by.items():
        arc=Path(r['backends']['m6']['archive']);b=arc.read_bytes();w=b[18]
        inner[name]=m6_account(b[25+w:])
    times={}; unique={}
    for r in rows:
        for backend in ('m6','zstd'):
            t=r['backends'][backend]['backend_encode'];unique[tuple(t['argv'])]=t
    for backend in ('m6','zstd'):
        group=[t for argv,t in unique.items() if ('cix' if backend=='m6' else '/bin/zstd') in str(argv[0])]
        times[backend]=dict(unique_trials=len(group),wall_seconds=sum(t['wall_seconds'] for t in group),
                            cpu_seconds=sum(t['user_seconds']+t['system_seconds'] for t in group),
                            max_process_rss_kib=max(t['max_rss_kib'] for t in group))
    native=[r['backends']['native']['encode'] for r in rows]
    times['native_proxy']=dict(trials=len(native),wall_seconds=sum(t['wall_seconds'] for t in native),
                              cpu_seconds=sum(t['user_seconds']+t['system_seconds'] for t in native),
                              max_process_rss_kib=max(t['max_rss_kib'] for t in native))
    return dict(matrix=dict(A_original_m6=A,B_BSS_m6=cost('mask0','m6'),C_all_residual_m6=cost('mask7','m6'),
                           D_best_ordinary_mask=ordinary,D_bytes=cost(ordinary,'m6'),E_frozen_m6=E,
                           F_frozen_zstd=F,G_original_zstd=G,H_external={n:v['bytes'] for n,v in controls.items() if n not in ('bare_m6','bare_zstd')}),
                paid_composition_gain_bytes=A-E,zstd_representation_gain_bytes=G-F,
                original_m6_backend_gain_bytes=G-A,transformed_m6_backend_gain_bytes=F-E,
                difference_in_differences_bytes=(A-E)-(G-F),descriptor_bytes=29,
                inner_m6_archive_gain_bytes=A-(E-29),
                replication_gate=E<A and E<cost(ordinary,'m6'),
                preferred=bank,proxy_shortlists=proxy,
                native_m6_spearman=correlation([r['backends']['native']['bytes'] for r in rows],[r['backends']['m6']['bytes'] for r in rows]),
                zstd_m6_spearman=correlation([r['backends']['zstd']['bytes'] for r in rows],[r['backends']['m6']['bytes'] for r in rows]),
                m6_accounting=inner,bare_m6_accounting=m6_account(controls['bare_m6']['archive']),encoder_economics=times)

if __name__=='__main__':
    data=json.loads((AREA/'results.json').read_text())
    # The runner may include a conditional replication as a separate result.
    if 'rows' not in data:
        output={k:analyse(v) for k,v in data.items() if isinstance(v,dict) and 'rows' in v}
    else:output=analyse(data)
    rep=AREA/'replication-results.json'
    if rep.exists():output=dict(qualification=output,replication=analyse(json.loads(rep.read_text())))
    (AREA/'analysis.json').write_text(json.dumps(output,indent=2,sort_keys=True)+'\n')
    print(json.dumps(output.get('matrix',output),indent=2))
