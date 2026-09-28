"""Fixed-width and restricted-alphabet refinement of the database constraints."""
import collections
import zlib
from cix.multinomial import vencode,vdecode
from benchmarks import mysql_record_constraints as base
from benchmarks.record_float_grid import signed,read_signed

MAGIC=b'CIXD\x02'
RAW=b'MYCC1'


def pack_ids(ids,width):
    out=bytearray();acc=0;bits=0
    for value in ids:
        acc=(acc<<width)|value;bits+=width
        while bits>=8:bits-=8;out.append((acc>>bits)&255)
        acc&=(1<<bits)-1
    if bits:out.append(acc<<(8-bits))
    return bytes(out)


def unpack_ids(blob,n,width):
    if len(blob)!=(n*width+7)//8:raise ValueError('fixed alphabet payload length')
    out=[];acc=0;bits=0;at=0;mask=(1<<width)-1
    for _ in range(n):
        while bits<width:acc=(acc<<8)|blob[at];at+=1;bits+=8
        bits-=width;out.append((acc>>bits)&mask);acc&=(1<<bits)-1
    if acc:raise ValueError('nonzero alphabet padding')
    return out


def transform(data,mode=1):
    if mode not in (1,2,3,4):raise ValueError('invalid fixed-column policy')
    raw,stats=base.transform(data,3);nr,pos=vdecode(raw,5);size=(nr+7)//8;flags=raw[pos:pos+size];pos+=size
    n=sum((flags[i//8]>>(i%8))&1 for i in range(nr));_,pos=base.read(raw,pos)
    out=bytearray(RAW+raw[5:pos]);changed=[]
    for index in range(9):
        column,pos=base.read(raw,pos);replacement=b'\0'+column
        if column[0]==0 and n:
            values=base.column_decode(column,n);width=len(values[0])
            if all(len(value)==width for value in values):
                content=b''.join(values);replacement=bytes([mode])+vencode(width)
                if mode==1:replacement+=content
                else:
                    palette=sorted(set(content));lookup={x:i for i,x in enumerate(palette)};ids=[lookup[x] for x in content]
                    replacement+=vencode(len(palette))+bytes(palette);counts=collections.Counter(ids)
                    if mode==2:replacement+=pack_ids(ids,(len(palette)-1).bit_length())
                    else:
                        average=len(content)//max(1,len(palette));profile=[counts[i] for i in range(len(palette))]
                        replacement+=b''.join(signed(count-average) for count in profile)
                        replacement+=base.order_encode(ids,profile,3 if mode==3 else 2)
                changed.append(dict(index=index,width=width,original_column_bytes=len(column),new_column_bytes=len(replacement)))
        out.extend(base.pack(replacement))
    if pos!=len(raw):raise ValueError('trailing database transform')
    return bytes(out),dict(mode=mode,original_bytes=len(data),transformed_bytes=len(out),parsed_records=n,refined_columns=changed)


def inverse(blob):
    if blob[:5]!=RAW:raise ValueError('invalid fixed-column transform')
    nr,pos=vdecode(blob,5);size=(nr+7)//8;flags=blob[pos:pos+size];pos+=size
    if len(flags)!=size:raise ValueError('truncated flags')
    n=sum((flags[i//8]>>(i%8))&1 for i in range(nr));_,pos=base.read(blob,pos);out=bytearray(base.RAW+blob[5:pos])
    for _ in range(9):
        column,pos=base.read(blob,pos)
        if not column:raise ValueError('missing fixed-column mode')
        mode=column[0]
        if mode==0:decoded=column[1:]
        else:
            width,at=vdecode(column,1);length=width*n
            if mode==1:content=column[at:]
            elif mode in (2,3,4):
                k,at=vdecode(column,at);palette=column[at:at+k];at+=k
                if k>256 or len(palette)!=k or (not k and length):raise ValueError('invalid fixed-column alphabet')
                if mode==2:ids=unpack_ids(column[at:],length,(k-1).bit_length() if k else 0)
                else:
                    counts=[];average=length//max(1,k)
                    for _ in range(k):delta,at=read_signed(column,at);counts.append(average+delta)
                    if any(c<=0 for c in counts) or sum(counts)!=length:raise ValueError('invalid fixed-column composition')
                    ids=base.order_decode(column[at:],counts)
                if any(i>=k for i in ids):raise ValueError('fixed-column symbol outside alphabet')
                content=bytes(palette[i] for i in ids)
            else:raise ValueError('invalid fixed-column coding')
            if len(content)!=length:raise ValueError('fixed column length mismatch')
            decoded=b'\0'+b''.join(base.pack(content[i*width:(i+1)*width]) for i in range(n))
        out.extend(base.pack(decoded))
    if pos!=len(blob):raise ValueError('trailing fixed columns')
    return base.inverse(bytes(out))


def encode(data,mode=1):
    import brotli
    raw,stats=transform(data,mode);frame=MAGIC+vencode(len(data))+zlib.crc32(data).to_bytes(4,'big')+brotli.compress(raw,quality=11)
    return frame,dict(**stats,physical_bytes=len(frame))


def decode(frame):
    import brotli
    if frame[:5]!=MAGIC:raise ValueError('invalid fixed-column frame')
    n,pos=vdecode(frame,5);crc=int.from_bytes(frame[pos:pos+4],'big');data=inverse(brotli.decompress(frame[pos+4:]))
    if len(data)!=n or zlib.crc32(data)!=crc:raise ValueError('fixed-column checksum mismatch')
    return data
