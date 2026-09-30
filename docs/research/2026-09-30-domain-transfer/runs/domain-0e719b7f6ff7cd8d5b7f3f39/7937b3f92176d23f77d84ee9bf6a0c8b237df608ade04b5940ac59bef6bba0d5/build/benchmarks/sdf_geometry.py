"""Reversible structural coordinate residuals for canonical V2000 records.

The bond graph selects an earlier atom as a coordinate predictor. The record
skeleton preserves all non-coordinate bytes. Unsupported records pass through
literally. No input values or dictionaries are embedded in the decoder.
"""
import collections
from cix.multinomial import (vencode,vdecode,encode_type_class,decode_type_class)

MAGIC=b'SDFG\x01'
SEP=b'$$$$\n'


def fixed(value):
    text=('-' if value<0 else '')+f'{abs(value)//10000}.{abs(value)%10000:04d}'
    return text.rjust(10).encode('ascii')


def layout(lines):
    if len(lines)<4 or not lines[3].rstrip().endswith(b'V2000'):raise ValueError('unsupported record')
    n=int(lines[3][:3]);m=int(lines[3][3:6])
    if not 0<n<=999 or not 0<=m<=999 or len(lines)<5+n+m:raise ValueError('incomplete record')
    if not lines[4+n+m].startswith(b'M  '):raise ValueError('missing property section')
    parents=[i-1 for i in range(n)]
    for line in lines[4+n:4+n+m]:
        a=int(line[:3])-1;b=int(line[3:6])-1
        if not 0<=a<n or not 0<=b<n or a==b:raise ValueError('unsupported bond indices')
        a,b=sorted((a,b));parents[b]=a
    return n,parents


def extract(record,mode):
    lines=record.splitlines(keepends=True);n,parents=layout(lines);coordinates=[];types=[]
    for line in lines[4:4+n]:
        if len(line)<34:raise ValueError('short atom')
        values=[]
        for start in (0,10,20):
            field=line[start:start+10];value=int(field.strip().replace(b'.',b''))
            if fixed(value)!=field:raise ValueError('noncanonical coordinate retained literally')
            values.append(value)
        coordinates.append(tuple(values));types.append(atom_group(line[30:]))
    residuals=[]
    for i,coordinate in enumerate(coordinates):
        parent=-1 if mode==0 else i-1 if mode==1 else parents[i]
        base=coordinates[parent] if parent>=0 else (0,0,0)
        residuals.append(tuple(v-b for v,b in zip(coordinate,base)))
    for i in range(n):lines[4+i]=lines[4+i][30:]
    return b''.join(lines),residuals,types


def atom_group(suffix):
    return {b'C':0,b'H':1,b'N':2,b'O':3}.get(suffix[:4].strip(),4)


def signed(value):return vencode(2*value if value>=0 else -2*value-1)


