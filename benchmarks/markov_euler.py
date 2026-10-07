"""Exact Markov type classes: exclude row orderings that cannot form a trail.

Uses the directed matrix-tree / Whittle counting identity, not a new counting
theorem. Controls share start/end states, alphabet and every transition count.
Modes: 0 independent-row rank; 1 remaining-row arithmetic; 2 valid-trail rank;
3 arithmetic conditioned on the exact number of valid completions.
Reference: Whittle, JRSS B 17(2), 1955, doi:10.1111/j.2517-6161.1955.tb00197.x.
"""
from functools import lru_cache
import math
import zlib
from cix.multinomial import (vencode,vdecode,multinomial_cardinality,permutation_rank,
    permutation_unrank,_ArithmeticEncoder,_ArithmeticDecoder)

MAGIC = b'CIXW\x01'
MAX_LENGTH = 4096
MAX_ALPHABET = 16


def determinant(matrix):
    """Fraction-free Bareiss elimination, with exact pivoting."""
    a = [list(row) for row in matrix]; n = len(a)
    if not n: return 1
    denominator = 1; sign = 1
    for k in range(n-1):
        if not a[k][k]:
            pivot = next((i for i in range(k+1,n) if a[i][k]),None)
            if pivot is None: return 0
            a[k],a[pivot]=a[pivot],a[k];sign=-sign
        value=a[k][k]
        for i in range(k+1,n):
            for j in range(k+1,n):
                numerator=a[i][j]*value-a[i][k]*a[k][j]
                if numerator%denominator:raise ArithmeticError('nonintegral determinant step')
                a[i][j]=numerator//denominator
        for i in range(k+1,n):a[i][k]=0
        denominator=value
    return sign*a[-1][-1]


@lru_cache(maxsize=MAX_LENGTH+1)
def factorial(n):return math.factorial(n)


@lru_cache(maxsize=8192)
def cardinality(matrix,start,end):
    k=len(matrix);out=[sum(row) for row in matrix];incoming=[sum(matrix[i][j] for i in range(k)) for j in range(k)]
    if any(value<0 for row in matrix for value in row):return 0
    if not sum(out):return int(start==end)
    if any(out[i]-incoming[i] != int(i==start)-int(i==end) for i in range(k)):return 0
    active=[i for i in range(k) if out[i]+incoming[i] or i==end]
    other=[i for i in active if i!=end]
    laplacian=[[out[i]-matrix[i][i] if i==j else -matrix[i][j] for j in other] for i in other]
    trees=determinant(laplacian)
    if trees<=0:return 0
    numerator=trees;denominator=1
    for i in active:
        degree=out[i]-1+int(i==end)
        if degree<0:return 0
        numerator*=factorial(degree)
        for value in matrix[i]:denominator*=factorial(value)
    if numerator%denominator:raise ArithmeticError('nonintegral trail count')
    return numerator//denominator


def freeze(matrix):return tuple(tuple(row) for row in matrix)


def branches(matrix,current,end):
    sizes=[]
    for target,count in enumerate(matrix[current]):
        if not count:sizes.append(0);continue
        matrix[current][target]-=1;sizes.append(cardinality(freeze(matrix),target,end));matrix[current][target]+=1
    return sizes


