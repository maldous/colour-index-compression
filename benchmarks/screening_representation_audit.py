#!/usr/bin/env python3
"""One-off, read-only analysis of retained screening evidence. Runs no codecs."""
import argparse, csv, hashlib, json, subprocess
from collections import Counter
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/research/2026-09-30-representation-benefits'
NAMES = {'fcbench-msg':'MSG numerical data','fcbench-mhd':'MHD simulation','golf':'GitHub events · prefix','fcbench-pt-heldout':'PT simulation · held-out range','fcbench-rsim-heldout':'RSim · near-constant held-out range','golf-heldout':'GitHub events · held-out range'}
ROUTES = {'raw':'Raw storage','runs':'Run-only','composition':'Direct CIX composition','lz':'LZ separated streams','predictor':'Causal prediction residuals','bwt':'BWT → MTF → runs','stride':'Delta/XOR + byte planes','phrases':'Input-derived phrase dictionary','ppm':'Contextual PPM','mixture':'Fixed-point predictor mixture','deflate':'Original bytes → DEFLATE'}
BACKENDS = ['raw','cix','deflate','hybrid','count-range','ppm','mixture']
PROFILES = {'current':'Current / balanced','fast':'Speed / fast','size':'Size / maximum'}
SOURCE_DIRS = ['generic-pipeline','representation-coverage','codec-profiles']
def read(p): return json.loads(p.read_text())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def effective(r):
    route=r['config']['force']
    return {'raw':'raw','runs':'raw','composition':'cix','deflate':'deflate','ppm':'ppm','mixture':'mixture'}.get(route,r['config'].get('backend','hybrid'))
def resource(r):
    # Single-core lanes differ, but have the same allowed one-core allocation.
    return {k:v for k,v in r['_receipt']['budget'].items() if k!='cpu'}
def matched(a,b):
    ai,bi=a['_receipt']['identity'],b['_receipt']['identity']
    return (a['input_sha256']==b['input_sha256'] and ai['input']==bi['input'] and
            ai['build_sha256']==bi['build_sha256'] and ai['initial_state']==bi['initial_state'] and
            resource(a)==resource(b) and a['config']['effort']==b['config']['effort'] and
            effective(a)==effective(b))
def get_archive(r):
    rec=r['_receipt'];p=Path(rec['artifacts']['archive']); assert p.stat().st_size==r['bytes'];assert sha(p)==r['archive_sha256']
    if r['status']=='VERIFIED_SCREENING':
        v=r['verification'];assert v['matched'] and v['source_sha256']==v['restored_sha256']==r['input_sha256']
        assert 'archive only' in rec['independent_decode']
        restored=Path(rec['artifacts']['restored']);assert sha(restored)==r['input_sha256']
        inp=rec['identity']['input']
        with Path(inp['path']).open('rb') as f:f.seek(inp['offset']); original=f.read(inp['length'])
        assert hashlib.sha256(original).hexdigest()==r['input_sha256'] and original==restored.read_bytes()
        assert sum(v for v in r['accounting'].values() if isinstance(v,int))+54==r['bytes']
    return p

