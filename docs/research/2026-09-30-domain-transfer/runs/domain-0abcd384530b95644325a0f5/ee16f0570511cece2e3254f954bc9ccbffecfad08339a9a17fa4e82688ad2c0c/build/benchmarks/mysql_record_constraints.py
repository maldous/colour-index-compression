"""Reversible MyISAM record columns, conditional alphabets and occupancy counts.

The supported historical layout has two integer keys, a small integer, two
floating fields, decimal text, a date, and three character columns. Unsupported
records remain literal. Dictionaries and compositions come from the input and
are fully transmitted. No benchmark bytes or generated-data seeds are built in.
"""
import collections
import datetime
import math
import zlib
from cix.multinomial import vencode,vdecode,Fenwick,_ArithmeticEncoder,_ArithmeticDecoder,multinomial_cardinality

MAGIC=b'CIXD\x01'
RAW=b'MYCS1'
NUMERIC={0,1,2,5}


def pack(blob):return vencode(len(blob))+blob


def read(blob,pos):
    size,pos=vdecode(blob,pos);end=pos+size
    if end>len(blob):raise ValueError('truncated column')
    return blob[pos:end],end


def wrap(body):
    n=len(body)
    if n>65535:raise ValueError('oversized record')
    if n%4==1:return b'\x01'+n.to_bytes(2,'big')+body
    pad=(-n)%4
    return b'\x03'+n.to_bytes(2,'big')+bytes([pad])+body+bytes(pad)


def fields(body):
    if len(body)<24 or body[:2] not in (b'\x60\x00',b'\x60\x02'):raise ValueError('unsupported field flags')
    at=22;length=body[at];at+=1;money=body[at:at+length];at+=length
    if at>=len(body):raise ValueError('truncated money')
    length=body[at];at+=1;date=body[at:at+length];at+=length
    if at+30>len(body):raise ValueError('truncated fixed fields')
    m,d,y=map(int,date.split(b'/'));day=datetime.date(y,m,d)
    if f'{m}/{d}/{y}'.encode()!=date:raise ValueError('noncanonical date')
    code=body[at:at+10];name=body[at+10:at+30];at+=30;address=body[at:]
    if body[1]==2:
        if not address or address[0]!=len(address)-1 or address[0]>=80:raise ValueError('invalid short address')
        address=address[1:]
    elif len(address)!=80:raise ValueError('invalid full address')
    return [body[2:6],body[6:10],body[10:14],body[14:18],body[18:22]+bytes([len(money)])+money,
            day.toordinal().to_bytes(4,'little'),code,name,address]


def join_fields(row):
    key,integer,small,floating,money,date,code,name,address=row
    if any(len(x)!=4 for x in (key,integer,small,floating,date)) or len(code)!=10 or len(name)!=20:raise ValueError('invalid fixed column width')
    if len(money)<5 or money[4]!=len(money)-5 or len(address)>80:raise ValueError('invalid variable column width')
    day=datetime.date.fromordinal(int.from_bytes(date,'little'));date=f'{day.month}/{day.day}/{day.year}'.encode()
    return (b'\x60'+bytes([2 if len(address)<80 else 0])+key+integer+small+floating+money+
        bytes([len(date)])+date+code+name+(bytes([len(address)]) if len(address)<80 else b'')+address)


def split(data):
    at=0;records=[];columns=[[] for _ in range(9)]
    while at<len(data):
        start=at
        if len(data)-at<4 or data[at] not in (1,3):records.append(data[at:]);break
        kind=data[at];size=int.from_bytes(data[at+1:at+3],'big');header=3+(kind==3);padding=data[at+3] if kind==3 else 0
        end=at+header+size+padding
        if end>len(data) or not size:records.append(data[at:]);break
        raw=data[at:end];body=data[at+header:at+header+size];at=end
        try:
            row=fields(body)
            if wrap(join_fields(row))!=raw:raise ValueError('noncanonical record storage')
        except (ValueError,OverflowError,IndexError):records.append(raw);continue
        records.append(None)
        for col,value in zip(columns,row):col.append(value)
    return records,columns


