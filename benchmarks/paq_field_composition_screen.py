"""Paid conditional-composition size screen with causal instruction contexts.

This computes exact type-class rank widths and explicit count/dictionary costs.
It does not emit a compressed stream or implement the causal replay decoder.
Only a favorable screen would justify that implementation. No leaderboard score.
"""
import argparse
from collections import Counter
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path
import struct
import numpy as np
from benchmarks import ecoff_instruction_loss as layout, ecoff_call_trace_analysis as mapping
from cix.multinomial import vencode

# Fixed schema dictionary, not learned from input symbol values or test corpus.
FIELDS=['Opcode','Fp.Function','Fp.Ra','Fp.Rb','Fp.Rc','Mfc.Function','Mfc.Ra','Mfc.Rb',
        'Opr.Bit','Opr.Function','Opr.Ra','Opr.Literal','Opr.Rb','Opr.Unused','Opr.Rc',
        'Mbr.Ra','Mbr.Rb','Mbr.Displacement','Bra.Ra','Bra.Displacement',
        'Mem.Ra','Mem.Rb','Mem.Displacement','Pcd.Function','Nop.Function']


def labels(word, position, previous_opcode=64):
    """All labels depend only on instruction bits before this position."""
    if position < 6:
        name='Opcode';start=0;opcode=64
    else:
        opcode=word>>26;kind,fields=layout.schema(opcode,word);start=6
        for field,width in fields:
            if start<=position<start+width:name=kind+'.'+field;break
            start+=width
        else:raise ValueError('unmapped instruction position')
    role=FIELDS.index(name)+1
    return (role, 1+opcode*len(FIELDS)+role-1, 1+32*(role-1)+position-start,
            1+previous_opcode if position<6 else 66+role)


@lru_cache(maxsize=200000)
def rank_bytes(n,k):return ((math.comb(n,k)-1).bit_length()+7)//8


def counts_cost(n,k):return len(vencode(n))+len(vencode(k))+rank_bytes(n,k)


def analyze(folder):
    folder=Path(folder);proof=json.loads((folder/'complete.json').read_text())
    source=(folder/'source.bin').read_bytes();trace=(folder/'predictions.u32').read_bytes()
    sha=lambda b:hashlib.sha256(b).hexdigest()
    if not proof['round_trip'] or not proof['trace_equals_reference']:raise ValueError('unqualified source')
    if sha(source)!=proof['input_sha256'] or sha(trace)!=proof['trace_sha256']:raise ValueError('changed trace')
    records=np.frombuffer(trace,dtype='<u4');p=records&0x7fffffff;y=records>>31
    q=np.minimum(p,0x80000000-p).astype(np.uint64)
    if np.any(q==0):raise ValueError('zero predictive probability')
    errors=(y^(p>>30)).astype(np.uint64);outcome=mapping.outcome_bytes(records)
    contexts=np.zeros((5,len(records)),dtype=np.uint16);contexts[4]=np.arange(len(records),dtype=np.uint32)%8
    regions=0
    for off,size in layout.layout.objects(source):
        obj=source[off:off+size];sections=layout.layout.sections(obj)
        if not all(k in sections for k in (b'.text',b'.init',b'.fini')):continue
        start,n=sections[b'.text'];si,ni=sections[b'.init'];sf,nf=sections[b'.fini']
        if si!=start+n or sf!=si+ni:continue
        code=mapping.shuffled_code(obj[start:start+n+ni+nf]);at=outcome.find(code)
        if at<0 or outcome.find(code,at+1)>=0:raise ValueError('ambiguous instruction region')
        previous=64;regions+=1
        for wi,(word,) in enumerate(struct.iter_unpack('>I',code)):
            for bit in range(32):contexts[:4,(at+wi*4)*8+bit]=labels(word,bit,previous)
            previous=word>>26
    rows=[];exp=np.floor(np.log2(q)).astype(np.uint64);base=np.left_shift(np.uint64(1),exp)
    for subbits in range(4):
        bucket=(exp<<subbits)+(((q-base)<<subbits)//base)
        buckets=31<<subbits;details=[]
        for index in range(buckets):
            selected=bucket==index;n=int(np.sum(selected));k=int(np.sum(errors[selected]));plain=counts_cost(n,k) if n else len(vencode(0))
            candidates=[]
            if n:
                for family in range(len(contexts)):
                    ids=contexts[family,selected];maxid=int(ids.max())+1
                    ns=np.bincount(ids,minlength=maxid);ks=np.bincount(ids,weights=errors[selected],minlength=maxid).astype(np.int64)
                    active=np.flatnonzero(ns);cost=len(vencode(len(active)));previous_id=-1
                    for ident in active:
                        cost+=len(vencode(int(ident)-previous_id-1))+counts_cost(int(ns[ident]),int(ks[ident]));previous_id=int(ident)
                    candidates.append(cost)
            winner=min([plain,*candidates]);choice=[plain,*candidates].index(winner)
            details.append(dict(bucket=index,events=n,errors=k,unpartitioned_bytes=plain,
                context_bytes=candidates,selected=choice,selected_bytes=winner+(1 if n else 0)))
        # Match the existing PAQ/CIX residual envelope; PAQ headers are 8 bytes here.
        header_bytes=5+3+8+len(vencode(len(source)))+4
        plain_total=header_bytes+sum(r['unpartitioned_bytes'] for r in details)
        selected_total=header_bytes+sum(r['selected_bytes'] for r in details)
        rows.append(dict(subbits=subbits,whole_composition_layout_bytes=plain_total,
            selected_layout_bytes=selected_total,delta_vs_native_bytes=selected_total-proof['physical_bytes'] if 'physical_bytes' in proof else selected_total-len((folder/'baseline.paq8px215').read_bytes()),
            selected_context_buckets=sum(r['selected']!=0 for r in details),buckets=details))
    return dict(complete=True,diagnostic_only=True,physical_codec=False,source_proof=proof,
        contexts=['instruction field','opcode and field','field and bit position','previous opcode for opcode bits','byte bit position'],
        code_regions=regions,rows=rows,source_hashes={str(Path(p)):sha(Path(p).read_bytes()) for p in [__file__,layout.__file__,mapping.__file__]},
        limitation='Exact proposed rank widths plus count/dictionary/selector layout; no native causal decoder exists. Not a compressed size or a full-member result.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source',default='results/leaderboard/ecoff-call-trace');parser.add_argument('--output',required=True);args=parser.parse_args()
    result=analyze(args.source);Path(args.output).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps([{k:v for k,v in row.items() if k!='buckets'} for row in result['rows']],indent=2))
