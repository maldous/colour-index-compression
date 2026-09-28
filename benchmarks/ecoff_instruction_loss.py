"""Attribute a qualified native PAQ trace to Alpha instruction fields.

Predictive bit loss is diagnostic, not a physical compressed size. Conditional
type-class uncertainty assumes transmitted counts and excludes their cost.
No value tables from this analysis are consumed by a compressor or decoder.
"""
import array
from collections import Counter,defaultdict
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
from benchmarks import ecoff_constraints as layout, ecoff_call_trace_analysis as mapping


def schema(op,word):
    if op in (0x14,0x15,0x16,0x17):return 'Fp',[('Function',11),('Ra',5),('Rb',5),('Rc',5)]
    if op==0x18:return 'Mfc',[('Function',16),('Ra',5),('Rb',5)]
    if op in (0x10,0x11,0x12,0x13,0x1c):
        rest=[('Literal',8)] if word>>25&1 else [('Rb',5),('Unused',3)]
        return 'Opr',[('Bit',1),('Function',7),('Ra',5),*rest,('Rc',5)]
    if op in (0x1a,0x34):return 'Mbr',[('Ra',5),('Rb',5),('Displacement',16)]
    if 0x30<=op<=0x3f:return 'Bra',[('Ra',5),('Displacement',21)]
    if 0x08<=op<=0x0f or 0x20<=op<=0x2f:return 'Mem',[('Ra',5),('Rb',5),('Displacement',16)]
    return ('Pcd' if op in (0,0x19,0x1b,0x1d,0x1e,0x1f) else 'Nop'),[('Function',26)]


def analyze(folder):
    folder=Path(folder);proof=json.loads((folder/'complete.json').read_text());sha=lambda b:hashlib.sha256(b).hexdigest()
    if not proof['round_trip'] or not proof['trace_equals_reference']:raise ValueError('unqualified trace')
    data=(folder/'source.bin').read_bytes();raw=(folder/'predictions.u32').read_bytes()
    if sha(data)!=proof['input_sha256'] or sha(raw)!=proof['trace_sha256']:raise ValueError('trace identity mismatch')
    events=array.array('I');events.frombytes(raw)
    if sys.byteorder!='little':events.byteswap()
    outcome=mapping.outcome_bytes(events);totals=defaultdict(lambda:dict(fields=0,raw_bits=0,paq_bits=0.))
    counts=defaultdict(Counter);conditional=defaultdict(lambda:defaultdict(Counter));locations=[]
    for off,size in layout.objects(data):
        obj=data[off:off+size];sections=layout.sections(obj)
        if not all(k in sections for k in (b'.text',b'.init',b'.fini')):continue
        start,n=sections[b'.text'];ni=sections[b'.init'];nf=sections[b'.fini']
        if ni[0]!=start+n or nf[0]!=ni[0]+ni[1]:continue
        n+=ni[1]+nf[1];shuffled=mapping.shuffled_code(obj[start:start+n]);at=outcome.find(shuffled)
        if at<0 or outcome.find(shuffled,at+1)>=0:raise ValueError('instruction region does not map uniquely')
        locations.append(dict(source_offset=off+start,trace_byte_offset=at,bytes=n))
        for i,(word,) in enumerate(struct.iter_unpack('>I',shuffled)):
            opcode=word>>26;kind,fields=schema(opcode,word);position=0
            for field,width in [('Opcode',6),*fields]:
                key='Opcode' if field=='Opcode' else kind+'.'+field
                if opcode==0x29 and (word>>16)&31==29 and field=='Displacement':key='GP.Displacement'
                value=(word>>(32-position-width))&((1<<width)-1);loss=0.
                for bit,record in enumerate(events[(at+i*4)*8+position:(at+i*4)*8+position+width]):
                    p,y=record&0x7fffffff,record>>31
                    if y!=((value>>(width-bit-1))&1):raise ValueError('instruction field trace mismatch')
                    loss-=math.log2((p if y else (1<<31)-p)/(1<<31))
                total=totals[key];total['fields']+=1;total['raw_bits']+=width;total['paq_bits']+=loss
                counts[key][value]+=1;conditional[key][opcode][value]+=1;position+=width
            if position!=32:raise ValueError('instruction schema did not cover all bits')
    cardinality_bits=lambda counter:(math.lgamma(sum(counter.values())+1)-sum(math.lgamma(n+1) for n in counter.values()))/math.log(2)
    rows=[]
    for key,row in totals.items():
        rows.append(dict(field=key,**row,paq_predictive_bytes=row['paq_bits']/8,observed_alphabet=len(counts[key]),
            global_type_class_bits=cardinality_bits(counts[key]),opcode_conditioned_type_class_bits=
                None if key=='Opcode' else sum(cardinality_bits(c) for c in conditional[key].values())))
    rows.sort(key=lambda r:r['paq_bits'],reverse=True)
    if sum(r['raw_bits'] for r in rows)!=sum(r['bytes'] for r in locations)*8:raise ValueError('field coverage mismatch')
    return dict(diagnostic_only=True,physical_codec=False,qualified_trace=proof,code_regions=locations,rows=rows,
        source_hashes={str(Path(p)):sha(Path(p).read_bytes()) for p in [__file__,layout.__file__,mapping.__file__]},
        total_raw_code_bits=sum(r['raw_bits'] for r in rows),total_paq_code_bits=sum(r['paq_bits'] for r in rows),
        note=__doc__)


if __name__=='__main__':
    result=analyze(sys.argv[1]);Path(sys.argv[2]).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result['rows'],indent=2))
