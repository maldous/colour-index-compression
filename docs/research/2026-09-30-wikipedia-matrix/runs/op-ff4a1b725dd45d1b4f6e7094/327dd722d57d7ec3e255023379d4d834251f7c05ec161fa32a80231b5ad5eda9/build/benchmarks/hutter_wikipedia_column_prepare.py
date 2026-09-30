#!/usr/bin/env python3
"""Freeze the first column comparison; no encode and no held-out bytes read."""
from pathlib import Path
import json,copy,hashlib
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/'docs/research/2026-09-30-wikipedia-columns';mfolder=p/'manifests';mfolder.mkdir(exist_ok=True)
template=json.loads((ROOT/'docs/research/2026-09-30-wikipedia-structure/moderate/manifests/dev0-original.json').read_text())
source=b'boundary\x00\n'+b''.join(b'<page><title>T&amp;'+str(i%17).encode()+b'</title><id>'+f'{i:06d}'.encode()+b'</id><revision><id>0009</id><timestamp>2006-03-01T00:00:00Z</timestamp><contributor><username>A&amp;B</username><id>07</id></contributor><text xml:space="preserve">Alpha [[Target]] {{T|n=007}}  3.14\n</text></revision></page>\n' for i in range(160))+b'<page><title>fragment'
small=p/'synthetic.bin';small.write_bytes(source)
control_path=next(q for q in (ROOT/'docs/research/2026-09-30-wikipedia-structure/moderate/runs').glob('*/receipt.json') if json.loads(q.read_text())['identity']['configuration']['mode']=='original')
control=json.loads(control_path.read_text())
build=['benchmarks/hutter_bounded_runner.py','benchmarks/hutter_wikipedia_column_batch.py','benchmarks/hutter_wikipedia_column_prepare.py','benchmarks/hutter_wikipedia_columns_probe.py','benchmarks/hutter_wikipedia_columns.py','benchmarks/hutter_wikipedia_column_coding.py','benchmarks/hutter_structure_columns.py','benchmarks/hutter_structure.py','benchmarks/hutter_structure_probe.py','benchmarks/markup_columns.py','benchmarks/mysql_record_constraints.py','cix/__init__.py','cix/multinomial.py']
for phase in ('small','dev0'):
 for mode,cpu in [('raw',0),('remaining',2),('rank',4)]+([('original',6)] if phase=='small' else []):
  m=copy.deepcopy(template);m['configuration'].update(mode=mode,experiment_phase=phase,codec_commit='manifest build SHA-256 identifies frozen implementation',execution_boundary=f'one lane CPU{cpu}; at most4 concurrentjobs',column_block_values=1024)
  m['hypothesis']='Skeleton-relative field columns and paid within-column dictionaries/counts may reduce total PAQ bytes; matched remaining-count arithmetic and exact rank receive identical palettes/counts/partitions.'
  m['mechanism']=mode;m['build_paths']=build
  m['matched_control']='Pinned identical PAQv216 -4 -simd AVX2; exact original input; same PAQ input basename; original raw dev0 completed control reused without recompression.'
  m['promotion_criteria']='Every retained gain must independently restoreexact SHA; successful complete archives >= verifiedcontrol are size-rejectedUNVERIFIED. No portfolio concealment. Several devregions and higher-effort PAQ required before any general/strongest-baseline claim; noholdouts/fullrun now.'
  m['budget'].update(cpu=cpu,wall_seconds=300 if phase=='small' else 1200)
  if phase=='small':
   m.pop('stage',None);m.pop('longer_budget_justification',None)
   m['input']={'path':str(small),'offset':0,'length':len(source),'sha256':hashlib.sha256(source).hexdigest()}
  else:
   m['decode_size_gate']={'control_receipt':str(control_path),'archive_sha256':control['archive_sha256'],'control_bytes':control['archive_bytes'],'matching_configuration_keys':['paq_binary_sha256','paq_options','source_filename']}
  if mode!='original':
   m['encode_command'][1]=str(ROOT/'benchmarks/hutter_wikipedia_columns_probe.py');m['decode_command'][1]=str(ROOT/'benchmarks/hutter_wikipedia_columns_probe.py')
  m['encode_command'][m['encode_command'].index('--mode')+1]=mode
  path=mfolder/f'{phase}-{mode}.json';content=json.dumps(m,indent=2)+'\n'
  if path.exists() and path.read_text()!=content:raise ValueError('immutable manifest mismatch')
  path.write_text(content)
(p/'control-reference.json').write_text(json.dumps({'receipt':str(control_path),'archive_bytes':control['archive_bytes'],'archive_sha256':control['archive_sha256'],'input':control['identity']['input'],'note':'Existing independently verified original PAQ reused; no repeatedbaselineencode'},indent=2)+'\n')
