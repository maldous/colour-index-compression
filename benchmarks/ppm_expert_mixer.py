"""CIXQ5: mix a generic order-six byte PPM distribution with bit predictors."""
from contextlib import contextmanager
import zlib
from cix import fixedmix as m
from cix.multinomial import vencode,vdecode
from benchmarks.extended_mixer import policy as extended_policy
MAGIC=b'CIXQ\x05'


@contextmanager
def policy(bits):
    with extended_policy(bits):
        base=m._State
        class State(base):
            def __init__(self,eta_shift):
                super().__init__(eta_shift)
                for row in self.weights:row[:]=[44]*23
                self.initial_weights=[row[:] for row in self.weights]
                self.byte_tables=[{} for _ in range(7)]
            def distribution(self):
                weights=[0]*256;excluded=set();remaining=1<<24
                for order in range(min(6,len(self.history)),-1,-1):
                    context=bytes(self.history[-order:]) if order else b''
                    counts=self.byte_tables[order].get(context)
                    if not counts:continue
                    eligible=[(symbol,count) for symbol,count in counts.items() if symbol not in excluded]
                    if not eligible:continue
                    mass=sum(c for _,c in eligible);distinct=len(eligible)
                    for symbol,count in eligible:
                        weights[symbol]+=remaining*count//(mass+distinct);excluded.add(symbol)
                    remaining=remaining*distinct//(mass+distinct)
                unseen=256-len(excluded);cumulative=[0]
                for symbol,weight in enumerate(weights):
                    if symbol not in excluded and unseen:weight+=remaining//unseen
                    cumulative.append(cumulative[-1]+weight+1)
                return cumulative
            def probabilities(self,bit_position,prefix_bits):
                _,stretches,keys=super().probabilities(bit_position,prefix_bits)
                if bit_position==0:self.cumulative=self.distribution()
                lo=prefix_bits<<(8-bit_position);hi=lo+(1<<(8-bit_position));mid=(lo+hi)//2
                c=self.cumulative;probability=max(1,min(4095,4096*(c[hi]-c[mid])//(c[hi]-c[lo])))
                stretches.append(m._STRETCH[probability])
                mixed=self.bias[bit_position]+sum(w*s for w,s in zip(self.weights[bit_position],stretches))//m.WEIGHT_SCALE
                return m._squash(mixed),stretches,keys
            def finish_byte(self,byte):
                for order in range(min(6,len(self.history))+1):
                    context=bytes(self.history[-order:]) if order else b''
                    counts=self.byte_tables[order].setdefault(context,{})
                    counts[byte]=counts.get(byte,0)+1
                    if sum(counts.values())>16384:
                        for symbol in counts:counts[symbol]=(counts[symbol]+1)//2
                super().finish_byte(byte)
        m._State=State
        try:yield
        finally:m._State=base


def encode(data,bits):
    with policy(bits):payload=m.encode_fixed_mix(data,eta_shift=6)
    return MAGIC+bytes([bits])+vencode(len(data))+zlib.crc32(data).to_bytes(4,'big')+payload


def decode(frame):
    if frame[:5]!=MAGIC:raise ValueError('unknown PPM-expert frame')
    bits=frame[5];length,pos=vdecode(frame,6)
    if pos+4>len(frame):raise ValueError('truncated frame')
    checksum=int.from_bytes(frame[pos:pos+4],'big')
    with policy(bits):data=m.decode_fixed_mix(frame[pos+4:],source_length=length)
    if zlib.crc32(data)!=checksum:raise ValueError('checksum mismatch')
    return data


def native_encoder():
    from benchmarks.native_contextual_mixer import encoder
    native=encoder('results/leaderboard/native_mixer_ppm.so')
    def encode(data,bits):return MAGIC+native(data,bits)[5:]
    return encode
