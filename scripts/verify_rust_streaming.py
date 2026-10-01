#!/usr/bin/env python3
"""Exercise early output, idle flush and backpressure over real Unix pipes."""
from __future__ import annotations
import hashlib, json, os, random, select, signal, subprocess, tempfile, threading, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CIX=ROOT/'dist/cix'; UNCIX=ROOT/'dist/uncix'; CAT=ROOT/'dist/cixcat'

def exact(fd:int,n:int,timeout:float)->bytes:
    out=bytearray(); deadline=time.monotonic()+timeout
    while len(out)<n:
        remaining=deadline-time.monotonic()
        if remaining<=0 or not select.select([fd],[],[],remaining)[0]:
            raise TimeoutError(f"wanted {n} bytes, got {len(out)}")
        b=os.read(fd,n-len(out))
        if not b: raise EOFError(f"wanted {n} bytes, pipe closed after {len(out)}")
        out.extend(b)
    return bytes(out)

def idle_flush()->dict:
    enc=subprocess.Popen([str(CIX),'--stream','--block-size','1MiB','--memory','1MiB','--threads','1','--flush-interval','100ms','--route','raw','-c','-'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,bufsize=0)
    dec=subprocess.Popen([str(UNCIX),'--stream','-c','-'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,bufsize=0)
    t=time.monotonic(); enc.stdin.write(b'first irregular fragment\0');enc.stdin.flush()
    header=exact(enc.stdout.fileno(),13,2)
    frame=exact(enc.stdout.fileno(),41,2); size=int.from_bytes(frame[5:9],'little'); payload=exact(enc.stdout.fileno(),size,2); first=time.monotonic()-t
    dec.stdin.write(header+frame+payload);dec.stdin.flush(); got1=exact(dec.stdout.fileno(),len(b'first irregular fragment\0'),2)
    assert dec.poll() is None, 'decoder must remain open until the terminal checksum arrives'
    enc.stdin.write(b'second chunk after an idle gap');enc.stdin.flush()
    frame2=exact(enc.stdout.fileno(),41,2);size2=int.from_bytes(frame2[5:9],'little');payload2=exact(enc.stdout.fileno(),size2,2)
    dec.stdin.write(frame2+payload2);dec.stdin.flush(); expected2=b'second chunk after an idle gap';got2=exact(dec.stdout.fileno(),len(expected2),2)
    enc.stdin.close(); footer=exact(enc.stdout.fileno(),41,2); assert footer[0]==255
    enc.stdout.close(); assert enc.wait(timeout=2)==0,enc.stderr.read()
    dec.stdin.write(footer);dec.stdin.close(); assert dec.wait(timeout=2)==0,dec.stderr.read();dec.stdout.close()
    assert got1==b'first irregular fragment\0' and got2==expected2
    return {'first_frame_before_encoder_eof':True,'first_decoded_bytes_before_footer':True,'idle_flush_interval_ms':100,'first_output_latency_seconds':first,'partial_chunks_exact':True}

def slow_consumer()->dict:
    rng=random.Random(3221); data=rng.randbytes(3*1024*1024)
    enc=subprocess.Popen([str(CIX),'--stream','--block-size','1MiB','--memory','1MiB','--threads','1','--route','raw','-c','-'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,bufsize=0)
    failure=[]
    def producer():
        try:
            for i in range(0,len(data),9973): enc.stdin.write(data[i:i+9973]);enc.stdin.flush()
            enc.stdin.close()
        except Exception as e: failure.append(repr(e))
    thread=threading.Thread(target=producer);thread.start();time.sleep(.2);thread.join(.05)
    blocked_before_drain=thread.is_alive()
    # The consumer intentionally waits, then drains in small increments.
    encoded=bytearray()
    while True:
        r,_,_=select.select([enc.stdout],[],[],5)
        if not r: raise TimeoutError('slow-consumer stream stalled')
        b=os.read(enc.stdout.fileno(),8192)
        if not b: break
        encoded.extend(b);time.sleep(.001)
    thread.join(5); assert blocked_before_drain and not thread.is_alive() and not failure,failure
    assert enc.wait(timeout=5)==0,enc.stderr.read()
    restored=subprocess.run([str(CAT),'-'],input=bytes(encoded),stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True).stdout
    assert restored==data
    return {'source_bytes':len(data),'archive_bytes':len(encoded),'source_sha256':hashlib.sha256(data).hexdigest(),'slow_consumer_exact':True,'consumer_delay_ms':200,'producer_blocked_until_consumer_drained':blocked_before_drain,'input_chunk_bytes':9973}

def main():
    empty=subprocess.run([str(CIX),'--stream','--memory','1MiB','-c','-'],input=b'',stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True).stdout
    assert len(empty)==54
    restored=subprocess.run([str(UNCIX),'--stream','-c','-'],input=empty,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True).stdout
    assert restored==b''
    conflict=subprocess.run([str(CIX),'--stream','--history','1KiB','--independent-blocks','-c','-'],input=b'x',stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    assert conflict.returncode!=0 and b'conflicts' in conflict.stderr
    with tempfile.TemporaryDirectory(prefix='cix-interrupt-') as td:
        target=Path(td)/'interrupted.cix'
        interrupted=subprocess.Popen([str(CIX),'--stream','--flush-interval','5s','--route','raw','-o',str(target),'-'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,bufsize=0)
        interrupted.stdin.write(b'partial data before interrupt');interrupted.stdin.flush();time.sleep(.1);interrupted.send_signal(signal.SIGINT)
        assert interrupted.wait(timeout=3)!=0
        assert not target.exists() and not list(Path(td).glob('*.cix-tmp-*'))
        interrupted_stderr=interrupted.stderr.read().decode(errors='replace')
        assert 'interrupted' in interrupted_stderr
    result={'scope':'pipe correctness and latency only; no compression performance inference','empty_stream_exact':True,'contradictory_history_mode_rejected':True,'sigint_nonzero_and_temp_cleanup':True,'idle_flush':idle_flush(),'slow_consumer':slow_consumer()}
    path=ROOT/'docs/research/2026-10-01-rust-native/streaming-verification.json';path.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
