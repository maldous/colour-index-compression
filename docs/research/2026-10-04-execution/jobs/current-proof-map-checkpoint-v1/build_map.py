#!/usr/bin/env python3
from pathlib import Path
import ast,hashlib,json,os,re,resource,subprocess,time
os.sched_setaffinity(0,{9});resource.setrlimit(resource.RLIMIT_AS,(500_000_000,500_000_000));resource.setrlimit(resource.RLIMIT_CPU,(45,45));resource.setrlimit(resource.RLIMIT_FSIZE,(2_000_000,2_000_000))
ROOT=Path('/home/user/src/colour-index-compression');OUT=Path(__file__).resolve().parent;N=ROOT/'rust/cix-native';J=ROOT/'docs/research/2026-10-04-execution/jobs';OLD=Path('/home/user/src/cix-managed-service/work/cix55-source-readiness')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def native(name):return N/'src/full_engine'/(name+'.rs')
# Explicit human-selected counterparts; symbol location is checked, not inferred from names alone.
M={
'__init__.py':([],[],[]),'legacy/__init__.py':([],[],[]),
'backends.py':(['backend_provider','containers'],['encode','wrap_paq'],['decode','unwrap_paq']),
'cli.py':([],[],[]),
'engine.py':(['catalogue','selection','dispatch','containers'],['catalog','select_whole_input','encode_candidate','encode_raw'],['decode','decode_raw']),
'heterogeneous.py':(['mixed','mixed_selection'],['encode_with','encode'],['decode_with']),
'image_grid.py':(['catalogue','dispatch','strided_values','volume_lifting'],['catalog','encode_candidate'],['decode']),
'legacy/image_grid.py':(['catalogue','dispatch'],['catalog'],['decode']),
'legacy/chemical_db.py':(['structured_frames','record_ordering','catalogue','dispatch'],['encode_geometry','encode_hydrogen','encode_mysql_record_constraints','encode_mysql_fixed_columns'],['decode_geometry','decode_hydrogen','decode_mysql_record_constraints','decode_mysql_fixed_columns']),
'legacy/executable.py':(['address_relations','dispatch'],['encode_checked_frame','encode_transformed_frame'],['decode_checked_frame','decode_transformed_frame','decode']),
'legacy/ecoff_call_entries.py':(['address_relations'],[],[]),
'legacy/ecoff_constraints.py':(['address_relations'],['constraints_transform'],['constraints_inverse']),
'legacy/ecoff_fields.py':(['address_relations'],['fields_transform'],['fields_inverse']),
'legacy/ecoff_got.py':(['address_relations'],['got_transform'],['got_inverse']),
'legacy/ecoff_pdata.py':(['address_relations'],['pdata_transform'],['pdata_inverse']),
'legacy/ecoff_pdata_symbols.py':(['address_relations'],['pdata_symbols_transform'],['pdata_symbols_inverse']),
'legacy/ecoff_pointer_deltas.py':(['address_relations'],['pointer_delta_transform'],['pointer_delta_inverse']),
'legacy/ecoff_relocated_pointers.py':(['address_relations'],['relocated_pointer_candidates'],[]),
'legacy/ecoff_section_pointers.py':(['address_relations'],['section_pointer_transform'],['section_pointer_inverse']),
'legacy/ecoff_symbol_loads.py':(['address_relations'],['symbol_load_transform'],['symbol_load_inverse']),
'legacy/framing.py':(['arithmetic'],['vencode','checked_frame'],['vdecode','parse_checked_frame','verify_frame']),
'legacy/grid_backend.py':(['bounded_values'],['transform_backend','encode_backend_frame'],['inverse_backend','decode_backend_frame']),
'legacy/grid_conditional.py':(['grid_counts'],['transform_conditional','encode_conditional_frame'],['inverse_conditional','decode_conditional_frame']),
'legacy/grid_context.py':(['grid_counts'],['transform_counts','encode_counts_frame'],['inverse_counts','decode_counts_frame']),
'legacy/grid_feedback.py':(['grid_context'],['transform_raw','encode_frame'],['inverse_raw','decode_frame']),
'legacy/grid_grouped.py':(['conditional_values'],['transform_coordinate_groups','encode_grouped_frame'],['inverse_coordinate_groups','decode_grouped_frame']),
'legacy/grid_interval.py':(['interval_context','conditional_values'],['transform_raw','encode_frame','encode_integers'],['inverse_raw','decode_frame','decode_integers']),
'legacy/multinomial.py':(['arithmetic'],['colex_rank','composition_rank'],['colex_unrank','composition_unrank']),
'legacy/ordered_subset.py':(['arithmetic'],['ordered_subset_encode_with_method','ordered_subset_encode'],['ordered_subset_decode_with_method','ordered_subset_decode']),
'legacy/mysql_fixed_columns.py':(['record_ordering'],['transform_mysql_fixed_columns','encode_mysql_fixed_columns'],['inverse_mysql_fixed_columns','decode_mysql_fixed_columns']),
'legacy/mysql_record_constraints.py':(['record_ordering'],['transform_mysql_record_constraints','encode_mysql_record_constraints'],['inverse_mysql_record_constraints','decode_mysql_record_constraints']),
'legacy/mysql_remaining_counts.py':(['record_ordering'],['remaining_count_order_encode'],['remaining_count_order_decode']),
'legacy/record_float_grid.py':(['strided_values'],['transform_wcs_grid_numeric','transform_wcs_grid_transpose','encode_wcs_grid_numeric_frame'],['inverse_wcs_grid','decode_wcs_grid']),
'legacy/sdf_geometry.py':(['graph_residuals'],['encode','encode_with_palette'],['decode_with_limit']),
'legacy/sdf_hydrogen.py':(['graph_residuals'],['encode_hydrogen_with_options'],['decode_hydrogen_with_limit']),
'legacy/multiscale_volume.py':(['volume_lifting'],['encode_multiscale'],['decode_multiscale']),
'legacy/spatial_image_codec.py':(['volume_lifting','spatial_frames'],['encode_spatial','encode_spatial_frame'],['decode_spatial','decode_spatial_frame']),
'legacy/volume_image_codec.py':(['volume_lifting'],['volume_transform','encode_volume'],['volume_inverse','decode_volume']),
'model.py':(['catalogue'],[],[]),'regions.py':(['regions'],['structured_regions','regions','boundaries'],[]),
'specialized.py':(['catalogue','dispatch'],['catalog','encode_candidate'],['decode'])}
oldmap=ROOT/'docs/research/2026-10-04-native-rc/port-map.json';entries=json.loads(oldmap.read_text())['entries'];assert len(entries)==41 and len({x['runtime_module'] for x in entries})==41
assert set(M)=={x['runtime_module'] for x in entries},set(M)^{x['runtime_module'] for x in entries}
inputs={};inventory={}
paths=set(native(name) for values in M.values() for name in values[0]);paths|={N/'src/cli.rs',N/'src/paq_bridge.rs',N/'src/paq_supervisor.rs',N/'src/rank.rs',N/'src/combinatorics.rs',N/'src/limits.rs',native('installed'),native('native_portfolio'),native('mod')}
for p in sorted(paths):
 s=p.read_text();inputs[str(p)]=sha(p);functions=[];constants=[];imports=[]
 for ln,line in enumerate(s.splitlines(),1):
  for m in re.finditer(r'\bfn\s+(\w+)',line):functions.append(dict(name=m.group(1),line=ln,signature=line.strip(),cfg_test_previous_line='#[cfg(test)]' in s.splitlines()[max(0,ln-2)]))
  if re.match(r'\s*(?:pub\s+)?const\s+',line) and 'b"' in line:constants.append(dict(line=ln,text=line.strip()))
  if re.match(r'\s*use\b',line):imports.append(dict(line=ln,text=line.strip()))
 inventory[str(p)]=dict(sha256=sha(p),functions=functions,wire_constants=constants,imports=imports)
