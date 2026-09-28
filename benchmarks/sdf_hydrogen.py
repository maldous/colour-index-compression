"""Integer geometry candidates and conditional permutation ranks.

The molecular skeleton gives the number of hydrogen slots without a count
header. Earlier heavy-atom coordinates determine those slots. Each slot is
used once, so arrangement choices shrink from h**h to h!. Exact coordinate
residuals retain arbitrary layouts, unusual structures and rounding. PAQ-text
choice digits and CIX mixed-radix ranks receive identical candidate sets.
"""
from math import isqrt,log2
from cix.multinomial import vencode,vdecode,_ArithmeticEncoder,_ArithmeticDecoder
from benchmarks.sdf_geometry import SEP,fixed,layout

MAGIC=b'SDFH\x01'
TURN=1<<32
ANGLES=(536870912,316933406,167458907,85004756,42667331,21354465,
    10679838,5340245,2670163,1335087,667544,333772,166886,83443,41722,
    20861,10430,5215,2608,1304,652,326,163,81,41,20,10,5,3,1,1)


def rounded(value,denominator):
    return (value+denominator//2)//denominator if value>=0 else -((-value+denominator//2)//denominator)


def angle(x,y):
    if not(x or y):raise ValueError('undefined direction')
    shift=max(0,40-max(abs(x),abs(y)).bit_length());x<<=shift;y<<=shift;base=0
    if x<0:x=-x;y=-y;base=TURN//2
    z=0
    for i,step in enumerate(ANGLES):
        if y>0:x,y,z=x+(y>>i),y-(x>>i),z+step
        elif y<0:x,y,z=x-(y>>i),y+(x>>i),z-step
        else:break
    return (base+z)%TURN


def direction(phase,radius):
    z=(phase+TURN//2)%TURN-TURN//2;sign=1
    if z>TURN//4:z-=TURN//2;sign=-1
    elif z<-TURN//4:z+=TURN//2;sign=-1
    x,y=652032874,0
    for i,step in enumerate(ANGLES):
        if z>=0:x,y,z=x-(y>>i),y+(x>>i),z-step
        else:x,y,z=x+(y>>i),y-(x>>i),z+step
    return rounded(sign*x*radius,1<<30),rounded(sign*y*radius,1<<30),0


def topology(lines,stripped=False):
    n,parents=layout(lines);m=int(lines[3][3:6]);adj=[[] for _ in range(n)]
    for line in lines[4+n:4+n+m]:
        a=int(line[:3])-1;b=int(line[3:6])-1;adj[a].append(b);adj[b].append(a)
    adj=[sorted(set(neighbours)) for neighbours in adj]
    types=[line[2:5].strip() if stripped else line[31:34].strip() for line in lines[4:4+n]]
    return n,parents,adj,types


def parse(record):
    lines=record.splitlines(keepends=True);n,parents,adj,types=topology(lines);coords=[];signs=[]
    for line in lines[4:4+n]:
        if len(line)<34:raise ValueError('short coordinate line')
        vector=[];mask=0
        for axis,start in enumerate((0,10,20)):
            field=line[start:start+10];value=int(field.strip().replace(b'.',b''))
            if field==b'   -0.0000':mask|=1<<axis
            elif fixed(value)!=field:raise ValueError('unsupported coordinate formatting')
            vector.append(value)
        coords.append(tuple(vector));signs.append(mask)
    skeleton=lines.copy()
    for i in range(n):skeleton[4+i]=bytes([48+signs[i]])+lines[4+i][30:]
    return b''.join(skeleton),coords,parents,adj,types


def candidates(i,coordinates,parents,adj,types,slots,model,radius):
    """Only the skeleton and coordinates before i may affect these candidates."""
    parent=parents[i];base=coordinates[parent] if parent>=0 else (0,0,0)
    if model==0 or types[i]!=b'H' or len(adj[i])!=1:return [base],None
    centre=adj[i][0]
    if centre>=i:return [base],None
    if centre in slots:return slots[centre],centre
    hydrogens=[j for j in adj[centre] if types[j]==b'H']
    heavy=[j for j in adj[centre] if types[j]!=b'H']
    if (not 1<=len(hydrogens)<=8 or not heavy or any(j>=i for j in heavy)
        or min(hydrogens)!=i or any(len(adj[j])!=1 for j in hydrogens)):return [base],None
    origin=coordinates[centre];vectors=[tuple(coordinates[j][k]-origin[k] for k in range(3)) for j in heavy]
    if any(v[2] or not(v[0] or v[1]) for v in vectors):return [base],None
    if model==1:
        if len(heavy)!=2 or len(hydrogens)!=1:return [base],None
        vector=tuple(sum(v[k] for v in vectors) for k in range(3));norm=isqrt(sum(x*x for x in vector))
        if not norm:return [base],None
        offsets=[tuple(rounded(-x*radius,norm) for x in vector)]
    else:
        phases=sorted(set(angle(v[0],v[1]) for v in vectors))
        gaps=[((phases[(j+1)%len(phases)]-phase)%TURN if len(phases)>1 else TURN,phase) for j,phase in enumerate(phases)]
        gap,start=max(gaps,key=lambda pair:(pair[0],-pair[1]))
        offsets=[direction(start+gap*(j+1)//(len(hydrogens)+1),radius) for j in range(len(hydrogens))]
    slots[centre]=[tuple(origin[k]+v[k] for k in range(3)) for v in offsets]
    return slots[centre],centre


def encode(data,model=2,representation=1,radius=6200):
    if model not in (0,1,2) or representation not in (0,1,2,3) or not 1<=radius<=1000000:raise ValueError('invalid hydrogen mode')
    records=data.split(SEP);skeleton=[];flags=bytearray((len(records)+7)//8);vectors=[];digits=[]
    arithmetic=_ArithmeticEncoder();frequencies={};arithmetic_uncertainty=0.0
    rank=0;product=1;parsed=0;predicted=0;close=0;uncertainty=0.0;independent_uncertainty=0.0
    for record_index,record in enumerate(records):
        try:rest,coords,parents,adj,types=parse(record)
        except (ValueError,IndexError):skeleton.append(record);continue
        flags[record_index//8]|=1<<(record_index%8);parsed+=1;skeleton.append(rest);slots={}
        for i,actual in enumerate(coords):
            options,key=candidates(i,coords[:i],parents,adj,types,slots,model,radius)
            chosen=min(range(len(options)),key=lambda k:(sum((actual[j]-options[k][j])**2 for j in range(3)),k))
            if len(options)>1:
                digits.append(chosen);rank+=chosen*product;product*=len(options);uncertainty+=log2(len(options))
                if representation>=2:
                    counts=frequencies.setdefault(len(options),[1]*len(options));lo=sum(counts[:chosen]);total=sum(counts)
                    arithmetic.encode(lo,lo+counts[chosen],total);arithmetic_uncertainty+=log2(total/counts[chosen])
                    if representation==3:
                        counts[chosen]+=1
                        if sum(counts)>4096:counts[:]=[(c+1)//2 for c in counts]
            if key is not None:
                predicted+=1;independent_uncertainty+=log2(sum(types[j]==b'H' for j in adj[key]))
            residual=tuple(actual[k]-options[chosen][k] for k in range(3));vectors.append(residual)
            if key is not None:
                close+=max(map(abs,residual))<=2;slots[key].pop(chosen)
    body=SEP.join(skeleton);out=bytearray(MAGIC+bytes([model,representation])+vencode(radius)+vencode(len(records))+flags+vencode(len(body))+body)
    payload=bytes(48+d for d in digits) if representation==0 else rank.to_bytes(((product-1).bit_length()+7)//8,'little')
    if representation>=2:
        packed,bits=arithmetic.finish();payload=vencode(bits)+packed
    out.extend(vencode(len(payload)));out.extend(payload)
    out.extend(b''.join(('%d,%d,%d\n'%v).encode() for v in vectors))
    return bytes(out),dict(records=len(records),parsed_records=parsed,atoms=len(vectors),model=model,
        representation=representation,radius=radius,predicted_atoms=predicted,within_two_units=close,
        candidate_order_choices=len(digits),candidate_order_combinatorial_bits=uncertainty,
        candidate_independent_bits=independent_uncertainty,order_payload_bytes=len(payload),
        choice_arithmetic_prediction_bits=arithmetic_uncertainty if representation>=2 else None,
        transformed_bytes=len(out),original_bytes=len(data))


def decode(blob):
    if blob[:5]!=MAGIC or len(blob)<7:raise ValueError('invalid hydrogen stream')
    model,representation=blob[5:7];radius,pos=vdecode(blob,7)
    if model not in (0,1,2) or representation not in (0,1,2,3) or not 1<=radius<=1000000:raise ValueError('invalid hydrogen mode')
    nr,pos=vdecode(blob,pos);nf=(nr+7)//8;flags=blob[pos:pos+nf];pos+=nf
    if len(flags)!=nf:raise ValueError('truncated record flags')
    size,pos=vdecode(blob,pos);body=blob[pos:pos+size];pos+=size
    if len(body)!=size:raise ValueError('truncated skeleton')
    size,pos=vdecode(blob,pos);choices=blob[pos:pos+size];pos+=size
    if len(choices)!=size:raise ValueError('truncated choices')
    rank=int.from_bytes(choices,'little') if representation==1 else 0;digit_at=0;frequencies={}
    if representation>=2:
        bits,start=vdecode(choices,0)
        if start+(bits+7)//8!=len(choices):raise ValueError('invalid choice arithmetic framing')
        arithmetic=_ArithmeticDecoder(choices[start:],bits)
    vectors=[tuple(map(int,line.split(b','))) for line in blob[pos:].splitlines()]
    if any(len(v)!=3 for v in vectors):raise ValueError('invalid residual vector')
    records=body.split(SEP)
    if len(records)!=nr:raise ValueError('record count mismatch')
    restored=[];vector_at=0
    for r,record in enumerate(records):
        if not flags[r//8]&(1<<(r%8)):restored.append(record);continue
        lines=record.splitlines(keepends=True);n,parents,adj,types=topology(lines,True);coords=[];slots={}
        for i in range(n):
            options,key=candidates(i,coords,parents,adj,types,slots,model,radius);chosen=0
            if len(options)>1:
                if representation==1:chosen=rank%len(options);rank//=len(options)
                elif representation==0:
                    if digit_at>=len(choices):raise ValueError('missing candidate index')
                    chosen=choices[digit_at]-48;digit_at+=1
                    if not 0<=chosen<len(options):raise ValueError('candidate index outside restricted alphabet')
                else:
                    counts=frequencies.setdefault(len(options),[1]*len(options));total=sum(counts);target=arithmetic.target(total);lo=0
                    for chosen,count in enumerate(counts):
                        if target<lo+count:arithmetic.update(lo,lo+count,total);break
                        lo+=count
                    else:raise ValueError('choice arithmetic symbol invalid')
                    if representation==3:
                        counts[chosen]+=1
                        if sum(counts)>4096:counts[:]=[(c+1)//2 for c in counts]
            if vector_at>=len(vectors):raise ValueError('missing coordinate residual')
            coordinate=tuple(options[chosen][k]+vectors[vector_at][k] for k in range(3));coords.append(coordinate);vector_at+=1
            if key is not None:slots[key].pop(chosen)
            sign_mask=lines[4+i][0]-48
            if not 0<=sign_mask<8:raise ValueError('invalid zero signs')
            fields=[]
            for k,value in enumerate(coordinate):
                if sign_mask&(1<<k):
                    if value:raise ValueError('sign mask on nonzero value')
                    fields.append(b'   -0.0000')
                else:fields.append(fixed(value))
            prefix=b''.join(fields)
            if len(prefix)!=30:raise ValueError('coordinate overflow')
            lines[4+i]=prefix+lines[4+i][1:]
        restored.append(b''.join(lines))
    if vector_at!=len(vectors) or rank or (not representation and digit_at!=len(choices)):raise ValueError('unused residual state')
    return SEP.join(restored)
