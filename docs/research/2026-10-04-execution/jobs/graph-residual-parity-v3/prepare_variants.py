#!/usr/bin/env python3
"""Byte surgery only: never encode/decode, compile, fetch, or alter originals."""
from pathlib import Path
import hashlib,json,os,resource
os.sched_setaffinity(0,{8})
resource.setrlimit(resource.RLIMIT_AS,(500_000_000,500_000_000))
resource.setrlimit(resource.RLIMIT_FSIZE,(1_000_000,1_000_000))
resource.setrlimit(resource.RLIMIT_CPU,(30,30))
JOB=Path(__file__).resolve().parent
FX=JOB/'harness/tests/fixtures/graph_residual_parity'
OUT=JOB/'variants'
OUT.mkdir(exist_ok=False)
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def varint(data,at):
    value=0
    for shift in range(0,70,7):
        byte=data[at];at+=1;value|=(byte&127)<<shift
        if not byte&128:return value,at
    raise ValueError('fixture header varint exceeds 10 bytes')
def payload_start(frame,hydrogen):
    at=7
    if hydrogen:_,at=varint(frame,at)
    records,at=varint(frame,at);at+=(records+7)//8
    size,at=varint(frame,at);at+=size
    count_or_choices,at=varint(frame,at)
    return at+count_or_choices if hydrogen else at
cases=[]
names=[f'graph-{m}-1.frame' for m in range(3)]+[f'hydrogen-{m}-{p}.frame' for m in range(3) for p in range(4)]
for name in names:
    source=FX/name;frame=source.read_bytes();hydrogen=name.startswith('hydrogen-')
    assert frame[-1:]==b'\n'
    start=payload_start(frame,hydrogen);without_lf=frame[:-1]
    last_line_start=without_lf.rfind(b'\n',start)+1
    if last_line_start==0:last_line_start=start
    assert without_lf[last_line_start:].count(b',')==2
    last_comma=without_lf.rfind(b',',last_line_start)
    assert last_comma+1<len(without_lf)
    mutations={'no-final-lf':without_lf,'empty-final-component':without_lf[:last_comma+1],
               'missing-final-vector':without_lf[:last_line_start]}
    inp=FX/('hydrogen.input' if hydrogen else 'graph.input')
    for mutation,data in mutations.items():
        path=OUT/(source.stem+'.'+mutation+'.frame');path.write_bytes(data)
        cases.append(dict(id=path.stem,archive_path=str(path),archive_sha256=digest(path),archive_bytes=len(data),
                          mutation=mutation,source_frame_path=str(source),source_frame_sha256=digest(source),
                          source_payload_start=start,removed_bytes=len(frame)-len(data),
                          native_driver_kind='hydrogen' if hydrogen else 'graph',
                          reference_module='cix_runtime.legacy.sdf_hydrogen' if hydrogen else 'cix_runtime.legacy.sdf_geometry',
                          reference_function='decode',expected_outcome='ACCEPT_EXACT_INPUT' if mutation=='no-final-lf' else 'REJECT',
                          expected_input_path=str(inp),expected_input_sha256=digest(inp),output_cap_bytes=inp.stat().st_size))
(JOB/'variant-manifest.json').write_text(json.dumps(dict(schema='cix128-text-variants-v1',text_sources=15,cases=cases,
    contract='Root alone executes: 15 optional-LF exact native/Python reconstructions and 30 malformed rejection cases. Driver kind/archive/output/exact-output-cap interface unchanged. Negative native driver must exit nonzero; Rust is_err and Python errors establish rejection. No decoder was executed to generate variants.'),indent=2)+'\n')
print('Prepared 45 byte-mutated archives from 15 canonical text frames; no codec invoked.')
