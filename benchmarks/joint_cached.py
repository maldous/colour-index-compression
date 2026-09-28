"""Trusted local result-cache acceleration for the unchanged CIXT1 policy."""
import hashlib
import zlib
from pathlib import Path
from cix.multinomial import vdecode,vencode
from benchmarks import joint_bounded as joint
from benchmarks import ppm_bounded as ppm
from benchmarks.mixer_rounded_bounded import encode as encode_mixer
from benchmarks.local_compare import source_digest


def encode_cached(data,frame,record):
    root=Path(__file__).resolve().parents[1]
    identity=record['identity'];policy=identity['policy']
    def digest(path):return hashlib.sha256((root/path).read_bytes()).hexdigest()
    expected=dict(block_size=joint.BLOCK_SIZE,orders=list(joint.ORDERS),history=65536,
                  core_sha256=source_digest(root),encoder_sha256=digest('benchmarks/ppm_bounded.py'),
                  native_source_sha256=digest('benchmarks/native_ppm.cpp'),
                  native_wrapper_sha256=digest('benchmarks/native_ppm.py'),
                  native_binary_sha256=digest('results/leaderboard/native_ppm.so'))
    if (policy!=expected or not record['round_trip'] or record['size']!=len(frame)
        or record['frame_sha256']!=hashlib.sha256(frame).hexdigest()
        or identity['original']!=len(data) or identity['input_sha256']!=hashlib.sha256(data).hexdigest()):
        raise ValueError('cached PPM identity, policy or artifact mismatch')
    if frame[:5]!=ppm.MAGIC:raise ValueError('wrong cached frame version')
    length,pos=vdecode(frame,5);block_size,pos=vdecode(frame,pos)
    if length!=len(data) or block_size!=joint.BLOCK_SIZE or pos+4>len(frame):raise ValueError('cached header mismatch')
    if int.from_bytes(frame[pos:pos+4],'big')!=zlib.crc32(data):raise ValueError('cached checksum mismatch')
    pos+=4;out=bytearray(joint.MAGIC+frame[5:pos])
    for offset in range(0,len(data),block_size):
        block=data[offset:offset+block_size];size,pos=vdecode(frame,pos)
        if not 1<=size<=len(block)+1 or pos+size>len(frame):raise ValueError('bad cached record size')
        best=frame[pos:pos+size];pos+=size
        if best[0] not in (0,1):raise ValueError('bad cached record mode')
        candidate=b'\x02'+encode_mixer(block)
        if len(candidate)<len(best):best=candidate
        out.extend(vencode(len(best)));out.extend(best)
    if pos!=len(frame):raise ValueError('cached trailing bytes')
    return bytes(out)
