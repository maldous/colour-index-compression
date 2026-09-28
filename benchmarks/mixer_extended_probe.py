"""Paired complete-frame extended-context diagnostic on fixed 64 KiB prefixes."""
import hashlib,json,time
from pathlib import Path


def main():
    from benchmarks.extended_mixer import encode,decode,native_encoder
    native=native_encoder()
    controls=[json.loads(s) for s in Path('results/leaderboard/contextual-mixer-scale.jsonl').read_text().splitlines()]
    for control in controls:
        data=(Path('benchmark-work')/control['case']).read_bytes()[:65536]
        assert hashlib.sha256(data).hexdigest()==control['input_sha256']
        rows=[]
        for bits in (0,2):
            start=time.perf_counter();frame=native(data,bits);native_seconds=time.perf_counter()-start
            reference=encode(data,bits)
            assert frame==reference and decode(frame)==data
            rows.append(dict(context_bits=bits,size=len(frame),native_seconds=native_seconds,byte_identical=True,round_trip=True))
        print(json.dumps(dict(case=control['case'],input_sha256=control['input_sha256'],bytes_tested=len(data),
                              diagnostic_only=True,control=control,rows=rows)),flush=True)


if __name__=='__main__':main()
