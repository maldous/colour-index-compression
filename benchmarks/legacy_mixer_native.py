"""Opt-in Q2/Q3/Q5 acceleration, isolated from existing running experiments."""
import zlib
from cix.multinomial import vdecode
from benchmarks.relational_mixer import Native

class LegacyNative(Native):
    def __init__(self):
        super().__init__('results/leaderboard/native_legacy_mixer.so')
    def decode(self, blob):
        if len(blob)<11 or blob[:4]!=b'CIXQ' or blob[4] not in (2,3,5):
            raise ValueError('unsupported legacy mixer')
        bits=blob[5]
        if bits not in (0,2,4):raise ValueError('invalid bank width')
        mode={2:16,3:17,5:0}[blob[4]]
        length,pos=vdecode(blob,6)
        if length>1<<30 or pos+4>len(blob):raise ValueError('invalid length')
        checksum=int.from_bytes(blob[pos:pos+4],'big');payload=blob[pos+4:]
        data=self.call(self.lib.cix_relation_decode,payload,len(payload),length,bits,mode)
        if len(data)!=length or zlib.crc32(data)!=checksum:raise ValueError('checksum mismatch')
        return data
    def payload(self,data,bits,version):
        return self.call(self.lib.cix_relation_encode,data,len(data),bits,{2:16,3:17,5:0}[version])


def enable():
    # Process-local opt-in only; source and binaries of live runs stay untouched.
    from benchmarks import mixer_rounded_bounded, mixer_ppm_bounded, mixer_ppm_large
    from benchmarks import rounded_mixer, extended_mixer, ppm_expert_mixer
    native=LegacyNative()
    for module in (mixer_rounded_bounded,mixer_ppm_bounded,mixer_ppm_large):
        module.decode_mixer=native.decode
    for module in (rounded_mixer,extended_mixer,ppm_expert_mixer):
        module.decode=native.decode
    return native