def read_signed(blob,pos):
    value,pos=vdecode(blob,pos);return (value//2 if not value&1 else -(value//2)-1),pos


def encode(data,mode=2,representation=0,palette_size=64):
    if mode not in (0,1,2) or representation not in (0,1,2):raise ValueError('unknown geometry mode')
    records=data.split(SEP);skeleton=[];flags=bytearray((len(records)+7)//8);vectors=[];groups=[];parsed=0
    for i,record in enumerate(records):
        try:rest,residuals,types=extract(record,mode)
        except (ValueError,IndexError):skeleton.append(record);continue
        flags[i//8]|=1<<(i%8);parsed+=1;skeleton.append(rest);vectors.extend(residuals);groups.extend(types)
    body=SEP.join(skeleton)
    out=bytearray(MAGIC+bytes([mode,representation])+vencode(len(records))+flags+vencode(len(body))+body)
    out.extend(vencode(len(vectors)));payload_start=len(out)
    if representation==0:
        for vector in vectors:
            for value in vector:out.extend(signed(value))
    elif representation==1:
        text=b''.join(('%d,%d,%d\n'%v).encode() for v in vectors);out.extend(text)
    else:
        if not 1<=palette_size<=254:raise ValueError('palette outside byte alphabet')
        counts=collections.Counter(vectors);palette=[v for v,c in counts.most_common(palette_size)];ids={v:i for i,v in enumerate(palette)}
        out.extend(vencode(len(palette)))
        for vector in palette:
            for value in vector:out.extend(signed(value))
        streams=[bytearray() for _ in range(5)];escaped=bytearray();escape=len(palette)
        for vector,group in zip(vectors,groups):
            streams[group].append(ids.get(vector,escape))
            if vector not in ids:
                for value in vector:escaped.extend(signed(value))
        for stream in streams:
            out.extend(vencode(len(stream)))
            for offset in range(0,len(stream),4096):
                frame=encode_type_class(bytes(stream[offset:offset+4096]));out.extend(vencode(len(frame)));out.extend(frame)
        out.extend(escaped)
    return bytes(out),dict(records=len(records),parsed_records=parsed,atoms=len(vectors),mode=mode,
        representation=representation,coordinate_payload_bytes=len(out)-payload_start,
        transformed_bytes=len(out),original_bytes=len(data),palette_size=palette_size if representation==2 else None)


def decode(blob):
    if blob[:5]!=MAGIC or len(blob)<7:raise ValueError('invalid geometry frame')
    mode,representation=blob[5:7]
    if mode not in (0,1,2) or representation not in (0,1,2):raise ValueError('unknown geometry mode')
    nr,pos=vdecode(blob,7);flag_size=(nr+7)//8;flags=blob[pos:pos+flag_size];pos+=flag_size
    if len(flags)!=flag_size:raise ValueError('truncated flags')
    size,pos=vdecode(blob,pos);skeleton=blob[pos:pos+size];pos+=size;nvec,pos=vdecode(blob,pos)
    if len(skeleton)!=size:raise ValueError('truncated skeleton')
    records=skeleton.split(SEP)
    if len(records)!=nr:raise ValueError('record count mismatch')
    palette=[];streams=[];positions=[0]*5
    if representation==1:
        vectors=[tuple(map(int,line.split(b','))) for line in blob[pos:].splitlines()];pos=len(blob)
        if len(vectors)!=nvec or any(len(v)!=3 for v in vectors):raise ValueError('invalid coordinate list')
    elif representation==2:
        count,pos=vdecode(blob,pos)
        if count>254:raise ValueError('oversized palette')
        for _ in range(count):
            vector=[]
            for _ in range(3):value,pos=read_signed(blob,pos);vector.append(value)
            palette.append(tuple(vector))
        for _ in range(5):
            n,pos=vdecode(blob,pos);stream=bytearray()
            for offset in range(0,n,4096):
                size,pos=vdecode(blob,pos);chunk,consumed=decode_type_class(blob[pos:pos+size]);pos+=size
                if consumed!=size:raise ValueError('unused type class bytes')
                if len(chunk)!=min(4096,n-offset):raise ValueError('type class block mismatch')
                stream.extend(chunk)
            streams.append(bytes(stream))
    vector_at=0;restored=[]
    for i,record in enumerate(records):
        if not flags[i//8]&(1<<(i%8)):restored.append(record);continue
        lines=record.splitlines(keepends=True);n,parents=layout(lines);coordinates=[]
        for atom in range(n):
            if representation==1:residual=vectors[vector_at]
            elif representation==2:
                group=atom_group(lines[4+atom]);at=positions[group]
                if at>=len(streams[group]):raise ValueError('palette stream exhausted')
                token=streams[group][at];positions[group]+=1
                if token<len(palette):residual=palette[token]
                elif token!=len(palette):raise ValueError('palette token invalid')
                else:residual=None
            else:residual=None
            if residual is None:
                values=[]
                for _ in range(3):value,pos=read_signed(blob,pos);values.append(value)
                residual=tuple(values)
            parent=-1 if mode==0 else atom-1 if mode==1 else parents[atom]
            base=coordinates[parent] if parent>=0 else (0,0,0)
            coordinate=tuple(a+b for a,b in zip(residual,base));coordinates.append(coordinate)
            fields=b''.join(fixed(value) for value in coordinate)
            if len(fields)!=30:raise ValueError('reconstructed coordinate overflow')
            lines[4+atom]=fields+lines[4+atom];vector_at+=1
        restored.append(b''.join(lines))
    if pos!=len(blob) or vector_at!=nvec:raise ValueError('unused or missing coordinate data')
    if representation==2 and any(positions[i]!=len(streams[i]) for i in range(5)):raise ValueError('unused palette tokens')
    return SEP.join(restored)
