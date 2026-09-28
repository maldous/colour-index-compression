"""CIXQ4: generic online calibration of extended fixed-point mixer probabilities."""
from contextlib import contextmanager
import zlib
from cix import fixedmix as m
from cix.multinomial import vencode,vdecode
from benchmarks.extended_mixer import policy as extended_policy
from benchmarks.rounded_mixer import rounded
MAGIC=b'CIXQ\x04'


@contextmanager
def policy(bits):
    with extended_policy(bits):
        base=m._State
        class State(base):
            def __init__(self,eta_shift):
                super().__init__(eta_shift)
                self.calibration=[[i*128 for i in range(33)] for _ in range(32)]
            def probabilities(self,bit_position,prefix_bits):
                raw,stretches,keys=super().probabilities(bit_position,prefix_bits)
                self.raw_probability=raw
                context=((self.history[-1]&3) if self.history else 0)*8+bit_position
                self.calibration_context=context
                bucket,fraction=divmod(raw,128);row=self.calibration[context]
                probability=max(1,min(4095,((128-fraction)*row[bucket]+fraction*row[bucket+1]+64)//128))
                return probability,stretches,keys
            def update(self,bit_position,prefix_bits,bit,probability_one,stretches,keys):
                raw=self.raw_probability
                super().update(bit_position,prefix_bits,bit,raw,stretches,keys)
                bucket,fraction=divmod(raw,128);row=self.calibration[self.calibration_context]
                for index,weight in ((bucket,128-fraction),(bucket+1,fraction)):
                    row[index]=max(0,min(4096,row[index]+rounded((bit*4096-row[index])*weight,8192)))
        m._State=State
        try:yield
        finally:m._State=base


def encode(data,bits):
    with policy(bits):payload=m.encode_fixed_mix(data,eta_shift=6)
    return MAGIC+bytes([bits])+vencode(len(data))+zlib.crc32(data).to_bytes(4,'big')+payload


def decode(frame):
    if frame[:5]!=MAGIC:raise ValueError('unknown calibrated frame')
    bits=frame[5];length,pos=vdecode(frame,6)
    if pos+4>len(frame):raise ValueError('truncated frame')
    checksum=int.from_bytes(frame[pos:pos+4],'big')
    with policy(bits):data=m.decode_fixed_mix(frame[pos+4:],source_length=length)
    if zlib.crc32(data)!=checksum:raise ValueError('checksum mismatch')
    return data


def native_encoder():
    from benchmarks.native_contextual_mixer import encoder
    native=encoder('results/leaderboard/native_mixer_calibrated.so')
    def encode(data,bits):return MAGIC+native(data,bits)[5:]
    return encode
