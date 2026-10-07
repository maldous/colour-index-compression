import hashlib,json,time
from pathlib import Path
from benchmarks.hutter_track_a import decode as decode_a
from benchmarks.hutter_track_b import decode_archive as decode_b

root=Path('/home/user/src/colour-index-compression/docs/research/2026-09-30-bounded-research')
sha=lambda b:hashlib.sha256(b).hexdigest()
started=time.monotonic(); rows=[]
a=json.loads((root/'track-a-second-enforced-receipt.json').read_text())
for region in a['development_regions']:
 for row in region['rows']:
  frame=root/'track-a-second-enforced-receipt-frames'/f"{region['name']}-{row['method']}.cix-ta"
  data=frame.read_bytes(); restored=decode_a(data)
  assert sha(restored)==region['input_sha256'] and sha(data)==row['frame_sha256']
  assert len(data)==sum(row[k] for k in ('framing_bytes','first_literal_bytes','count_metadata_bytes','ordering_bytes','exception_bytes'))
  rows.append({'path':str(frame),'bytes':len(data),'verified':True,'restored_sha256':sha(restored)})
for path in sorted((root/'track-b-results').glob('b[12]-*/*.json')):
 row=json.loads(path.read_text());frame=Path(row['output']['archive']);data=frame.read_bytes();restored=decode_b(data)
 assert sha(restored)==row['input']['sha256'] and sha(data)==row['output']['archive_sha256']
 assert len(data)==sum(row['accounting'][k] for k in ('payload_bytes','metadata_bytes','framing_bytes'))
 rows.append({'path':str(frame),'bytes':len(data),'verified':True,'restored_sha256':sha(restored)})
result={'source_commit':'94101e510344c9385fcfdd2c5fbc2b6cd86725db','verification':'all archived physical streams decoded and overhead totals checked','count':len(rows),'elapsed_seconds':time.monotonic()-started,'rows':rows}
(root/'root-audit-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'verified_frames':len(rows),'elapsed_seconds':result['elapsed_seconds']}))