# Later targeted receipts and predecessors, compared per exact current file.
RECEIPTS=['foundation-v13','catalogue-v5','portfolio-grid-v2','spatial-counts-v2','address-fixture-v5','grid-counts-fixture-v2','grid-feedback-fixture-v1','grid-interval-fixture-v1','native-quality-v10','native-regression-v3','native-final-source-v3','installed-discovery-v1']
receipts={}
for name in RECEIPTS:
 d=J/name;src=d/'source.json';s=json.loads(src.read_text());inputs[str(src)]=sha(src);b=s.get('sha256',s.get('source_files_sha256',s.get('native_file_hashes',{})));bindings={}
 for rel,value in b.items():
  p=ROOT/rel if (ROOT/rel).is_file() else N/rel;expected=value.get('sha256') if isinstance(value,dict) else value
  if str(p) in inventory or p==N/'Cargo.lock' or p==N/'Cargo.toml' or (p.is_file() and '/tests/' in str(p)):
   current=sha(p) if p.is_file() else None;bindings[str(p)]=dict(recorded=expected,current=current,status='MATCH' if expected==current else 'CHANGED_OR_MISSING')
 receipt=d/'receipt.json';sched=d/'scheduler-output.json';raw={};phases={};tests=[]
 if receipt.exists():
  raw=json.loads(receipt.read_text());inputs[str(receipt)]=sha(receipt)
  phases=raw.get('phases',{})
  if not phases and isinstance(raw,dict):phases={k:v for k,v in raw.items() if isinstance(v,dict) and ('argv' in v or 'returncode' in v)}
 if sched.exists():
  o=json.loads(sched.read_text());inputs[str(sched)]=sha(sched);status=dict(exit=o.get('exit_code'),cgroup_verified=o.get('cgroup_verified'))
 else:status=dict(producer_status=raw.get('status'),phases={k:v.get('returncode') for k,v in phases.items()})
 checks=d/'checks.json'
 if checks.exists():
  inputs[str(checks)]=sha(checks)
  for i,c in enumerate(json.loads(checks.read_text())):phases['check'+str(i)]=dict(argv=c['command'],returncode=c['exit_code'])
 for phase,pinfo in phases.items():
  log=Path(pinfo['stdout']) if pinfo.get('stdout') else None
  if log and log.is_file() and log.stat().st_size<2_000_000:
   inputs[str(log)]=sha(log)
   for line in log.read_text(errors='replace').splitlines():
    if line.startswith('test ') and not line.startswith('test result:'):tests.append(dict(phase=phase,test=line))
 if not tests and (d/'raw').exists():
  for log in (d/'raw').glob('*.stdout.log'):
   if log.stat().st_size<2_000_000:
    inputs[str(log)]=sha(log)
    tests += [dict(phase='raw stdout',test=l) for l in log.read_text(errors='replace').splitlines() if l.startswith('test ') and not l.startswith('test result:')]
 receipts[name]=dict(source_manifest=str(src),source_manifest_sha256=sha(src),status=status,bindings=bindings,phases={k:dict(argv=v.get('argv'),returncode=v.get('returncode')) for k,v in phases.items()},named_test_results=tests,note='Retained run only; matched individual source file does not prove unchanged full dependency/provider closure. Generator jobs prove fixture provenance, not native parity.')
