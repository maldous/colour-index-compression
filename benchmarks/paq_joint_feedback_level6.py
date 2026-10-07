"""Test qualified joint feedback at higher effort, retaining exact native controls."""
import concurrent.futures
import json
import os
from pathlib import Path
import zlib
from benchmarks import paq_joint_feedback_probe as joint, paq_gp_feedback_probe as reference
from cix.multinomial import vdecode


def run(spec):
    path, cpu, root = spec
    os.sched_setaffinity(0, {cpu})
    return joint.worker((path, 3, '-6', root))


def main():
    root = Path('results/leaderboard/paq-joint-feedback-level6').resolve()
    if root.exists(): raise ValueError('preserve existing level6 experiment')
    manifest = json.loads(Path('results/leaderboard/ecoff-got-cohorts-v2/manifest.json').read_text())
    control_root = Path('results/leaderboard/paq-gp-feedback-level6-cohorts')
    report_path = control_root/'complete.json'
    report = json.loads(report_path.read_text())
    if not report['complete']: raise ValueError('incomplete native controls')
    outer = {str(p):joint.sha(p.read_bytes()) for p in (Path(__file__), Path(reference.__file__))}
    controls = []
    for item in manifest['rows']:
        source = Path(item['path']); data = source.read_bytes(); digest = joint.sha(data)
        if digest != item['sha256']: raise ValueError('regional input changed')
        r, = [r for r in report['rows'] if r['input_path'] == item['path'] and r['mode'] == 4]
        framepath = control_root/f'{source.stem}-4'/'stream.cixb'; frame = framepath.read_bytes()
        if (not r['round_trip'] or r['input_sha256'] != digest or r['restored_sha256'] != digest
            or r['options'] != '-6' or len(frame) != r['physical_bytes'] or joint.sha(frame) != r['frame_sha256']):
            raise ValueError('native physical proof changed')
        for p,h in r['source_hashes'].items():
            if joint.sha(Path(p).read_bytes()) != h: raise ValueError('native dependency changed')
        if frame[:5] != reference.MAGIC or frame[5] != 4: raise ValueError('native frame changed')
        n,pos = vdecode(frame,6)
        if n != len(data) or int.from_bytes(frame[pos:pos+4],'big') != zlib.crc32(data) or joint.sha(frame[pos+4:]) != r['paq_sha256']:
            raise ValueError('native payload changed')
        controls.append(dict(r,artifact=str(framepath),verification='Previously independently restored native archive; all identities rechecked'))
    root.mkdir(parents=True)
    specs = [(item['path'],cpu,str(root)) for item,cpu in zip(manifest['rows'],(0,18,22),strict=True)]
    with concurrent.futures.ProcessPoolExecutor(3,max_tasks_per_child=1) as pool:
        rows = list(pool.map(run,specs))
    groups = []
    for control,row in zip(controls,rows,strict=True):
        if row['transformed_sha256'] != control['transformed_sha256']: raise ValueError('transform mismatch')
        groups.append(dict(native=control,joint=row,saved_bytes=control['physical_bytes']-row['physical_bytes']))
    for p,h in outer.items():
        if joint.sha(Path(p).read_bytes()) != h: raise ValueError('comparison dependency changed')
    result = dict(complete=True,diagnostic_only=True,scored=False,groups=groups,source_hashes=outer,
        native_report=str(report_path),native_report_sha256=joint.sha(report_path.read_bytes()),
        verification='Three new joint frames independently restored; three unchanged native controls retained after full identity checks. No whole-file projection.')
    (root/'comparison.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps([dict(input=x['joint']['input_path'],saved_bytes=x['saved_bytes']) for x in groups]),flush=True)


if __name__ == '__main__': main()
