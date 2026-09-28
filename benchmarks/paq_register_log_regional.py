"""Measure new adaptive frames against unchanged, fully verified reference frames.

Native and fixed-prior archives were independently encoded and restored in the
preceding regional tournament. Reuse them only after source/input/frame/backend
identity checks. Do not repeat those encodes merely to compare the new method.
"""
import argparse
import json
from pathlib import Path
import subprocess
import zlib
from benchmarks import paq_register_log_probe as adaptive, paq_register_prior_probe as reference
from cix.multinomial import vdecode


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True)
    parser.add_argument('--controls',default='results/leaderboard/paq-register-prior-cohorts')
    parser.add_argument('--manifest',default='results/leaderboard/ecoff-got-cohorts-v2/manifest.json');args=parser.parse_args()
    root=Path(args.output).resolve();root.mkdir(parents=True,exist_ok=True);control_root=Path(args.controls).resolve()
    manifest=json.loads(Path(args.manifest).read_text());control=json.loads((control_root/'complete.json').read_text())
    if not control['complete']:raise ValueError('incomplete controls')
    outer_sources={str(p):adaptive.sha(p.read_bytes()) for p in [Path(__file__),Path(reference.__file__)]};comparisons=[]
    for item in manifest['rows']:
        source=Path(item['path']);data=source.read_bytes();digest=adaptive.sha(data)
        if digest!=item['sha256']:raise ValueError('changed regional source')
        selected={}
        for mode in (4,1):
            candidates=[r for r in control['rows'] if r['input_path']==item['path'] and r['mode']==mode]
            if len(candidates)!=1:raise ValueError('ambiguous reference')
            r=candidates[0];framepath=control_root/f'{source.stem}-{mode}'/'stream.cixb';frame=framepath.read_bytes()
            if (not r['round_trip'] or r['input_sha256']!=digest or r['restored_sha256']!=digest
                or r['options']!='-4' or len(frame)!=r['physical_bytes'] or adaptive.sha(frame)!=r['frame_sha256']):
                raise ValueError('reference physical proof changed')
            for path,expected in r['source_hashes'].items():
                if adaptive.sha(Path(path).read_bytes())!=expected:raise ValueError('reference dependency changed')
            if frame[:5]!=reference.MAGIC or frame[5]!=mode:raise ValueError('reference header changed')
            n,pos=vdecode(frame,6)
            if n!=len(data) or int.from_bytes(frame[pos:pos+4],'big')!=zlib.crc32(data) or adaptive.sha(frame[pos+4:])!=r['paq_sha256']:
                raise ValueError('reference payload or checksum mismatch')
            selected['native' if mode==4 else 'fixed_prior']=dict(r,artifact=str(framepath),verification='Exact unchanged frame and its prior independent restoration retained; input/source/backend hashes rechecked')
        row=adaptive.worker((item['path'],1,'-4',str(root)))
        pair=dict(input_path=item['path'],input_sha256=digest,controls=selected,adaptive=row,
            saved_vs_native_bytes=selected['native']['physical_bytes']-row['physical_bytes'],
            saved_vs_fixed_bytes=selected['fixed_prior']['physical_bytes']-row['physical_bytes'])
        comparisons.append(pair);print(json.dumps({k:v for k,v in pair.items() if k not in ('controls','adaptive')}),flush=True)
    for path,expected in outer_sources.items():
        if adaptive.sha(Path(path).read_bytes())!=expected:raise ValueError('comparison source changed')
    report=dict(complete=True,diagnostic_only=True,source_hashes=outer_sources,rows=comparisons,
        reference_report=str(control_root/'complete.json'),reference_report_sha256=adaptive.sha((control_root/'complete.json').read_bytes()),
        revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=adaptive.ROOT,text=True).strip(),
        verification='Three new physical frames independently decoded; six existing reference frames reused only after complete identity checks. No controls are estimated and no whole-file score is inferred.')
    (root/'comparison.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