def info(r):
    if not r:return None
    return {k:r.get(k) for k in ('cell_id','label','config','bytes','archive_sha256','input_sha256','verification','encode','decode','accounting','receipt','failure_reason')} | {'effective_backend':effective(r),'budget':r['_receipt']['budget'],'source_hashes':r['_receipt']['identity']['build_sha256'],'initial_state':r['_receipt']['identity']['initial_state'],'evidence_source':r['_source'],'independent_decode':r['_receipt'].get('independent_decode'),'commands':[p['command'] for p in r['_receipt']['phases']]}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=OUT);ap.add_argument('--site-root',type=Path);args=ap.parse_args();out=args.output;out.mkdir(parents=True,exist_ok=True)
    originals={};sources=[]
    for name in SOURCE_DIRS:
        p=ROOT/f'docs/research/2026-09-30-{name}/results.json';sources.append({'path':str(p.relative_to(ROOT)),'sha256':sha(p)})
        for r in read(p):
            if r['label'] in NAMES and r['config'].get('force') in ROUTES:
                r['_source']=str(p.relative_to(ROOT));r['_receipt']=read(Path(r['receipt']))
                if r['cell_id'] in originals:assert originals[r['cell_id']]['archive_sha256']==r['archive_sha256']
                else:originals[r['cell_id']]=r
    trials=list(originals.values());assert len(trials)==102;assert all(r['config']['effort']=='maximum' and r['original_bytes']==16384 for r in trials)
    for r in trials:get_archive(r)
    failed=[r for r in trials if r['status']!='VERIFIED_SCREENING'];assert len(failed)==6 and all(r['config']['force']=='mixture' for r in failed)
    controls=[r for r in trials if r['config']['force'] in ('raw','composition','deflate','ppm') and r['status']=='VERIFIED_SCREENING']
    cells=[]
    for profile in PROFILES:
        for backend in BACKENDS:
            for label in NAMES:
                for route in ROUTES:
                    cell={'profile':profile,'backend':backend,'slice':label,'slice_name':NAMES[label],'representation':route,'representation_name':ROUTES[route],'status':'NOT MEASURED','delta_bytes':None,'delta_percent':None,'control_bytes':None,'complete_bytes':None,'encode_delta_seconds':None,'decode_delta_seconds':None,'reason':'No forced representation trial at this profile and backend.','candidate':None,'control':None}
                    candidates=[r for r in trials if profile=='size' and r['label']==label and r['config']['force']==route and effective(r)==backend]
                    if candidates:
                        assert len(candidates)==1
                        r=candidates[0];cell['candidate']=info(r)
                        if r['status']!='VERIFIED_SCREENING':cell.update(status='UNQUALIFIED',reason='Four-second route budget exceeded. The 13-byte partial header is not a completed archive; failed reconstruction is not a size result.')
                        else:
                            cell['complete_bytes']=r['bytes']
                            eligible=[b for b in controls if b['label']==label and matched(r,b)]
                            if not eligible:
                                cell['reason']='Completed exact archive, but no unchanged-input control matches effective backend, effort, source snapshot, initial state and all outer resource caps. Comparison unavailable.'
                            else:
                                assert len(eligible)==1;b=eligible[0];delta=r['bytes']-b['bytes']
                                cell.update(status='WIN' if delta<0 else 'LOSS' if delta>0 else 'TIE',delta_bytes=delta,delta_percent=delta/b['bytes']*100,control_bytes=b['bytes'],encode_delta_seconds=round(r['encode']['seconds']-b['encode']['seconds'],8),decode_delta_seconds=round(r['decode']['seconds']-b['decode']['seconds'],8),control=info(b),reason='Unchanged-input anchor compared with itself; not an additional representation benefit.' if r['cell_id']==b['cell_id'] else 'Same effective coding policy, settings, snapshot, reset state and resource caps; complete physical sizes and independent exact restoration.')
                    cells.append(cell)
    # Main 6x11 matrix selects a supported comparison, never a cross-backend delta.
    main_cells=[]
    for profile in PROFILES:
        for label in NAMES:
            for route in ROUTES:
                pool=[c for c in cells if c['profile']==profile and c['slice']==label and c['representation']==route]
                supported=[c for c in pool if c['delta_bytes'] is not None]
                if supported:assert len(supported)==1;chosen=supported[0]
                else:chosen=next((c for c in pool if c['status']=='UNQUALIFIED'),next((c for c in pool if c['candidate'] and c['backend']=='hybrid'),next((c for c in pool if c['candidate']),pool[3])))
                main_cells.append(chosen | {'view':'supported'})
    wins=[c for c in main_cells if c['status']=='WIN'];assert len(wins)==11
    # Preserve selection measurements by profile separately, with matched ablations only for balanced development.
    generic=read(ROOT/'docs/research/2026-09-30-generic-pipeline/results.json');profiles=read(ROOT/'docs/research/2026-09-30-codec-profiles/results.json')
    selected=[]
    for profile in PROFILES:
        for label in NAMES:
            pool=[r for r in generic if r['label']==label and r['config']=={'mode':'pipeline','effort':'balanced'}] if profile=='current' else [r for r in profiles if r['label']==label and r['config'].get('method')=='cix' and r['config'].get('profile')==profile]
            assert len(pool)==1;r=pool[0]
            if profile=='current':enc=r['encode']['seconds'];dec=r['decode']['seconds'];reps=1;routes=r['codec']['route_usage_source_bytes'];em=r['encode']['peak_rss_kib']/1024;dm=r['decode']['peak_rss_kib']/1024
            else:
                # Source report contains median aggregate encode/decode fields.
                enc=r['encode']['seconds'];dec=r['decode']['seconds'];reps=3;routes=r['codec']['route_usage_source_bytes'];em=r['encode']['peak_rss_kib']/1024;dm=r['decode']['peak_rss_kib']/1024
            selected.append({'profile':profile,'slice':label,'bytes':r['bytes'],'encode_seconds':enc,'decode_seconds':dec,'encode_rss_mib':em,'decode_rss_mib':dm,'repetitions':reps,'routes':routes,'cell_id':r['cell_id'],'receipt':r['receipt']})
    ablations=[]
    for r in generic:
        if r['label'] in NAMES and r['config'].get('disable'):
            base=next(b for b in generic if b['label']==r['label'] and b['config']=={'mode':'pipeline','effort':'balanced'})
            a,b=read(Path(r['receipt'])),read(Path(base['receipt']))
            assert r['verification']['matched'] and a['identity']['input']==b['identity']['input'] and a['identity']['build_sha256']==b['identity']['build_sha256'] and {k:v for k,v in a['budget'].items() if k!='cpu'}=={k:v for k,v in b['budget'].items() if k!='cpu'}
            ablations.append({'profile':'current','slice':r['label'],'disabled':r['config']['disable'][0],'selected_bytes':base['bytes'],'disabled_bytes':r['bytes'],'route_contribution_bytes':r['bytes']-base['bytes'],'cell_id':r['cell_id'],'receipt':r['receipt'],'control_receipt':base['receipt']})
    blocked=read(ROOT/'docs/research/2026-09-30-codec-profiles/blocked.json');assert len(blocked)==6
    registry=[r for r in read(ROOT/'docs/research/2026-09-30-generic-pipeline/inputs.json') if r['label'] in NAMES]
    categories={
      'multiple_slices':[{ 'representation':route,'slices':[c['slice'] for c in wins if c['representation']==route]} for route in ROUTES if sum(c['representation']==route for c in wins)>1],
      'particular_slices':'Run-only wins on MHD and near-constant RSim, but loses on MSG, PT and both Golf ranges. CIX-only predictor/BWT win on MHD and Golf, lose on MSG; CIX-only planes win on MSG/MHD, lose on Golf. LZ wins on all three tested CIX-controlled development slices. No representation has a demonstrated win on exactly one slice.',
      'no_demonstrated_benefit':'Phrase dictionary: finished archives but no matching original hybrid control. Raw, composition, PPM and original-byte DEFLATE are unchanged-input anchors, not transformation gains. Mixer: six unqualified trials. This is not proof of absence of benefit.',
      'unresolved':'Need targeted unchanged-input hybrid and count-range controls; legacy DEFLATE control with identical 300 s / 250 MB caps; controlled forced routes under balanced and fast; transformed CIX trials on exposed held-out ranges; affordable mixer configuration and larger unexposed inputs. No new trials were run for this report.'}
    doc={'schema':1,'evidence_cutoff':'Retained measurements through 2026-09-30; one-off audit, no experiment sweep','research_commit_at_audit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'pipeline_sha256':sha(ROOT/'cix/pipeline.py'),'formulas':{'delta_bytes':'candidate_complete_bytes - control_complete_bytes','delta_percent':'100 * delta_bytes / control_complete_bytes','negative':'improvement'},'profiles':PROFILES,'backends':BACKENDS,'representations':ROUTES,'slice_names':NAMES,'inputs':registry,'sources':sources,'matrices':main_cells,'backend_matrices':cells,'selected_results':selected,'ablations':ablations,'memory_exclusions':blocked,'categories':categories,'notes':[
      'All six inputs are 16,384-byte screening slices, not full datasets. Previously held-out ranges are now exposed.',
      'All forced representation trials used maximum effort: 65,536-byte blocks, no retained history, 4 s route wall budget, 512 MiB worker address-space cap. Current balanced and speed fast have no paired forced-route evaluations.',
      'Legacy outer caps: 300 s, 2,000,000,000 B RSS, 250,000,000 B temporary. New extension: 60 s, same RSS, 100,000,000 B temporary. Different caps are not treated as matched, even if neither trial exhausted them.',
      'One pinned physical core per process; equivalent lanes 16–19, aggregate four cores / 12 GB / 4 GB. Lane and thermal/cache differences plus one repetition make time deltas observations, not statistically verified speed claims.',
      'CIX-only backend means per-stream raw/run/exact-rank portfolio with the same entropy gate, not every stream necessarily rank-coded. DEFLATE backend similarly retains raw/run alternatives. Hybrid adds both portfolios. Composition ignores requested hybrid backend and calls streams(original,cix); deflate forces streams(original,deflate).',
      'Complete bytes include 13-byte file header, 41-byte block frame, 41-byte end frame, transforms, dictionaries, counts, descriptors, all payload and checksums. Accounting fields sum to archive bytes minus 54; framing_bytes includes the block frame.',
      'TIE anchors compare an unchanged-input archive with itself and do not constitute independent experiments or representation benefits. NOT MEASURED also means comparison unavailable despite a verified candidate archive; reason and complete size are retained.',
      'Peak RSS records the timed parent process and is not aggregate worker-tree peak. Cgroup sampled high-water is a lower bound. Incremental decoder/program packaging is not included in these archive-only comparisons; no full-submission claim.',
      'PAQ v216 -8 vs transformed CIX uses a different backend; those pipeline comparisons cannot isolate representation gain. Six PAQ -12L/five-layer rows are memory exclusions, not failed runs. No other memory-excluded representation trial is recorded in these screening files.'
    ]}
    (out/'matrix.json').write_text(json.dumps(doc,indent=2)+'\n')
    fields=['profile','backend','slice','slice_name','representation','representation_name','status','delta_bytes','delta_percent','control_bytes','complete_bytes','encode_delta_seconds','decode_delta_seconds','reason']
    for name,rows in [('matrix.csv',main_cells),('backend-matrices.csv',cells)]:
        with (out/name).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows({k:c[k] for k in fields} for c in rows)
    def table(rows):
        s='| Slice | '+' | '.join(ROUTES.values())+' |\n|---|'+'---|'*len(ROUTES)+'\n'
        for label in NAMES:
            values=[]
            for route in ROUTES:
                c=next(c for c in rows if c['slice']==label and c['representation']==route)
                value=f"{c['delta_bytes']:+,} B ({c['delta_percent']:+.2f}%) · {c['status']} · {c['backend']}" if c['delta_bytes'] is not None else f"— B / — % · {c['status']}"
                if c['status']=='NOT MEASURED' and c['complete_bytes'] is not None:value+=f"; archive {c['complete_bytes']:,} B"
                values.append(value)
            s+='| '+NAMES[label]+' (`'+label+'`) | '+' | '.join(values)+' |\n'
        return s
    md='# CIX screening representation benefits — one-off matched-control audit\n\n'+'\n\n'.join(doc['notes'])+'\n\nNegative changes mean smaller complete archives. No missing delta is imputed as zero. Percent denominator is the matched compressed baseline, not original input size.\n'
    for profile in PROFILES:md+='\n## '+PROFILES[profile]+' — 6 × 11 supported-comparison matrix\n\n'+table([c for c in main_cells if c['profile']==profile])
    md+='\n## Verified matched representation benefits and observed timing\n\n| Slice | Representation / backend | Control → complete B | Change B / % | Encode s (control → candidate) | Decode s | Observed tradeoff |\n|---|---|---|---|---|---|---|\n'
    for c in wins:
        a,b=c['candidate'],c['control'];e,d=c['encode_delta_seconds'],c['decode_delta_seconds'];trade='size + observed speed' if e<=0 and d<=0 and (e<0 or d<0) else 'size; observed times tie' if e==d==0 else 'size/speed trade-off'
        md+=f"| {c['slice']} | {c['representation_name']} / {c['backend']} | {b['bytes']:,} → {a['bytes']:,} | {c['delta_bytes']:+,} / {c['delta_percent']:+.3f}% | {b['encode']['seconds']:.2f} → {a['encode']['seconds']:.2f} | {b['decode']['seconds']:.2f} → {a['decode']['seconds']:.2f} | {trade} |\n"
    summaries=[]
    md+='\n## One summary per slice\n'
    for label in NAMES:
        ww=[c for c in wins if c['slice']==label];best=min(ww,key=lambda c:c['complete_bytes']) if ww else None
        reps=', '.join(c['representation_name']+' / '+c['backend'] for c in ww) or 'None established against a matching unchanged-input control'
        md+='\n### '+label+' — '+NAMES[label]+'\n\nVerified gains: '+reps+'.\n\n'
        if best:
            a,b=best['candidate'],best['control'];md+=f"Strongest matched benefit: {best['representation_name']} / {best['backend']}, {b['bytes']:,} → {a['bytes']:,} B ({best['delta_bytes']:+,} B, {best['delta_percent']:+.3f}%). Encode {b['encode']['seconds']:.2f} → {a['encode']['seconds']:.2f} s ({best['encode_delta_seconds']:+.2f}); decode {b['decode']['seconds']:.2f} → {a['decode']['seconds']:.2f} s ({best['decode_delta_seconds']:+.2f}).\n\n"
        else:md+='Strongest isolated representation benefit / baseline / timing changes: unavailable. No matching positive comparison exists.\n\n'
        for s in [s for s in selected if s['slice']==label]:md+=f"- {PROFILES[s['profile']]} selected {s['bytes']:,} B, {next(iter(s['routes']))}, encode/decode {s['encode_seconds']:.2f}/{s['decode_seconds']:.2f} s; n={s['repetitions']}.\n"
        if label=='fcbench-msg':decision='The CIX-only stride gain loses to the 12,746 B hybrid phrase archive. Separately, a matched CURRENT selector ablation proves phrases improve its overall selection by 328 B (13,074 → 12,746), although the missing original hybrid control prevents isolating the phrase transform itself. All other CURRENT route ablations tie.'
        elif label=='fcbench-mhd':decision='LZ / CIX reaches the selected 500 B. A CURRENT matched selector ablation proves its incremental overall benefit is 42 B (without LZ 542 → 500), not the entire 2,758 B saving against composition. Other CURRENT ablations tie.'
        elif label=='golf':decision='Original-byte DEFLATE at 2,853 B remains smaller than the strongest supported transformed CIX archive (LZ 3,045 B). None of the transformed route CURRENT ablations improves selection; removing original-byte DEFLATE costs 136 B (2,989 → 2,853).'
        elif label=='fcbench-pt-heldout':decision='The verified 12,749 B hybrid stride archive is selected in all three profiles. Unchanged-input hybrid control is missing, so a representation-only delta and time change cannot be attributed. No held-out route ablation establishes an incremental selector contribution.'
        elif label=='fcbench-rsim-heldout':decision='Run-only / raw reaches the 103 B selected archive. It is 10 B smaller than the measured 113 B composition and original-DEFLATE anchors, but there is no matching CURRENT/FAST/SIZE selector-removal ablation on this range. The slice is 16,383 zero bytes and one byte 64; do not generalise to entire RSim.'
        else:decision='Original-byte DEFLATE is best at 2,770 B and is selected in all profiles. No matching transformed CIX/hybrid control is available; its transformed archives do not establish an attributable gain. No selector-removal ablation is available.'
        summaries.append({'slice':label,'verified_gains':[c['representation'] for c in ww],'strongest':best,'decision':decision})
        md+='\n'+decision+' Forced-route encode times do not include the whole adaptive selector search; those costs are separately measured above.\n'
    md+='\n## Unqualified and memory-excluded\n\nSix fixed-point mixture trials exceeded 4 s route budgets and failed restoration. Their 13 B partial headers have no qualified size, percentage, rank or useful decode timing. All remain UNQUALIFIED.\n\nPAQ maximum v216 -12L with five LSTM layers was not launched on any slice: approximately 29 GB plus LSTM state exceeds the aggregate 12 GB cap. These six RESOURCE_LIMIT exclusions remain outside representation rankings. Huffman and ANS/FSE are unimplemented, not memory exclusions.\n'
    md+='\n## Final findings\n\n1. Multiple-slice benefits: '+ '; '.join(ROUTES[x['representation']]+': '+', '.join(x['slices']) for x in categories['multiple_slices'])+'.\n2. Particular-slice limitations: '+categories['particular_slices']+'\n3. No demonstrated benefit: '+categories['no_demonstrated_benefit']+'\n4. Unresolved targeted follow-up: '+categories['unresolved']+'\n'
    md+='\n## Reproduction and references\n\nRun `python benchmarks/screening_representation_audit.py` from the private repository. It invokes no compressor or decoder; it recalculates matrices and rechecks retained physical artifacts, exact decoded bytes, SHA-256, full accounting, source/configuration identities and resource matches.\n\n'
    for src in sources:md+=f"- [{src['path']}](../{src['path'].split('/')[-2]}/results.json), SHA-256 `{src['sha256']}`.\n"
    md+='\n`matrix.json` carries both cell identities, raw commands, source hashes, budgets, accounting, independent-decode receipts and every observed candidate size. `backend-matrices.csv` enumerates all 3 × 7 × 6 × 11 backend cells. `matrix.csv` enumerates the 3 × 6 × 11 supported-comparison cells. No broad sweep or targeted experiment was launched.\n'
    doc['slice_summaries']=summaries
    (out/'matrix.json').write_text(json.dumps(doc,indent=2)+'\n')
    (out/'REPORT.md').write_text(md)
    if args.site_root:
        target=args.site_root/'dist/data';target.mkdir(exist_ok=True)
        for name in ('matrix.json','matrix.csv','backend-matrices.csv','REPORT.md'):(target/('representation-benefits-'+name)).write_bytes((out/name).read_bytes())
        # Existing public receipt names use the immutable cell identity.
        for r in trials:
            dest=target/'receipts'/f"{r['cell_id']}.json";dest.parent.mkdir(exist_ok=True);dest.write_bytes(Path(r['receipt']).read_bytes())
    print(json.dumps({'trials':len(trials),'verified':len(trials)-len(failed),'unqualified':len(failed),'wins':len(wins),'matched_comparisons':sum(c['delta_bytes'] is not None for c in main_cells),'matrix_cells':len(main_cells),'backend_cells':len(cells),'output':str(out)}))
if __name__=='__main__':main()
