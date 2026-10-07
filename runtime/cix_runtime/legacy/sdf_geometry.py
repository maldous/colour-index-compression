"""Reversible structural coordinate residuals for canonical V2000 records.

The bond graph selects an earlier atom as a coordinate predictor. The record
skeleton preserves all non-coordinate bytes. Unsupported records pass through
literally. No input values or dictionaries are embedded in the decoder.
"""
import collections
from .multinomial import vencode, vdecode, encode_type_class, decode_type_class

MAGIC=b'SDFG\x01'
SEP=b'$$$$\n'
COORDINATE_STARTS=(0,10,20)
GROUP_COUNT=5
TYPE_CLASS_BLOCK=4096


def fixed(value):
    text=('-' if value<0 else '')+f'{abs(value)//10000}.{abs(value)%10000:04d}'
    return text.rjust(10).encode('ascii')


def _counts(lines):
    if len(lines)<4 or not lines[3].rstrip().endswith(b'V2000'):raise ValueError('unsupported record')
    atoms=int(lines[3][:3]);bonds=int(lines[3][3:6])
    if not 0<atoms<=999 or not 0<=bonds<=999 or len(lines)<5+atoms+bonds:raise ValueError('incomplete record')
    if not lines[4+atoms+bonds].startswith(b'M  '):raise ValueError('missing property section')
    return atoms,bonds


def _bond_parent(line,atoms):
    first=int(line[:3])-1;second=int(line[3:6])-1
    if not 0<=first<atoms or not 0<=second<atoms or first==second:raise ValueError('unsupported bond indices')
    return sorted((first,second))


def layout(lines):
    atoms,bonds=_counts(lines);parents=[index-1 for index in range(atoms)]
    for line in lines[4+atoms:4+atoms+bonds]:
        first,second=_bond_parent(line,atoms);parents[second]=first
    return atoms,parents


def _coordinates(lines,atoms):
    coordinates=[];groups=[]
    for line in lines[4:4+atoms]:
        if len(line)<34:raise ValueError('short atom')
        values=[]
        for start in COORDINATE_STARTS:
            field=line[start:start+10];value=int(field.strip().replace(b'.',b''))
            if fixed(value)!=field:raise ValueError('noncanonical coordinate retained literally')
            values.append(value)
        coordinates.append(tuple(values));groups.append(atom_group(line[30:]))
    return coordinates,groups


def _parent(mode,index,parents):
    if mode==0:return -1
    return index-1 if mode==1 else parents[index]


def _coordinate_residuals(coordinates,parents,mode):
    residuals=[]
    for index,coordinate in enumerate(coordinates):
        parent=_parent(mode,index,parents);base=coordinates[parent] if parent>=0 else (0,0,0)
        residuals.append(tuple(value-base_value for value,base_value in zip(coordinate,base)))
    return residuals


def extract(record,mode):
    lines=record.splitlines(keepends=True);atoms,parents=layout(lines)
    coordinates,groups=_coordinates(lines,atoms)
    residuals=_coordinate_residuals(coordinates,parents,mode)
    for index in range(atoms):lines[4+index]=lines[4+index][30:]
    return b''.join(lines),residuals,groups


def atom_group(suffix):
    return {b'C':0,b'H':1,b'N':2,b'O':3}.get(suffix[:4].strip(),4)


def signed(value):return vencode(2*value if value>=0 else -2*value-1)


