"""Collect the adaptive joint pilot with complete immutable reference proofs."""
import argparse
import json
from pathlib import Path
import zlib
from benchmarks import paq_joint_log_probe as new, paq_joint_feedback_probe as old
from cix.multinomial import vdecode


def verified_rows(root, codec):
    report_path=root/'complete.json'; report=json.loads(report_path.read_text())
    if not report['complete']: raise ValueError('incomplete pilot')
    rows={}; hashes={}
    for r in report['rows']:
        source=Path(r['input_path']); data=source.read_bytes(); digest=new.sha(data)
        framepath=root/f'{source.stem}-{r["mode"]}'/'stream.cixb'; frame=framepath.read_bytes()
        if (not r['round_trip'] or r['input_sha256']!=digest or r['restored_sha256']!=digest
            or len(frame)!=r['physical_bytes'] or new.sha(frame)!=r['frame_sha256'] or r['options']!='-4'):
            raise ValueError('pilot physical proof changed')
        for path,expected in r['source_hashes'].items():
            if path not in hashes: hashes[path]=new.sha(Path(path).read_bytes())
            if hashes[path]!=expected: raise ValueError('pilot source dependency changed')
        if frame[:5]!=codec.MAGIC or frame[5]!=r['mode']: raise ValueError('pilot frame changed')
        n,pos=vdecode(frame,6)
        if n!=len(data) or int.from_bytes(frame[pos:pos+4],'big')!=zlib.crc32(data) or new.sha(frame[pos+4:])!=r['paq_sha256']:
            raise ValueError('pilot payload changed')
        raw,_=codec.transform.transform(data,4)
        if new.sha(raw)!=r['transformed_sha256'] or codec.transform.inverse(raw)!=data: raise ValueError('pilot transform changed')
        if r['mode'] in rows: raise ValueError('duplicate pilot mode')
        rows[r['mode']]=dict(r,artifact=str(framepath))
    return rows,dict(path=str(report_path),sha256=new.sha(report_path.read_bytes()))


def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--output',required=True); args=parser.parse_args()
    output=Path(args.output)
    if output.exists(): raise ValueError('preserve existing qualification')
    controls,old_report=verified_rows(Path('results/leaderboard/paq-joint-feedback-pilot'),old)
    rows,new_report=verified_rows(Path('results/leaderboard/paq-joint-log-pilot'),new)
    if set(controls)!={0,1,2,3,4} or set(rows)!={0,2,3}: raise ValueError('missing pilot arm')
    for r in [*rows.values(),*controls.values()]:
        if r['input_sha256']!=controls[4]['input_sha256'] or r['transformed_sha256']!=controls[4]['transformed_sha256']:
            raise ValueError('unmatched experimental inputs')
    if rows[0]['paq_sha256']!=controls[4]['paq_sha256']: raise ValueError('disabled codec differs from native')
    result=dict(complete=True,diagnostic_only=True,scored=False,new_rows=list(rows.values()),retained_controls=list(controls.values()),
        source_reports=[old_report,new_report],collector_sha256=new.sha(Path(__file__).read_bytes()),
        disabled_matches_native=True,saved_vs_native_bytes=controls[4]['physical_bytes']-rows[3]['physical_bytes'],
        saved_vs_memory_bytes=controls[1]['physical_bytes']-rows[3]['physical_bytes'],
        saved_vs_adaptive_register_bytes=rows[2]['physical_bytes']-rows[3]['physical_bytes'],
        saved_vs_fixed_joint_bytes=controls[3]['physical_bytes']-rows[3]['physical_bytes'],
        interpretation='Three new physical archives independently restore. Disabled payload matches native exactly. Earlier five control frames are retained after input/frame/source/backend and transform checks. All streams include13 framing bytes and use the same structural transform; no full-file projection, hard state-space exclusion or identical-information rank-coder advantage is claimed.')
    output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('new_rows','retained_controls')},indent=2))


if __name__=='__main__': main()
