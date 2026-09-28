"""Causal bond geometry constrains heavy-atom candidates; exact residuals remain.

The proven hydrogen transform supplies the skeleton and hydrogen choices. This
second stage changes only coordinate residuals. Its inverse reconstructs the
complete hydrogen stream, then delegates exact source formatting to that codec.
No input filename, corpus identity, or original-byte table is consulted.
"""
from collections import Counter
from math import isqrt, log2
from cix.multinomial import vencode, vdecode, _ArithmeticEncoder, _ArithmeticDecoder
from benchmarks import sdf_hydrogen as h

MAGIC = b'SDFK\x01'


def pack(blob): return vencode(len(blob))+blob


def read(blob, pos):
    n, pos = vdecode(blob, pos)
    end = pos+n
    if end > len(blob): raise ValueError('truncated heavy geometry section')
    return blob[pos:end], end


def view(raw):
    if raw[:7] != h.MAGIC+b'\x02\x00': raise ValueError('unsupported underlying hydrogen policy')
    radius, pos = vdecode(raw, 7)
    nr, pos = vdecode(raw, pos)
    nf = (nr+7)//8
    flags = raw[pos:pos+nf];pos += nf
    if len(flags) != nf: raise ValueError('truncated hydrogen flags')
    body, pos = read(raw, pos)
    digits, pos = read(raw, pos)
    records = body.split(h.SEP)
    if len(records) != nr: raise ValueError('hydrogen record count mismatch')
    return dict(radius=radius, flags=flags, records=records, digits=digits,
                prefix=raw[:pos], tail=raw[pos:])


