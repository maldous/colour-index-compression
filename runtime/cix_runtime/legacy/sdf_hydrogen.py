"""Integer geometry candidates and conditional permutation ranks.

The molecular skeleton gives the number of hydrogen slots without a count
header. Earlier heavy-atom coordinates determine those slots. Each slot is
used once, so arrangement choices shrink from h**h to h!. Exact coordinate
residuals retain arbitrary layouts, unusual structures and rounding. PAQ-text
choice digits and CIX mixed-radix ranks receive identical candidate sets.
"""
from math import isqrt,log2
from .multinomial import vencode, vdecode, _ArithmeticEncoder, _ArithmeticDecoder
from .sdf_geometry import SEP, fixed, layout

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


def _base_candidate(index,coordinates,parents):
    parent=parents[index]
    return coordinates[parent] if parent>=0 else (0,0,0)


def _hydrogen_groups(centre,adj,types):
    hydrogens=[index for index in adj[centre] if types[index]==b'H']
    heavy=[index for index in adj[centre] if types[index]!=b'H']
    return hydrogens,heavy


def _valid_hydrogen_group(index,hydrogens,heavy,adj):
    if not 1<=len(hydrogens)<=8:return False
    return bool(heavy) and not any(atom>=index for atom in heavy) and min(hydrogens)==index and not any(len(adj[atom])!=1 for atom in hydrogens)


def _heavy_vectors(centre,heavy,coordinates):
    origin=coordinates[centre]
    vectors=[tuple(coordinates[atom][axis]-origin[axis] for axis in range(3)) for atom in heavy]
    if any(vector[2] or not(vector[0] or vector[1]) for vector in vectors):return None
    return origin,vectors


def _linear_offsets(heavy,hydrogens,vectors,radius):
    if len(heavy)!=2 or len(hydrogens)!=1:return None
    vector=tuple(sum(value[axis] for value in vectors) for axis in range(3));norm=isqrt(sum(value*value for value in vector))
    if not norm:return None
    return [tuple(rounded(-value*radius,norm) for value in vector)]