# Source identity and reference AST, no Python imports/execution.
rows=[]
for e in entries:
 name=e['runtime_module'];p=ROOT/'runtime/cix_runtime'/name;s=p.read_text();a=ast.parse(s);inputs[str(p)]=sha(p);defs=[dict(name=n.name,line=n.lineno) for n in a.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef))];imp=[dict(line=n.lineno,text=ast.get_source_segment(s,n)) for n in a.body if isinstance(n,(ast.Import,ast.ImportFrom))];wires=[]
 for n in ast.walk(a):
  if isinstance(n,ast.Constant) and isinstance(n.value,bytes) and 3<=len(n.value)<=24 and re.match(rb'[A-Z]{3}',n.value):wires.append(dict(line=n.lineno,hex=n.value.hex(),display=repr(n.value)))
 targets=[native(x) for x in M[name][0]]
 if name=='cli.py':targets=[N/'src/cli.rs']
 if name=='legacy/multinomial.py':targets+=[N/'src/rank.rs',N/'src/combinatorics.rs']
 if name=='backends.py':targets+=[N/'src/paq_bridge.rs',N/'src/paq_supervisor.rs']
 def symbols(wanted):
  return [dict(path=str(t),sha256=inventory[str(t)]['sha256'],**f) for t in targets for f in inventory[str(t)]['functions'] if f['name'] in wanted]
 enc=symbols(M[name][1]);dec=symbols(M[name][2]);proof=[];gaps=[]
 for rn,rc in receipts.items():
  relevant={str(t):rc['bindings'][str(t)] for t in targets if str(t) in rc['bindings']}
  if relevant:proof.append(dict(receipt=rn,source_bindings=relevant,scope='Only named tests/phases in receipts.json; file-level binding, not blanket module compatibility.',independent_acceptance='NOT_ESTABLISHED_BY_THIS_LOCAL_RECEIPT'))
 if name in ['legacy/sdf_geometry.py','legacy/sdf_hydrogen.py']:
  status='INDEPENDENT_ACCEPTED_SELECTED_FRAME_CLOSURE';scope=('Six SDFG mode0–2/reps0–1 plus nine palette mode0–2/sizes1,2,64 and one65-vector boundary; exact bytes/crossdecode/output/malformed cases' if name.endswith('sdf_geometry.py') else 'Twelve SDFH model0–2/choice-rep0–3/radius6200; full bytes/crossdecode; selected literal/line/signedzero/output/malformed cases')
  proof.append(dict(receipt='CIX-128',root_terminal='48718aac-e87e-4694-87bd-bbf26dd3049f',independent_acceptance='ecb000bb-b42d-45ba-bd5f-aa23053fb016',candidate_manifest_sha256='7817e61b048693096be8faba39bcda5004152a0d2d37cbcb60d33cec5fa15cc4',commit='557ae2ff4296b1fe054567585a903efa84d6dec3',scope=scope));gaps=['Selected fixtures only; not every possible input/model parameter, outer CIXG01/CIXQ01 PAQ envelope, CLI/SDK or RC55.']
 elif name in ['__init__.py','legacy/__init__.py']:
  status='NAMESPACE_ONLY_NO_CODEC_WIRE';scope='AST confirms no function/class/import; version/docstring namespace metadata. No encoder/decoder wire applies.';gaps=['Package/runtime integration is a separate consumer/CLI obligation.']
 elif name=='legacy/ecoff_call_entries.py':
  status='EXPLICIT_INTERFACE_AND_PROOF_GAP';scope='Reference ECBR2 transform(mode0–5)/inverse located; no corresponding call-entry transform/inverse or ECBR2 marker in inspected address/dispatch/catalogue counterpart.';gaps=['Map current callable encoder/decoder or implement under fresh root contract after checking exact retained full source; section/pdata presence does not prove ECBR2.']
 elif name=='legacy/ecoff_relocated_pointers.py':
  status='EXPLICIT_INTERFACE_AND_PROOF_GAP';scope='relocated_pointer_candidates discovery exists; standalone ECRP1 transform/inverse not located in selected counterpart.';gaps=['Discovery is not an ECRP1 encoder/inverse proof; reconcile whether standalone historical route remains required.']
 elif name=='legacy/ecoff_pdata.py':
  status='TEST_ONLY_SUBSET_EXPLICIT_PRODUCTION_GAP';scope='pdata_transform mode1 helper marked cfg(test); ECPD1 fixture subset only, production uses combined ECPD2.';gaps=['Reference ECPD1 broader modes not proven; owner must explicitly disposition retained standalone contract, not infer qualification from ECPD2.']
 else:
  status='PRESENT_WITH_SCOPED_RETAINED_EVIDENCE_OR_GAP';scope='Current source counterpart/symbols and individually matched/changed predecessor pins recorded. Named retained phases do not establish complete reference-module parity.';gaps=['No independently accepted complete per-module mode/wire/parameter matrix located in the admitted evidence set; missing scope stays explicit.']
 if name=='cli.py':enc=symbols(['main_entry','encode_selected']);dec=[];gaps+=['CLI main_entry drives decoding via core/runtime; dedicated current decoder call closure not bound here.']
 if name=='model.py':scope='Reference Candidate dataclass vs native catalogue Candidate/Recipe declarations; orchestration schema, no direct encoder/decoder function.'
 if name=='regions.py':scope='Input recognition/region boundaries, no archive encoder/decoder defined by reference itself; region-enclosing route proof separate.'
 row=dict(module=name,family=e['family'],reference=dict(path=str(p),sha256=sha(p),definitions=defs,imports=imp,wire_literals=wires),historical_map=e,current_native=[dict(path=str(t),sha256=inventory[str(t)]['sha256']) for t in targets],encoder=enc or {'gap_or_not_applicable':scope},decoder=dec or {'gap_or_not_applicable':scope},native_wire_constants=[dict(path=str(t),**c) for t in targets for c in inventory[str(t)]['wire_constants']],wire_scope='Exact observed reference/native literals and locations; outer subtype association is explicit only where interface/receipt establishes it. No generic CIXB ID substitutes for a missing mapping.',owner=dict(product_integrator_task='01a0f927-3e23-7cb1-bdc3-cb7d08783ade',historical_alias=e['native_owner'],current_specialist_lease='UNAVAILABLE_NOT_INFERRED',proof_map_executor='01a10bd3-7412-77c3-a13c-b2ad4710b4ac',ledger_writer='01a103be-69f6-76b1-aa46-b1c65331c533'),status=status,proof_scope=scope,proofs=proof,gaps=gaps)
 rows.append(row)
