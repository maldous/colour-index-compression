"""Experimental reversible context-conditioned fixed-point mixer framing."""
from contextlib import contextmanager
import zlib
from cix import fixedmix
from cix.multinomial import vencode,vdecode

MAGIC=b'CIXQ\x01'
BASE_STATE=fixedmix._State


@contextmanager
def state_policy(bits):
    if bits not in (0,2,4):raise ValueError('unsupported context width')
    class State(BASE_STATE):
        def __init__(self,eta_shift):
            super().__init__(eta_shift)
            self.initial_weights=[row[:] for row in self.weights]
            self.banks={0:(self.weights,self.bias)}
        def probabilities(self,bit_position,prefix_bits):
            context=(self.history[-1]&((1<<bits)-1)) if self.history else 0
            if context not in self.banks:
                self.banks[context]=([row[:] for row in self.initial_weights],[0]*8)
            self.weights,self.bias=self.banks[context]
            return super().probabilities(bit_position,prefix_bits)
    previous=fixedmix._State
    fixedmix._State=State
    try:yield
    finally:fixedmix._State=previous


def encode(data,bits):
    with state_policy(bits):
        payload=fixedmix.encode_fixed_mix(data,eta_shift=6)
    return MAGIC+bytes([bits])+vencode(len(data))+zlib.crc32(data).to_bytes(4,'big')+payload


def decode(frame):
    if frame[:5]!=MAGIC or len(frame)<11:raise ValueError('bad mixer frame')
    bits=frame[5];length,pos=vdecode(frame,6)
    if pos+4>len(frame):raise ValueError('truncated mixer frame')
    checksum=int.from_bytes(frame[pos:pos+4],'big')
    with state_policy(bits):
        data=fixedmix.decode_fixed_mix(frame[pos+4:],source_length=length)
    if zlib.crc32(data)!=checksum:raise ValueError('mixer checksum mismatch')
    return data


def main():
    import hashlib,json,random,time
    from pathlib import Path
    from benchmarks.native_ppm import enable
    enable()
    from benchmarks.ppm_bounded import encode as bounded,decode as unbounded
    rng=random.Random(72901)
    cases=[('random',rng.randbytes(4096)),('biased',bytes(rng.randrange(4) for _ in range(4096))),
           ('periodic',bytes(range(37))*110),('switching',b''.join(bytes(rng.randrange(k) for _ in range(512)) for k in (2,16,4,256,2,16,4,256)))]
    for label in ('canterbury/alice29.txt','canterbury/kennedy.xls','calgary/obj2'):
        cases.append((label,(Path('benchmark-work')/label).read_bytes()[:4096]))
    for name,data in cases:
        rows=[]
        for bits in (0,2,4):
            start=time.perf_counter();blob=encode(data,bits);seconds=time.perf_counter()-start
            assert decode(blob)==data
            rows.append(dict(context_bits=bits,size=len(blob),encode_seconds=seconds,round_trip=True))
        blob=bounded(data);assert unbounded(blob)==data
        print(json.dumps(dict(case=name,bytes_tested=len(data),input_sha256=hashlib.sha256(data).hexdigest(),
                              diagnostic_only=True,bounded_ppm_size=len(blob),rows=rows)),flush=True)


if __name__=='__main__':main()
