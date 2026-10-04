#!/usr/bin/env python3
"""Root-leased direct pinned-Cppcheck check of the normalized decompressor; no Sonar."""
from __future__ import annotations
import hashlib, importlib.util, json, os, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5]; JOB=Path(__file__).resolve().parent
PREPARED=ROOT/'docs/research/2026-10-04-execution/sonar-preparation/prepared-v6'
FREEZE=JOB/'frozen-scope.json'
TOOL=ROOT/'docs/research/2026-10-04-execution/jobs/sonar-tool-tests-v18/receipt.json'
PROJECTION=ROOT/'docs/research/2026-10-04-execution/jobs/adapter-cppcheck-projection-v3/receipt.json'
TARGET='rust/cix-native/adapters/squashfs/kernel/cix_squashfs_decompressor.c'
FAILED_INPUTS={}
PREFIXES=tuple(str(ROOT/'rust/cix-native'/part)+'/' for part in ('adapters','bindings','packaging','tests'))
def digest(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load():
 s=importlib.util.spec_from_file_location('diagnostic_repair',ROOT/'tools/sonar-cxx/repair.py');m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m);return m
def main():
 if os.environ.get('CIX_RELEASE_LEASE')!='1': raise RuntimeError('root scheduler lease required')
 repair=load(); repair.require_stopped_confirmation(repair.SUMMARY)
 if (JOB/'receipt.json').exists(): raise RuntimeError('refusing to overwrite direct Cppcheck prerequisite')
 global FAILED_INPUTS
 FAILED_INPUTS={'tool_receipt_sha256':digest(TOOL),'projection_receipt_sha256':digest(PROJECTION),'repair_py_sha256':digest(ROOT/'tools/sonar-cxx/repair.py')}
 tool_value=json.loads(TOOL.read_text())
 required=('repair.py','test_repair.py','include_context.py','test_include_context.py','translation_context.py','test_translation_context.py')
 if (tool_value.get('status')!='pass' or tool_value.get('source_unchanged') is not True or
     any(tool_value.get('source_sha256',{}).get('tools/sonar-cxx/'+name)!=digest(ROOT/'tools/sonar-cxx'/name) for name in required)):
  raise RuntimeError('v18 tool receipt is stale or failed')
 projection_value=json.loads(PROJECTION.read_text())
 if (projection_value.get('status')!='pass' or projection_value.get('source_unchanged') is not True or
     projection_value.get('tool_sha256',{}).get('repair.py')!=FAILED_INPUTS['repair_py_sha256']):
  raise RuntimeError('projection-v3 receipt is stale or failed')
 freeze=json.loads(FREEZE.read_text()); scope={r['path']:r['current_sha256'] for r in freeze['current_scope']}
 if len(scope)!=55 or any(digest(ROOT/n)!=h for n,h in scope.items()): raise RuntimeError('current scope differs from freeze')
 commands=[r for r in json.loads((PREPARED/'compile_commands.host.json').read_text()) if r['file'].startswith(PREFIXES)]
 row=[r for r in commands if r['file']==str(ROOT/TARGET)]
 if len(row)!=1: raise RuntimeError('missing exact decompressor compiler record')
 raw=JOB/'raw'; budget=repair.EvidenceBudget(raw); budget.mkdir(raw)
 repair.cppcheck(ROOT,[TARGET],raw,row,budget)
 errors=[e.attrib for e in repair.ET.parse(raw/'cppcheck.xml').iter('error')]
 fatal=[e for e in errors if e.get('id') in ('unknownMacro','preprocessorErrorDirective')]
 projections=json.loads((raw/'cppcheck-preprocessing.json').read_text())
 if len(projections)!=1 or projections[0].get('gnu_typeof_spellings_normalised',0)<1: raise RuntimeError('direct Cppcheck did not use the reviewed normalized decompressor projection')
 if fatal: raise RuntimeError('direct pinned Cppcheck retains fatal configuration diagnostic: '+repr(fatal))
 if any(digest(ROOT/n)!=h for n,h in scope.items()): raise RuntimeError('source changed during direct Cppcheck prerequisite')
 if (digest(TOOL)!=FAILED_INPUTS['tool_receipt_sha256'] or digest(PROJECTION)!=FAILED_INPUTS['projection_receipt_sha256'] or
     digest(ROOT/'tools/sonar-cxx/repair.py')!=FAILED_INPUTS['repair_py_sha256']):
  raise RuntimeError('tool or prerequisite receipt changed during direct Cppcheck prerequisite')
 (JOB/'receipt.json').write_text(json.dumps({'status':'pass','source_unchanged':True,'target':TARGET,'cppcheck_version':'pinned private 2.13 runtime','unknownMacro':0,'preprocessorErrorDirective':0,'gnu_typeof_spellings_normalised':projections[0]['gnu_typeof_spellings_normalised'],'tool_sha256':digest(ROOT/'tools/sonar-cxx/repair.py'),'input_sha256':FAILED_INPUTS},indent=2)+'\n')
if __name__=='__main__':
 try:
  main()
 except Exception as error:
  receipt=JOB/'receipt.json'
  if not receipt.exists():
   receipt.write_text(json.dumps({'status':'fail','input_sha256':FAILED_INPUTS,'error':str(error)},indent=2)+'\n')
  raise
