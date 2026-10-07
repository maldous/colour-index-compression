"""Exploratory eight-MiB conditional LZ diagnostics, not full stream results."""
import hashlib
import json
from pathlib import Path
import time


def main():
    from benchmarks.fast_runtime import enable as fast
    from benchmarks.native_ppm import enable as ppm
    from benchmarks.native_ppm_estimates import enable as estimates
    from benchmarks.comb_cache import enable as cache
    fast(); ppm(); estimates(); cache()
    from cix.lz import _encode_parse, decode_lz_block
    from benchmarks.native_lz_parse import parser
    parse_lz=parser()
    from cix.multinomial import encode_best_block, EncodedBlock, MODE_LZ
    from cix.cli import config_for_level
    gate=json.loads(Path('docs/research/2026-09-28-long-window-tier1.json').read_text())
    assert gate['complete'] and gate['member_count']==29 and gate['fresh_decode']
    for item in json.loads(Path('results/silesia-manifest.json').read_text()):
        path=Path(item['path']);source=path.read_bytes()
        assert len(source)==item['size'] and hashlib.sha256(source).hexdigest()==item['sha256']
        offset=len(source)//2;data=source[offset:offset+16384]
        prefix=source[max(0,offset-8388608):offset]
        started=time.perf_counter();incumbent=encode_best_block(data,prefix_history=prefix[-1048576:],config=config_for_level(3))
        incumbent_seconds=time.perf_counter()-started
        rows=[]
        for window in (1048576,8388608):
            started=time.perf_counter()
            parsed=parse_lz(data,prefix_history=prefix,window=window,chain=32,min_match=4,lazy=True)
            payload,desc=_encode_parse(parsed,data,prefix,(),4,'window-probe')
            candidate=EncodedBlock(MODE_LZ,len(data),payload,desc)
            elapsed=time.perf_counter()-started
            assert decode_lz_block(payload,source_length=len(data),prefix_history=prefix)==data
            rows.append(dict(window=window,framed_size=len(candidate.framed),round_trip=True,
                             selected_size=min(len(candidate.framed),len(incumbent.framed)),seconds=elapsed))
        print(json.dumps(dict(file=path.name,input_sha256=item['sha256'],offset=offset,bytes_tested=len(data),
                              prefix_bytes=len(prefix),diagnostic_only=True,incumbent_size=len(incumbent.framed),
                              incumbent_mode=incumbent.description,incumbent_seconds=incumbent_seconds,rows=rows)),flush=True)


if __name__=='__main__':
    main()