def learn_radius(data):
    counts = Counter()
    for record in data.split(h.SEP):
        try: _, coords, _, adj, types = h.parse(record)
        except (ValueError, IndexError): continue
        for i, xyz in enumerate(coords):
            if types[i] == b'H': continue
            for j in adj[i]:
                if j >= i or types[j] == b'H': continue
                radius = ((isqrt(sum((xyz[k]-coords[j][k])**2 for k in range(3)))+50)//100)*100
                if 0 < radius <= 1000000: counts[radius] += 1
    return max(counts, key=lambda r:(counts[r],-r)) if counts else 10000


def heavy_options(i, coords, parents, adj, types, model, radius, fallback):
    known = [j for j in adj[i] if j < i and types[j] != b'H']
    if model == 0 or types[i] == b'H' or not known: return [fallback], 0
    centre = parents[i] if parents[i] in known else known[0]
    origin = coords[centre]
    if origin[2]: return [fallback], 0
    options = []
    # Two already decoded neighbours constrain placement to two intersections.
    if model == 3 and len(known) >= 2:
        a, b = coords[known[0]], coords[known[1]]
        dx, dy = b[0]-a[0], b[1]-a[1]
        d2 = dx*dx+dy*dy
        if not a[2] and not b[2] and 0 < d2 <= 4*radius*radius:
            scale = 1 << 24
            ratio = isqrt(((4*radius*radius-d2)*scale*scale)//d2)
            ox, oy = h.rounded(-dy*ratio,2*scale), h.rounded(dx*ratio,2*scale)
            mx, my = h.rounded(a[0]+b[0],2), h.rounded(a[1]+b[1],2)
            options = [(mx+ox,my+oy,0),(mx-ox,my-oy,0)]
    if not options:
        neighbours = [j for j in adj[centre] if j < i and j != i and types[j] != b'H'
                      and not coords[j][2] and coords[j] != origin]
        if model >= 2 and neighbours:
            other = coords[min(neighbours)]
            phase = h.angle(other[0]-origin[0],other[1]-origin[1])
            phases = [phase+h.TURN*j//6 for j in (2,4,3,1,5)]
        else:
            phases = [h.TURN*j//12 for j in range(12)]
        for phase in phases:
            delta = h.direction(phase,radius)
            options.append(tuple(origin[k]+delta[k] for k in range(3)))
    # Occupied bond directions are redundant candidate slots. Excluding one is
    # always reversible: arbitrary placements still have an unrestricted residual.
    occupied = [coords[j] for j in adj[centre] if j < i]
    options = [p for p in options if all(sum((p[k]-q[k])**2 for k in range(3)) > radius*radius//16 for q in occupied)]
    options.append(fallback)
    return list(dict.fromkeys(options)), min(2,len(known))


class Choices:
    def __init__(self, representation, payload=None):
        self.rep = representation;self.payload = payload;self.at = 0
        self.rank = int.from_bytes(payload,'little') if representation == 1 and payload is not None else 0
        self.product = 1;self.digits = bytearray();self.freq = {};self.uniform_bits = 0.;self.model_bits = 0.;self.events = 0
        if representation >= 2:
            if payload is None: self.arithmetic = _ArithmeticEncoder()
            else:
                bits, pos = vdecode(payload,0)
                if pos+(bits+7)//8 != len(payload): raise ValueError('invalid heavy arithmetic framing')
                self.arithmetic = _ArithmeticDecoder(payload[pos:],bits)

    def symbol(self, k, context, chosen=None):
        if k == 1: return 0
        self.events += 1;self.uniform_bits += log2(k)
        encode = chosen is not None
        if self.rep == 0:
            if encode: self.digits.append(48+chosen)
            else:
                if self.at >= len(self.payload): raise ValueError('missing heavy choice')
                chosen = self.payload[self.at]-48;self.at += 1
        elif self.rep == 1:
            if encode: self.rank += self.product*chosen;self.product *= k
            else: chosen = self.rank%k;self.rank //= k
        else:
            counts = self.freq.setdefault((k,context),[1]*k);total = sum(counts)
            if encode:
                lo = sum(counts[:chosen]);self.arithmetic.encode(lo,lo+counts[chosen],total)
            else:
                target = self.arithmetic.target(total);lo = 0
                for chosen,count in enumerate(counts):
                    if target < lo+count: self.arithmetic.update(lo,lo+count,total);break
                    lo += count
                else: raise ValueError('invalid heavy arithmetic choice')
            self.model_bits += log2(total/counts[chosen])
            if self.rep == 3:
                counts[chosen] += 1
                if sum(counts)>4096: counts[:] = [(c+1)//2 for c in counts]
        if not 0 <= chosen < k: raise ValueError('heavy choice outside alphabet')
        return chosen

    def finish(self):
        if self.rep == 0: return bytes(self.digits)
        if self.rep == 1: return self.rank.to_bytes(((self.product-1).bit_length()+7)//8,'little')
        payload,bits = self.arithmetic.finish()
        return vencode(bits)+payload


def transcode(state, vectors, model, radius, choices, encoding):
    out=[];digit_at=0;vector_at=0;stats=Counter()
    for r,record in enumerate(state['records']):
        if not state['flags'][r//8]&(1<<(r%8)): continue
        n,parents,adj,types=h.topology(record.splitlines(keepends=True),True)
        coords=[];slots={}
        for i in range(n):
            options,key=h.candidates(i,coords,parents,adj,types,slots,2,state['radius'])
            chosen=0
            if len(options)>1:
                if digit_at >= len(state['digits']): raise ValueError('missing hydrogen choice')
                chosen=state['digits'][digit_at]-48;digit_at+=1
                if not 0<=chosen<len(options): raise ValueError('invalid hydrogen choice')
            base=options[chosen]
            candidates,context=heavy_options(i,coords,parents,adj,types,model,radius,base)
            if vector_at >= len(vectors): raise ValueError('missing heavy vector')
            residual=vectors[vector_at];vector_at+=1
            if encoding:
                actual=tuple(base[k]+residual[k] for k in range(3))
                choice=min(range(len(candidates)),key=lambda j:(sum((actual[k]-candidates[j][k])**2 for k in range(3)),j))
                choices.symbol(len(candidates),context,choice)
                changed=tuple(actual[k]-candidates[choice][k] for k in range(3))
                if len(candidates)>1:
                    stats['heavy_predictions']+=1;stats['within_two_units']+=max(map(abs,changed))<=2
            else:
                choice=choices.symbol(len(candidates),context)
                actual=tuple(candidates[choice][k]+residual[k] for k in range(3))
                changed=tuple(actual[k]-base[k] for k in range(3))
            coords.append(actual);out.append(changed)
            if key is not None: slots[key].pop(chosen)
    if vector_at!=len(vectors) or digit_at!=len(state['digits']): raise ValueError('unused hydrogen vectors or choices')
    return out,dict(stats)


def parse_vectors(blob):
    vectors=[tuple(map(int,line.split(b','))) for line in blob.splitlines()]
    if any(len(v)!=3 for v in vectors): raise ValueError('invalid heavy residual vector')
    return vectors


def vector_bytes(vectors): return b''.join(('%d,%d,%d\n'%v).encode() for v in vectors)


def encode(data, model=2, representation=0):
    if model not in range(4) or representation not in range(4): raise ValueError('invalid heavy policy')
    baseline,_=h.encode(data,2,0);state=view(baseline);radius=learn_radius(data)
    choices=Choices(representation)
    vectors,stats=transcode(state,parse_vectors(state['tail']),model,radius,choices,True)
    payload=choices.finish()
    raw=MAGIC+bytes([model,representation])+vencode(radius)+pack(state['prefix'])+pack(payload)+vector_bytes(vectors)
    return raw,dict(**stats,model=model,representation=representation,radius=radius,
        original_bytes=len(data),transformed_bytes=len(raw),heavy_choices=choices.events,
        heavy_combinatorial_bits=choices.uniform_bits,heavy_model_bits=choices.model_bits if representation>=2 else None,
        heavy_choice_bytes=len(payload))


def decode(raw):
    if raw[:5]!=MAGIC or len(raw)<7: raise ValueError('invalid heavy geometry stream')
    model,rep=raw[5:7]
    if model not in range(4) or rep not in range(4): raise ValueError('invalid heavy policy')
    radius,pos=vdecode(raw,7)
    if not 0<radius<=1000000: raise ValueError('invalid learned radius')
    prefix,pos=read(raw,pos);payload,pos=read(raw,pos);state=view(prefix)
    if state['tail']: raise ValueError('heavy frame contains duplicate residuals')
    choices=Choices(rep,payload)
    vectors,_=transcode(state,parse_vectors(raw[pos:]),model,radius,choices,False)
    if (rep==0 and choices.at!=len(payload)) or (rep==1 and choices.rank): raise ValueError('unused heavy choices')
    return h.decode(prefix+vector_bytes(vectors))