def read_signed(blob,pos):
    value,pos=vdecode(blob,pos);return (value//2 if not value&1 else -(value//2)-1),pos


def _extract_records(data,mode):
    records=data.split(SEP);skeleton=[];flags=bytearray((len(records)+7)//8);vectors=[];groups=[];parsed=0
    for index,record in enumerate(records):
        try:rest,residuals,types=extract(record,mode)
        except (ValueError,IndexError):skeleton.append(record);continue
        flags[index//8]|=1<<(index%8);parsed+=1;skeleton.append(rest);vectors.extend(residuals);groups.extend(types)
    return records,skeleton,flags,vectors,groups,parsed


def _append_signed_vectors(out,vectors):
    for vector in vectors:
        for value in vector:out.extend(signed(value))


def _append_palette(out,vectors,groups,palette_size):
    if not 1<=palette_size<=254:raise ValueError('palette outside byte alphabet')
    counts=collections.Counter(vectors);palette=[vector for vector,_ in counts.most_common(palette_size)]
    identifiers={vector:index for index,vector in enumerate(palette)};out.extend(vencode(len(palette)))
    _append_signed_vectors(out,palette)
    streams=[bytearray() for _ in range(GROUP_COUNT)];escaped=bytearray();escape=len(palette)
    for vector,group in zip(vectors,groups):
        streams[group].append(identifiers.get(vector,escape))
        if vector not in identifiers:_append_signed_vectors(escaped,[vector])
    for stream in streams:
        out.extend(vencode(len(stream)))
        for offset in range(0,len(stream),TYPE_CLASS_BLOCK):
            frame=encode_type_class(bytes(stream[offset:offset+TYPE_CLASS_BLOCK]));out.extend(vencode(len(frame)));out.extend(frame)
    out.extend(escaped)


def _append_vectors(out,vectors,groups,representation,palette_size):
    if representation==0:_append_signed_vectors(out,vectors)
    elif representation==1:out.extend(b''.join(('%d,%d,%d\n'%vector).encode() for vector in vectors))
    else:_append_palette(out,vectors,groups,palette_size)


def encode(data,mode=2,representation=0,palette_size=64):
    if mode not in (0,1,2) or representation not in (0,1,2):raise ValueError('unknown geometry mode')
    records,skeleton,flags,vectors,groups,parsed=_extract_records(data,mode);body=SEP.join(skeleton)
    out=bytearray(MAGIC+bytes([mode,representation])+vencode(len(records))+flags+vencode(len(body))+body)
    out.extend(vencode(len(vectors)));payload_start=len(out);_append_vectors(out,vectors,groups,representation,palette_size)
    return bytes(out),{
        'records':len(records),'parsed_records':parsed,'atoms':len(vectors),'mode':mode,
        'representation':representation,'coordinate_payload_bytes':len(out)-payload_start,
        'transformed_bytes':len(out),'original_bytes':len(data),'palette_size':palette_size if representation==2 else None,
    }


def _decode_header(blob):
    if blob[:5]!=MAGIC or len(blob)<7:raise ValueError('invalid geometry frame')
    mode,representation=blob[5:7]
    if mode not in (0,1,2) or representation not in (0,1,2):raise ValueError('unknown geometry mode')
    records_count,pos=vdecode(blob,7);flag_size=(records_count+7)//8;flags=blob[pos:pos+flag_size];pos+=flag_size
    if len(flags)!=flag_size:raise ValueError('truncated flags')
    size,pos=vdecode(blob,pos);skeleton=blob[pos:pos+size];pos+=size;vectors_count,pos=vdecode(blob,pos)
    if len(skeleton)!=size:raise ValueError('truncated skeleton')
    records=skeleton.split(SEP)
    if len(records)!=records_count:raise ValueError('record count mismatch')
    return mode,representation,flags,records,vectors_count,pos


def _signed_vector(blob,pos):
    values=[]
    for _ in range(3):value,pos=read_signed(blob,pos);values.append(value)
    return tuple(values),pos


def _palette_stream(blob,pos,size):
    stream=bytearray()
    for offset in range(0,size,TYPE_CLASS_BLOCK):
        frame_size,pos=vdecode(blob,pos);chunk,consumed=decode_type_class(blob[pos:pos+frame_size]);pos+=frame_size
        if consumed!=frame_size:raise ValueError('unused type class bytes')
        if len(chunk)!=min(TYPE_CLASS_BLOCK,size-offset):raise ValueError('type class block mismatch')
        stream.extend(chunk)
    return bytes(stream),pos


def _decode_palette(blob,pos):
    count,pos=vdecode(blob,pos)
    if count>254:raise ValueError('oversized palette')
    palette=[]
    for _ in range(count):
        vector,pos=_signed_vector(blob,pos);palette.append(vector)
    streams=[]
    for _ in range(GROUP_COUNT):
        size,pos=vdecode(blob,pos);stream,pos=_palette_stream(blob,pos,size);streams.append(stream)
    return palette,streams,pos


def _decode_vectors(blob,pos,representation,vectors_count):
    palette=[];streams=[]
    if representation==1:
        vectors=[tuple(map(int,line.split(b','))) for line in blob[pos:].splitlines()];pos=len(blob)
        if len(vectors)!=vectors_count or any(len(vector)!=3 for vector in vectors):raise ValueError('invalid coordinate list')
        return vectors,palette,streams,pos
    if representation==2:palette,streams,pos=_decode_palette(blob,pos)
    return [],palette,streams,pos


def _palette_residual(lines,atom,palette,streams,positions):
    group=atom_group(lines[4+atom]);at=positions[group]
    if at>=len(streams[group]):raise ValueError('palette stream exhausted')
    token=streams[group][at];positions[group]+=1
    if token<len(palette):return palette[token]
    if token!=len(palette):raise ValueError('palette token invalid')
    return None


def _restore_record(record,mode,representation,blob,pos,vectors,palette,streams,positions,vector_at):
    lines=record.splitlines(keepends=True);atoms,parents=layout(lines);coordinates=[]
    for atom in range(atoms):
        residual=vectors[vector_at] if representation==1 else None
        if representation==2:residual=_palette_residual(lines,atom,palette,streams,positions)
        if residual is None:residual,pos=_signed_vector(blob,pos)
        parent=_parent(mode,atom,parents);base=coordinates[parent] if parent>=0 else (0,0,0)
        coordinate=tuple(value+base_value for value,base_value in zip(residual,base));coordinates.append(coordinate)
        fields=b''.join(fixed(value) for value in coordinate)
        if len(fields)!=30:raise ValueError('reconstructed coordinate overflow')
        lines[4+atom]=fields+lines[4+atom];vector_at+=1
    return b''.join(lines),pos,vector_at


def decode(blob):
    mode,representation,flags,records,vectors_count,pos=_decode_header(blob)
    vectors,palette,streams,pos=_decode_vectors(blob,pos,representation,vectors_count)
    positions=[0]*GROUP_COUNT;vector_at=0;restored=[]
    for index,record in enumerate(records):
        if not flags[index//8]&(1<<(index%8)):restored.append(record);continue
        restored_record,pos,vector_at=_restore_record(record,mode,representation,blob,pos,vectors,palette,streams,positions,vector_at)
        restored.append(restored_record)
    if pos!=len(blob) or vector_at!=vectors_count:raise ValueError('unused or missing coordinate data')
    if representation==2 and any(positions[index]!=len(streams[index]) for index in range(GROUP_COUNT)):raise ValueError('unused palette tokens')
    return SEP.join(restored)
