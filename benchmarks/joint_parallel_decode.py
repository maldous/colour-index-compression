"""Standalone dependency-aware parallel decoding; never reads original input.

Self-contained mixer blocks run independently. A PPM block is released only after
its preceding decoded bytes exist. Thus parallel verification uses no oracle data.
"""
from concurrent.futures import ProcessPoolExecutor,wait,FIRST_COMPLETED
import zlib
from cix.multinomial import vdecode
from benchmarks.joint_bounded import MAGIC,MAX_BLOCK_SIZE


def init():
    from benchmarks.legacy_mixer_native import enable
    enable()


def block_task(mode,payload,expected,history):
    if mode==1:
        from cix.ppm import decode_ppm
        block=decode_ppm(payload,source_length=expected,prefix_history=history)
    elif mode==2:
        from benchmarks.mixer_rounded_bounded import decode
        block=decode(payload)
    else:raise ValueError('invalid block mode')
    if len(block)!=expected:raise ValueError('block length mismatch')
    return block


def decode(frame,jobs=4):
    if frame[:5]!=MAGIC:raise ValueError('unknown joint frame')
    length,pos=vdecode(frame,5);size,pos=vdecode(frame,pos)
    if not 65536<=size<=MAX_BLOCK_SIZE or pos+4>len(frame):raise ValueError('parallel decoder requires block >=64 KiB')
    checksum=int.from_bytes(frame[pos:pos+4],'big');pos+=4
    blocks=[];decoded={}
    for offset in range(0,length,size):
        expected=min(size,length-offset);n,pos=vdecode(frame,pos)
        if not 1<=n<=expected+1 or pos+n>len(frame):raise ValueError('invalid block framing')
        mode=frame[pos];payload=frame[pos+1:pos+n];pos+=n
        if mode==0:
            if len(payload)!=expected:raise ValueError('invalid raw size')
            decoded[len(blocks)]=payload
        elif mode not in (1,2):raise ValueError('invalid mode')
        blocks.append((mode,payload,expected))
    if pos!=len(frame):raise ValueError('trailing bytes')
    pending=set(range(len(blocks)))-decoded.keys();running={}
    with ProcessPoolExecutor(jobs,initializer=init) as pool:
        while pending or running:
            for i in sorted(pending):
                if len(running)>=jobs:break
                mode,payload,expected=blocks[i]
                if mode==1 and i and i-1 not in decoded:continue
                history=decoded[i-1][-65536:] if mode==1 and i else b''
                running[pool.submit(block_task,mode,payload,expected,history)]=i
                pending.remove(i)
            if not running:raise ValueError('decoder dependency deadlock')
            done,_=wait(running,return_when=FIRST_COMPLETED)
            for future in done:decoded[running.pop(future)]=future.result()
    result=b''.join(decoded[i] for i in range(len(blocks)))
    if len(result)!=length or zlib.crc32(result)!=checksum:raise ValueError('length or checksum mismatch')
    return result