def _radial_offsets(hydrogens,vectors,radius):
    phases=sorted({angle(vector[0],vector[1]) for vector in vectors})
    gaps=[]
    for index,phase in enumerate(phases):
        next_phase=phases[(index+1)%len(phases)]
        gap=(next_phase-phase)%TURN if len(phases)>1 else TURN
        gaps.append((gap,phase))
    gap,start=max(gaps,key=lambda pair:(pair[0],-pair[1]))
    return [direction(start+gap*(index+1)//(len(hydrogens)+1),radius) for index in range(len(hydrogens))]


def candidates(i,coordinates,parents,adj,types,slots,model,radius):
    """Only the skeleton and coordinates before i may affect these candidates."""
    base=_base_candidate(i,coordinates,parents)
    if model==0 or types[i]!=b'H' or len(adj[i])!=1:return [base],None
    centre=adj[i][0]
    if centre>=i:return [base],None
    if centre in slots:return slots[centre],centre
    hydrogens,heavy=_hydrogen_groups(centre,adj,types)
    if not _valid_hydrogen_group(i,hydrogens,heavy,adj):return [base],None
    structured=_heavy_vectors(centre,heavy,coordinates)
    if structured is None:return [base],None
    origin,vectors=structured
    offsets=_linear_offsets(heavy,hydrogens,vectors,radius) if model==1 else _radial_offsets(hydrogens,vectors,radius)
    if offsets is None:return [base],None
    slots[centre]=[tuple(origin[axis]+vector[axis] for axis in range(3)) for vector in offsets]
    return slots[centre],centre


def _encode_state(records):
    return {
        'skeleton':[], 'flags':bytearray((len(records)+7)//8), 'vectors':[], 'digits':[],
        'arithmetic':_ArithmeticEncoder(), 'frequencies':{}, 'arithmetic_uncertainty':0.0,
        'rank':0, 'product':1, 'parsed':0, 'predicted':0, 'close':0,
        'uncertainty':0.0, 'independent_uncertainty':0.0,
    }


def _closest_candidate(actual,options):
    return min(range(len(options)),key=lambda index, options=options, actual=actual:(sum((actual[axis]-options[index][axis])**2 for axis in range(3)),index))


def _record_choice(state,chosen,option_count,representation):
    if option_count<=1:return
    state['digits'].append(chosen);state['rank']+=chosen*state['product'];state['product']*=option_count
    state['uncertainty']+=log2(option_count)
    if representation<2:return
    counts=state['frequencies'].setdefault(option_count,[1]*option_count);lower=sum(counts[:chosen]);total=sum(counts)
    state['arithmetic'].encode(lower,lower+counts[chosen],total);state['arithmetic_uncertainty']+=log2(total/counts[chosen])
    if representation==3:
        counts[chosen]+=1
        if sum(counts)>4096:counts[:]=[(count+1)//2 for count in counts]


def _record_prediction(state,key,types,adj,residual,slots,chosen):
    if key is None:return
    state['predicted']+=1;state['independent_uncertainty']+=log2(sum(types[index]==b'H' for index in adj[key]))
    state['close']+=max(map(abs,residual))<=2;slots[key].pop(chosen)


def _encode_record(record,index,model,representation,radius,state):
    try:rest,coords,parents,adj,types=parse(record)
    except (ValueError,IndexError):state['skeleton'].append(record);return
    state['flags'][index//8]|=1<<(index%8);state['parsed']+=1;state['skeleton'].append(rest);slots={}
    for atom,actual in enumerate(coords):
        options,key=candidates(atom,coords[:atom],parents,adj,types,slots,model,radius)
        chosen=_closest_candidate(actual,options);_record_choice(state,chosen,len(options),representation)
        residual=tuple(actual[axis]-options[chosen][axis] for axis in range(3));state['vectors'].append(residual)
        _record_prediction(state,key,types,adj,residual,slots,chosen)


def _choice_payload(state,representation):
    if representation==0:return bytes(48+digit for digit in state['digits'])
    payload=state['rank'].to_bytes(((state['product']-1).bit_length()+7)//8,'little')
    if representation>=2:
        packed,bits=state['arithmetic'].finish();payload=vencode(bits)+packed
    return payload


def encode(data,model=2,representation=1,radius=6200):
    if model not in (0,1,2) or representation not in (0,1,2,3) or not 1<=radius<=1000000:raise ValueError('invalid hydrogen mode')
    records=data.split(SEP);state=_encode_state(records)
    for index,record in enumerate(records):_encode_record(record,index,model,representation,radius,state)
    body=SEP.join(state['skeleton']);out=bytearray(MAGIC+bytes([model,representation])+vencode(radius)+vencode(len(records))+state['flags']+vencode(len(body))+body)
    payload=_choice_payload(state,representation);out.extend(vencode(len(payload)));out.extend(payload)
    out.extend(b''.join(('%d,%d,%d\n'%vector).encode() for vector in state['vectors']))
    return bytes(out),{
        'records':len(records),'parsed_records':state['parsed'],'atoms':len(state['vectors']),'model':model,
        'representation':representation,'radius':radius,'predicted_atoms':state['predicted'],'within_two_units':state['close'],
        'candidate_order_choices':len(state['digits']),'candidate_order_combinatorial_bits':state['uncertainty'],
        'candidate_independent_bits':state['independent_uncertainty'],'order_payload_bytes':len(payload),
        'choice_arithmetic_prediction_bits':state['arithmetic_uncertainty'] if representation>=2 else None,
        'transformed_bytes':len(out),'original_bytes':len(data),
    }


def _decode_header(blob):
    if blob[:5]!=MAGIC or len(blob)<7:raise ValueError('invalid hydrogen stream')
    model,representation=blob[5:7];radius,pos=vdecode(blob,7)
    if model not in (0,1,2) or representation not in (0,1,2,3) or not 1<=radius<=1000000:raise ValueError('invalid hydrogen mode')
    records_count,pos=vdecode(blob,pos);flag_size=(records_count+7)//8;flags=blob[pos:pos+flag_size];pos+=flag_size
    if len(flags)!=flag_size:raise ValueError('truncated record flags')
    size,pos=vdecode(blob,pos);body=blob[pos:pos+size];pos+=size
    if len(body)!=size:raise ValueError('truncated skeleton')
    size,pos=vdecode(blob,pos);choices=blob[pos:pos+size];pos+=size
    if len(choices)!=size:raise ValueError('truncated choices')
    records=body.split(SEP)
    if len(records)!=records_count:raise ValueError('record count mismatch')
    vectors=[tuple(map(int,line.split(b','))) for line in blob[pos:].splitlines()]
    if any(len(vector)!=3 for vector in vectors):raise ValueError('invalid residual vector')
    return model,representation,radius,flags,records,choices,vectors


def _decode_choice_state(choices,representation):
    state={'rank':int.from_bytes(choices,'little') if representation==1 else 0,'digit_at':0,'frequencies':{}}
    if representation>=2:
        bits,start=vdecode(choices,0)
        if start+(bits+7)//8!=len(choices):raise ValueError('invalid choice arithmetic framing')
        state['arithmetic']=_ArithmeticDecoder(choices[start:],bits)
    return state


def _arithmetic_choice(state,option_count,representation):
    counts=state['frequencies'].setdefault(option_count,[1]*option_count);total=sum(counts);target=state['arithmetic'].target(total);lower=0
    for chosen,count in enumerate(counts):
        if target<lower+count:
            state['arithmetic'].update(lower,lower+count,total)
            if representation==3:
                counts[chosen]+=1
                if sum(counts)>4096:counts[:]=[(count+1)//2 for count in counts]
            return chosen
        lower+=count
    raise ValueError('choice arithmetic symbol invalid')


def _decode_choice(state,choices,representation,option_count):
    if option_count<=1:return 0
    if representation==1:
        chosen=state['rank']%option_count;state['rank']//=option_count;return chosen
    if representation==0:
        if state['digit_at']>=len(choices):raise ValueError('missing candidate index')
        chosen=choices[state['digit_at']]-48;state['digit_at']+=1
        if not 0<=chosen<option_count:raise ValueError('candidate index outside restricted alphabet')
        return chosen
    return _arithmetic_choice(state,option_count,representation)


def _coordinate_prefix(coordinate,sign_mask):
    if not 0<=sign_mask<8:raise ValueError('invalid zero signs')
    fields=[]
    for axis,value in enumerate(coordinate):
        if sign_mask&(1<<axis):
            if value:raise ValueError('sign mask on nonzero value')
            fields.append(b'   -0.0000')
        else:fields.append(fixed(value))
    prefix=b''.join(fields)
    if len(prefix)!=30:raise ValueError('coordinate overflow')
    return prefix


def _restore_record(record,model,representation,radius,choices,vectors,state,vector_at):
    lines=record.splitlines(keepends=True);atoms,parents,adj,types=topology(lines,True);coords=[];slots={}
    for atom in range(atoms):
        options,key=candidates(atom,coords,parents,adj,types,slots,model,radius)
        chosen=_decode_choice(state,choices,representation,len(options))
        if vector_at>=len(vectors):raise ValueError('missing coordinate residual')
        coordinate=tuple(options[chosen][axis]+vectors[vector_at][axis] for axis in range(3));coords.append(coordinate);vector_at+=1
        if key is not None:slots[key].pop(chosen)
        sign_mask=lines[4+atom][0]-48;prefix=_coordinate_prefix(coordinate,sign_mask)
        lines[4+atom]=prefix+lines[4+atom][1:]
    return b''.join(lines),vector_at


def decode(blob):
    model,representation,radius,flags,records,choices,vectors=_decode_header(blob)
    state=_decode_choice_state(choices,representation);restored=[];vector_at=0
    for index,record in enumerate(records):
        if not flags[index//8]&(1<<(index%8)):restored.append(record);continue
        restored_record,vector_at=_restore_record(record,model,representation,radius,choices,vectors,state,vector_at)
        restored.append(restored_record)
    if vector_at!=len(vectors) or state['rank'] or (not representation and state['digit_at']!=len(choices)):raise ValueError('unused residual state')
    return SEP.join(restored)