def frequencies(sizes):
    total=sum(sizes)
    if not total:raise ValueError('no valid continuation')
    if total <= 1<<20:return sizes
    # Same exact-completion information; bounded arithmetic precision is explicit.
    return [max(1,(value*(1<<20))//total) if value else 0 for value in sizes]


def descriptor(data):
    alphabet=sorted(set(data));index={v:i for i,v in enumerate(alphabet)};sequence=[index[v] for v in data]
    if len(data)>MAX_LENGTH or len(alphabet)>MAX_ALPHABET:raise ValueError('bounded Markov experiment size exceeded')
    matrix=[[0]*len(alphabet) for _ in alphabet]
    for a,b in zip(sequence,sequence[1:]):matrix[a][b]+=1
    return alphabet,sequence,matrix


def row_rank(sequence,matrix):
    streams=[bytearray() for _ in matrix]
    for a,b in zip(sequence,sequence[1:]):streams[a].append(b)
    rank=0;product=1
    for stream,counts in zip(streams,matrix):
        rank+=permutation_rank(bytes(stream),counts)*product;product*=multinomial_cardinality(counts)
    return rank,product


def trail_rank(sequence,matrix):
    counts=[list(row) for row in matrix];current=sequence[0];end=sequence[-1];total=cardinality(freeze(counts),current,end);rank=0
    for actual in sequence[1:]:
        sizes=branches(counts,current,end)
        if not sizes[actual]:raise ValueError('actual transition has no valid completion')
        rank+=sum(sizes[:actual]);counts[current][actual]-=1;current=actual
    return rank,total


def encode(data,mode=2):
    if mode not in range(4):raise ValueError('unknown Markov representation')
    alphabet,sequence,matrix=descriptor(data);n=len(data);k=len(alphabet)
    header=bytearray(MAGIC+bytes([mode])+vencode(n)+vencode(k)+bytes(alphabet))
    if n:header.extend([sequence[0],sequence[-1]])
    for row in matrix:
        occupied=[(j,value) for j,value in enumerate(row) if value]
        header.extend(vencode(len(occupied)))
        for j,value in occupied:header.extend(vencode(j)+vencode(value))
    row_space=math.prod(multinomial_cardinality(row) for row in matrix)
    trail_space=cardinality(freeze(matrix),sequence[0],sequence[-1]) if n else 1
    if not trail_space:raise ValueError('empty actual trail class')
    if mode in (0,2):
        rank,space=(row_rank(sequence,matrix) if mode==0 else trail_rank(sequence,matrix)) if n else (0,1)
        bits=(space-1).bit_length();payload=rank.to_bytes((bits+7)//8,'big');model_bits=math.log2(space)
    else:
        coder=_ArithmeticEncoder();counts=[list(row) for row in matrix];current=sequence[0] if n else 0;model_bits=0.;coded=False
        for actual in sequence[1:]:
            sizes=counts[current] if mode==1 else frequencies(branches(counts,current,sequence[-1]));total=sum(sizes)
            low=sum(sizes[:actual]);high=low+sizes[actual]
            if high==low:raise ValueError('zero-probability transition')
            if sizes[actual]!=total:
                coder.encode(low,high,total);coded=True;model_bits+=math.log2(total/sizes[actual])
            counts[current][actual]-=1;current=actual
        payload,bits=coder.finish() if coded else (b'',0)
    frame=bytes(header)+vencode(bits)+payload+zlib.crc32(data).to_bytes(4,'big')
    return frame,dict(mode=mode,original_bytes=n,physical_bytes=len(frame),metadata_bytes=len(frame)-len(payload),payload_bytes=len(payload),payload_bits=bits,
                      row_space_bits=math.log2(row_space),valid_trail_space_bits=math.log2(trail_space),
                      impossible_order_bits_removed=math.log2(row_space)-math.log2(trail_space),model_bits=model_bits)


def decode(frame):
    if frame[:5]!=MAGIC or len(frame)<12 or frame[5] not in range(4):raise ValueError('invalid Markov frame')
    mode=frame[5];n,pos=vdecode(frame,6);k,pos=vdecode(frame,pos)
    if n>MAX_LENGTH or k>MAX_ALPHABET or k>n or (n and not k):raise ValueError('invalid Markov dimensions')
    alphabet=frame[pos:pos+k];pos+=k
    if list(alphabet)!=sorted(set(alphabet)):raise ValueError('invalid Markov alphabet')
    start=end=0
    if n:
        if pos+2>len(frame):raise ValueError('truncated Markov endpoints')
        start,end=frame[pos:pos+2];pos+=2
        if max(start,end)>=k:raise ValueError('endpoint outside alphabet')
    matrix=[[0]*k for _ in range(k)]
    for row in matrix:
        count,pos=vdecode(frame,pos);previous=-1
        if count>k:raise ValueError('too many transitions')
        for _ in range(count):
            j,pos=vdecode(frame,pos);value,pos=vdecode(frame,pos)
            if not previous<j<k or not 0<value<n:raise ValueError('invalid transition count')
            row[j]=value;previous=j
    if sum(map(sum,matrix))!=max(0,n-1):raise ValueError('transition sum mismatch')
    bits,pos=vdecode(frame,pos);size=(bits+7)//8
    if pos+size+4!=len(frame):raise ValueError('Markov payload length mismatch')
    payload=frame[pos:pos+size];crc=int.from_bytes(frame[-4:],'big');counts=[list(row) for row in matrix]
    space=(math.prod(multinomial_cardinality(row) for row in matrix) if mode==0 else cardinality(freeze(matrix),start,end)) if n else 1
    if not space:raise ValueError('no compatible trail')
    sequence=[start] if n else [];current=start
    if mode in (0,2):
        rank=int.from_bytes(payload,'big')
        if bits!=(space-1).bit_length() or rank>=space:raise ValueError('Markov rank outside class')
        if mode==0:
            streams=[]
            for row in matrix:
                count=multinomial_cardinality(row);streams.append(permutation_unrank(rank%count,row));rank//=count
            cursors=[0]*k
            for _ in range(max(0,n-1)):
                if cursors[current]>=len(streams[current]):raise ValueError('context exhausted before complete trail')
                target=streams[current][cursors[current]];cursors[current]+=1;sequence.append(target);counts[current][target]-=1;current=target
        else:
            for _ in range(max(0,n-1)):
                sizes=branches(counts,current,end)
                for target,count in enumerate(sizes):
                    if rank<count:break
                    rank-=count
                else:raise ValueError('no rank continuation')
                sequence.append(target);counts[current][target]-=1;current=target
    else:
        coder=_ArithmeticDecoder(payload,bits)
        for _ in range(max(0,n-1)):
            sizes=counts[current] if mode==1 else frequencies(branches(counts,current,end));total=sum(sizes)
            if not total:raise ValueError('context exhausted before complete trail')
            choices=[j for j,c in enumerate(sizes) if c]
            if len(choices)==1:target=choices[0]
            else:
                value=coder.target(total);low=0
                for target,count in enumerate(sizes):
                    if value<low+count:coder.update(low,low+count,total);break
                    low+=count
                else:raise ValueError('invalid arithmetic transition')
            sequence.append(target);counts[current][target]-=1;current=target
    if n and current!=end or any(value for row in counts for value in row):raise ValueError('incomplete Markov trail')
    output=bytes(alphabet[i] for i in sequence)
    if zlib.crc32(output)!=crc:raise ValueError('Markov checksum mismatch')
    return output
