"""CIXQ2: symmetric rounding of signed learning updates, exact fixed prediction."""
from contextlib import contextmanager
import zlib
from cix import fixedmix as m
from cix.multinomial import vencode,vdecode
from benchmarks.contextual_mixer import state_policy

MAGIC=b'CIXQ\x02'


def rounded(n,d):return (n+d//2)//d if n>=0 else -((-n+d//2)//d)


@contextmanager
def policy(bits):
    with state_policy(bits):
        base=m._State
        class State(base):
            def update(self,bit_position,prefix_bits,bit,probability_one,stretches,keys):
                old=self.weights[bit_position][:];bias=self.bias[bit_position]
                super().update(bit_position,prefix_bits,bit,probability_one,stretches,keys)
                error=m.PROB_SCALE-probability_one if bit else -probability_one
                delta=rounded(error*m.LOG_SCALE,m.PROB_SCALE*(1<<self.eta_shift))
                self.bias[bit_position]=max(-m.CLIP_LOG,min(m.CLIP_LOG,bias+delta))
                denominator=m.PROB_SCALE*m.LOG_SCALE*(1<<self.eta_shift)
                for i,stretch in enumerate(stretches):
                    delta=rounded(error*stretch*m.WEIGHT_SCALE,denominator)
                    self.weights[bit_position][i]=max(-4*m.WEIGHT_SCALE,min(4*m.WEIGHT_SCALE,old[i]+delta))
        m._State=State
        try:yield
        finally:m._State=base


def encode(data,bits):
    with policy(bits):payload=m.encode_fixed_mix(data,eta_shift=6)
    return MAGIC+bytes([bits])+vencode(len(data))+zlib.crc32(data).to_bytes(4,'big')+payload


def decode(frame):
    if frame[:5]!=MAGIC:raise ValueError('unknown rounded mixer frame')
    bits=frame[5];length,pos=vdecode(frame,6)
    if pos+4>len(frame):raise ValueError('truncated frame')
    checksum=int.from_bytes(frame[pos:pos+4],'big')
    with policy(bits):data=m.decode_fixed_mix(frame[pos+4:],source_length=length)
    if zlib.crc32(data)!=checksum:raise ValueError('checksum mismatch')
    return data


def native_encoder():
    from benchmarks.native_contextual_mixer import encoder
    native=encoder('results/leaderboard/native_mixer_rounding.so')
    def encode(data,bits):return MAGIC+native(data,bits)[5:]
    return encode