for p in [oldmap,ROOT/'AGENTS.md',N/'Cargo.toml',N/'Cargo.lock',OLD/'observations.json',OLD/'dossier-manifest.json',OLD/'READINESS.md']:
 inputs[str(p)]=sha(p)
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip();dirty=subprocess.check_output(['git','status','--porcelain','--','rust/cix-native','runtime/cix_runtime'],cwd=ROOT,text=True)
(OUT/'source-manifest.json').write_text(json.dumps(inputs,indent=2)+'\n');(OUT/'native-interface-inventory.json').write_text(json.dumps(inventory,indent=2)+'\n');(OUT/'receipts.json').write_text(json.dumps(receipts,indent=2)+'\n');(OUT/'proof-map.json').write_text(json.dumps(dict(schema='cix130-current-proof-map-v1',as_of_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),branch=branch,head=head,dirty_relevant_paths=dirty.splitlines(),point_in_time_not_whole_tree_freeze=True,rows=rows,scope='Evidence reconciliation only; selected proof/partial/gap, not full41 or RC55 acceptance.'),indent=2)+'\n')
print(json.dumps(dict(rows=len(rows),source_inputs=len(inputs),native_interfaces=len(inventory),receipts=len(receipts),head=head,status_counts={status:sum(x['status']==status for x in rows) for status in sorted({x['status'] for x in rows})})))
