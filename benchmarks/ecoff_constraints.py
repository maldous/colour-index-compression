"""Predict ECOFF hash and msym tables from transmitted symbols and relocations.

Tables are replaced by zeros only after exact equality with the reconstruction.
Unrecognized/noncanonical data remains literal. File positions and executable
headers remain intact, preserving the backend's instruction-model detection.
Layout reference: Tru64 UNIX Object File and Symbol Table Specification, ch.14.
"""
import struct
import tarfile
from cix.multinomial import vencode,vdecode

TRAILER=b'ECFX1'


def sections(data):
    if len(data)<104 or data[:2]!=b'\x83\x01':raise ValueError('not Alpha ECOFF')
    _,count,_,_,_,optional,flags=struct.unpack_from('<HHIQIHH',data)
    end=24+optional+count*64
    if optional!=80 or not 1<=count<=256 or end>len(data) or flags not in (0x2005,0x2007,0x3007):
        raise ValueError('unsupported ECOFF header')
    out={};ranges=[]
    for i in range(count):
        name,_,_,size,offset,_,_,_,_,_=struct.unpack_from('<8sQQQQQQHHI',data,24+optional+i*64)
        name=name.rstrip(b'\0')
        if name in out:raise ValueError('duplicate ECOFF section')
        if offset:
            if offset<end or offset+size>len(data):raise ValueError('ECOFF section outside input')
            if size:ranges.append((offset,offset+size))
            out[name]=(offset,size)
    ranges.sort()
    if any(a[1]>b[0] for a,b in zip(ranges,ranges[1:])):raise ValueError('overlapping ECOFF sections')
    return out


def objects(data):
    try:sections(data)
    except (ValueError,struct.error):pass
    else:return [(0,len(data))]
    out=[];pos=0
    while pos+512<=len(data):
        block=data[pos:pos+512]
        if not any(block):break
        try:header=tarfile.TarInfo.frombuf(block,'utf-8','surrogateescape')
        except (tarfile.HeaderError,ValueError):break
        end=pos+512+header.size
        if header.size<0 or end>len(data):break
        if header.isfile():
            try:sections(data[pos+512:end])
            except (ValueError,struct.error):pass
            else:out.append((pos+512,header.size))
        pos=pos+512+((header.size+511)//512)*512
    return out


def name_hash(name):
    value=0
    for byte in name:
        value=(value<<4)+byte;high=value&0xf0000000
        value^=high>>24;value&=~high
    return value


def predicted(data):
    sec=sections(data)
    if not all(k in sec for k in (b'.hash',b'.dynsym',b'.dynstr')):return []
    hoff,hsize=sec[b'.hash'];soff,ssize=sec[b'.dynsym'];toff,tsize=sec[b'.dynstr']
    if hsize<8:return []
    buckets,n=struct.unpack_from('<II',data,hoff)
    if not buckets or not n or 8+4*(buckets+n)>hsize or n*24>ssize:return []
    hashes=[]
    for i in range(n):
        offset=struct.unpack_from('<I',data,soff+i*24)[0]
        if offset>=tsize:return []
        end=data.find(b'\0',toff+offset,toff+tsize)
        if end<0:return []
        hashes.append(name_hash(data[toff+offset:end]))
    heads=[0]*buckets;chains=[0]*n
    for i in range(n-1,0,-1):
        bucket=hashes[i]%buckets;chains[i]=heads[bucket];heads[bucket]=i
    hash_table=struct.pack('<'+'I'*(buckets+n),*heads,*chains)
    result=[(1,hoff+8,hash_table)]
    if b'.msym' in sec and b'.rel.dyn' in sec:
        moff,msize=sec[b'.msym'];roff,rsize=sec[b'.rel.dyn']
        if msize>=n*8 and rsize%16==0:
            first=[0]*n
            for index in range(1,rsize//16):
                info=struct.unpack_from('<I',data,roff+16*index+8)[0];symbol=info>>8
                if info and symbol<n and not first[symbol]:first[symbol]=index
            if max(first,default=0)<1<<24:
                msym=b''.join(struct.pack('<II',hashes[i],first[i]<<8) for i in range(n))
                result.append((2,moff,msym))
    return result


def transform(data,mode=3):
    if mode not in range(4):raise ValueError('invalid ECOFF constraint policy')
    transformed=bytearray(data);changes=[];stats={'objects':0,'hash_tables':0,'msym_tables':0,'derived_bytes':0}
    for offset,size in objects(data):
        stats['objects']+=1;mask=0;original=data[offset:offset+size]
        for bit,start,expected in predicted(original):
            if mode&bit and original[start:start+len(expected)]==expected:
                transformed[offset+start:offset+start+len(expected)]=bytes(len(expected));mask|=bit
                stats['hash_tables' if bit==1 else 'msym_tables']+=1;stats['derived_bytes']+=len(expected)
        if mask:changes.append((offset,size,mask))
    metadata=bytearray(vencode(len(changes)));previous_end=0
    for offset,size,mask in changes:
        metadata.extend(vencode(offset-previous_end));metadata.extend(vencode(size));metadata.append(mask);previous_end=offset+size
    raw=bytes(transformed)+metadata+len(metadata).to_bytes(8,'little')+TRAILER
    return raw,dict(**stats,mode=mode,original_bytes=len(data),transformed_bytes=len(raw),constraint_metadata_bytes=len(metadata)+13)


def inverse(raw):
    if len(raw)<14 or raw[-5:]!=TRAILER:raise ValueError('invalid ECOFF constraint trailer')
    length=int.from_bytes(raw[-13:-5],'little');start=len(raw)-13-length
    if start<0:raise ValueError('ECOFF metadata outside frame')
    data=bytearray(raw[:start]);meta=raw[start:-13];n,pos=vdecode(meta,0);previous_end=0
    if n>len(data)//104:raise ValueError('excessive ECOFF object count')
    for _ in range(n):
        delta,pos=vdecode(meta,pos);size,pos=vdecode(meta,pos);offset=previous_end+delta
        if pos>=len(meta):raise ValueError('missing ECOFF constraint mask')
        mask=meta[pos];pos+=1
        if mask not in (1,2,3) or offset+size>len(data):raise ValueError('invalid ECOFF constraint descriptor')
        candidates=predicted(bytes(data[offset:offset+size]));seen=0
        for bit,where,expected in candidates:
            if mask&bit:
                if any(data[offset+where:offset+where+len(expected)]):raise ValueError('derived ECOFF field is not zero')
                data[offset+where:offset+where+len(expected)]=expected;seen|=bit
        if seen!=mask:raise ValueError('ECOFF dependencies missing')
        previous_end=offset+size
    if pos!=len(meta):raise ValueError('unused ECOFF metadata')
    return bytes(data)
