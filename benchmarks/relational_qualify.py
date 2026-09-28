"""Independent Python qualification at real and counter-rescaling boundaries."""
import hashlib,json,random,time
from pathlib import Path
from benchmarks.relational_mixer import Native,encode,decode


def main():
    n=Native();r=random.Random(71277)
    cases=[b'',b'x',r.randbytes(255),bytes(range(256))*2,bytes(r.randrange(4) for _ in range(512)),b'abacabax'*80]
    rows=[]
    for data in cases:
        for bits in (0,2,4):
            for mode in range(4):
                blob=n.encode(data,bits,mode)
                assert encode(data,bits,mode)==blob
                assert decode(blob)==data and n.decode(blob)==data
                rows.append(dict(bytes=len(data),bits=bits,mode=mode,paired_encoders=True,paired_decoders=True))
    for name,data,mode in [('counter-rescale',b'\0'*17001,3),('successor-real',Path('benchmark-work/calgary/obj2').read_bytes()[:65536],1),('delta-boundary',bytes((i*i//11)&255 for i in range(66001)),2)]:
        start=time.perf_counter();blob=n.encode(data,2,mode);native_encode=time.perf_counter()-start
        start=time.perf_counter();assert n.decode(blob)==data;native_decode=time.perf_counter()-start
        start=time.perf_counter();assert decode(blob)==data;python_decode=time.perf_counter()-start
        # Reference encoder checks the complete payload too, including rescaling.
        start=time.perf_counter();assert encode(data,2,mode)==blob;python_encode=time.perf_counter()-start
        row=dict(case=name,bytes=len(data),mode=mode,size=len(blob),paired_encoders=True,paired_decoders=True,input_sha256=hashlib.sha256(data).hexdigest(),frame_sha256=hashlib.sha256(blob).hexdigest(),native_encode_seconds=native_encode,native_decode_seconds=native_decode,python_encode_seconds=python_encode,python_decode_seconds=python_decode)
        rows.append(row);print(json.dumps(row),flush=True)
    out=dict(complete=True,rows=rows,native_source_sha256=hashlib.sha256(Path('benchmarks/native_relational_mixer.cpp').read_bytes()).hexdigest())
    Path('results/leaderboard/relational-qualification.json').write_text(json.dumps(out,indent=2)+'\n')

if __name__=='__main__':main()