def order_encode(ids,counts,mode):
    n=len(ids);k=len(counts)
    if mode==1:return b'\x00'+b''.join(vencode(x) for x in ids)
    if mode==4 and all(c==1 for c in counts):
        # Conditional Lehmer digits: each previously used colour is eliminated.
        fenwick=Fenwick(counts);out=bytearray(b'\x04');remaining=n;rank=0;product=1;used=0
        for symbol in ids:
            digit=fenwick.prefix(symbol);rank=rank*remaining+digit;product*=remaining
            fenwick.add(symbol,-1);remaining-=1;used+=1
            if used==1024 or not remaining:
                out.extend(rank.to_bytes(((product-1).bit_length()+7)//8,'big'));rank=0;product=1;used=0
        return bytes(out)
    if mode==4 and n<=4096:
        cardinality=multinomial_cardinality(counts);total=cardinality;remaining=n;mutable=counts[:];tree=Fenwick(mutable);rank=0
        for symbol in ids:
            rank+=total*tree.prefix(symbol)//remaining;total=total*mutable[symbol]//remaining
            mutable[symbol]-=1;tree.add(symbol,-1);remaining-=1
        return b'\x03'+rank.to_bytes(((cardinality-1).bit_length()+7)//8,'big')
    encoder=_ArithmeticEncoder();mutable=counts[:];tree=Fenwick(mutable);remaining=n;dynamic=mode!=2
    for symbol in ids:
        low=tree.prefix(symbol);encoder.encode(low,low+mutable[symbol],remaining)
        if dynamic:mutable[symbol]-=1;tree.add(symbol,-1);remaining-=1
    payload,bits=encoder.finish()
    return bytes([2 if dynamic else 1])+vencode(bits)+payload


def order_decode(blob,counts):
    if not blob:raise ValueError('missing ordering mode')
    kind=blob[0];n=sum(counts);k=len(counts);pos=1;out=[]
    if kind==0:
        for _ in range(n):x,pos=vdecode(blob,pos);out.append(x)
        if pos!=len(blob):raise ValueError('trailing IDs')
    elif kind in (1,2):
        bits,pos=vdecode(blob,pos)
        if len(blob)-pos!=(bits+7)//8:raise ValueError('order arithmetic length')
        decoder=_ArithmeticDecoder(blob[pos:],bits);mutable=counts[:];tree=Fenwick(mutable);remaining=n
        for _ in range(n):
            target=decoder.target(remaining);symbol=tree.select(target);low=tree.prefix(symbol)
            decoder.update(low,low+mutable[symbol],remaining);out.append(symbol)
            if kind==2:mutable[symbol]-=1;tree.add(symbol,-1);remaining-=1
    elif kind==3:
        if n>4096:raise ValueError('oversized exact rank')
        total=multinomial_cardinality(counts);rank=int.from_bytes(blob[1:],'big')
        if len(blob)-1!=((total-1).bit_length()+7)//8 or rank>=total:raise ValueError('invalid type-class rank')
        mutable=counts[:];tree=Fenwick(mutable);remaining=n
        while remaining:
            symbol=tree.select(rank*remaining//total);rank-=total*tree.prefix(symbol)//remaining
            total=total*mutable[symbol]//remaining;out.append(symbol);mutable[symbol]-=1;tree.add(symbol,-1);remaining-=1
    elif kind==4:
        if any(c!=1 for c in counts):raise ValueError('not a permutation')
        tree=Fenwick(counts);remaining=n
        while remaining:
            length=min(1024,remaining);bases=list(range(remaining,remaining-length,-1));product=math.prod(bases);width=((product-1).bit_length()+7)//8
            rank=int.from_bytes(blob[pos:pos+width],'big');pos+=width
            if pos>len(blob) or rank>=product:raise ValueError('invalid conditional permutation rank')
            digits=[0]*length
            for i in range(length-1,-1,-1):rank,digits[i]=divmod(rank,bases[i])
            for digit in digits:
                symbol=tree.select(digit);out.append(symbol);tree.add(symbol,-1);remaining-=1
        if pos!=len(blob):raise ValueError('trailing permutation ranks')
    else:raise ValueError('invalid ordering mode')
    if len(out)!=n or collections.Counter(out)!=collections.Counter({i:c for i,c in enumerate(counts)}):raise ValueError('ordering composition mismatch')
    return out


def column_encode(values,index,mode):
    if mode==0 or index==6:return b'\x00'+b''.join(pack(x) for x in values),dict(kind='literal',values=len(values))
    numeric=index in NUMERIC;palette=sorted(set(values),key=(lambda x:int.from_bytes(x,'little')) if numeric else None)
    counts=collections.Counter(values);lookup={x:i for i,x in enumerate(palette)};ids=[lookup[x] for x in values]
    out=bytearray(bytes([2 if numeric else 1])+vencode(len(palette)));previous=0
    for value in palette:
        if numeric:
            current=int.from_bytes(value,'little');out.extend(vencode(current-previous));previous=current
        else:out.extend(pack(value))
        out.extend(vencode(counts[value]))
    profile=[counts[x] for x in palette];ordering=order_encode(ids,profile,mode);out.extend(pack(ordering))
    bits=(math.lgamma(len(values)+1)-sum(math.lgamma(c+1) for c in profile))/math.log(2)
    return bytes(out),dict(kind='dictionary',values=len(values),alphabet=len(palette),composition_bits=bits,ordering_bytes=len(ordering),dictionary_and_counts_bytes=len(out)-len(ordering),order_mode=ordering[0])


def column_decode(blob,n):
    kind=blob[0];pos=1;values=[]
    if kind==0:
        for _ in range(n):value,pos=read(blob,pos);values.append(value)
    elif kind in (1,2):
        k,pos=vdecode(blob,pos)
        if not 0<=k<=n:raise ValueError('invalid dictionary size')
        palette=[];counts=[];previous=0
        for _ in range(k):
            if kind==2:
                delta,pos=vdecode(blob,pos);previous+=delta
                if previous>=1<<32:raise ValueError('integer dictionary overflow')
                value=previous.to_bytes(4,'little')
            else:value,pos=read(blob,pos)
            count,pos=vdecode(blob,pos)
            if not count:raise ValueError('empty dictionary colour')
            palette.append(value);counts.append(count)
        if sum(counts)!=n:raise ValueError('composition length mismatch')
        payload,pos=read(blob,pos);values=[palette[x] for x in order_decode(payload,counts)]
    else:raise ValueError('invalid column mode')
    if pos!=len(blob):raise ValueError('trailing column data')
    return values


def transform(data,mode=3):
    if mode not in range(5):raise ValueError('invalid column policy')
    records,columns=split(data);n=len(records);flags=bytearray((n+7)//8);exceptions=bytearray()
    for i,record in enumerate(records):
        if record is None:flags[i//8]|=1<<(i%8)
        else:exceptions.extend(pack(record))
    out=bytearray(RAW+vencode(n)+flags+pack(exceptions));stats=[]
    for index,values in enumerate(columns):
        column,measurement=column_encode(values,index,mode);out.extend(pack(column));stats.append(dict(index=index,**measurement))
    return bytes(out),dict(mode=mode,original_bytes=len(data),records=n,parsed_records=len(columns[0]),literal_records=n-len(columns[0]),transformed_bytes=len(out),columns=stats)


def inverse(blob):
    if blob[:5]!=RAW:raise ValueError('invalid MyISAM transform')
    nr,pos=vdecode(blob,5);size=(nr+7)//8;flags=blob[pos:pos+size];pos+=size
    if len(flags)!=size:raise ValueError('truncated record flags')
    n=sum((flags[i//8]>>(i%8))&1 for i in range(nr));exceptions,pos=read(blob,pos);columns=[]
    for _ in range(9):column,pos=read(blob,pos);columns.append(column_decode(column,n))
    if pos!=len(blob):raise ValueError('trailing transform')
    out=bytearray();at=0;ep=0
    for i in range(nr):
        if (flags[i//8]>>(i%8))&1:
            out.extend(wrap(join_fields([col[at] for col in columns])));at+=1
        else:raw,ep=read(exceptions,ep);out.extend(raw)
    if ep!=len(exceptions):raise ValueError('trailing exceptions')
    return bytes(out)


def encode(data,mode=3,backend=0,paq_options='-4'):
    import brotli
    raw,stats=transform(data,mode)
    if backend==0:payload=brotli.compress(raw,quality=11)
    elif backend==1:
        from benchmarks.competitive_codec import encode_paq
        payload=encode_paq(raw,'v215',paq_options)
    else:raise ValueError('invalid record backend')
    frame=MAGIC+bytes([backend])+vencode(len(data))+zlib.crc32(data).to_bytes(4,'big')+payload
    return frame,dict(**stats,backend=backend,physical_bytes=len(frame))


def decode(frame):
    import brotli
    if frame[:5]!=MAGIC:raise ValueError('invalid MyISAM frame')
    backend=frame[5];n,pos=vdecode(frame,6);crc=int.from_bytes(frame[pos:pos+4],'big');pos+=4
    if backend==0:raw=brotli.decompress(frame[pos:])
    elif backend==1:
        from benchmarks.competitive_codec import decode as decode_paq
        raw=decode_paq(frame[pos:])
    else:raise ValueError('invalid record backend')
    data=inverse(raw)
    if len(data)!=n or zlib.crc32(data)!=crc:raise ValueError('MyISAM checksum mismatch')
    return data
