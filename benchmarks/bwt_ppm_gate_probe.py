"""Measure whether BWT token PPM estimation suppresses smaller real outputs."""
import json
from pathlib import Path
import time


def main():
    from benchmarks.fast_runtime import enable as fast
    from benchmarks.native_ppm import enable as ppm
    from benchmarks.native_ppm_estimates import enable as estimates
    from benchmarks.comb_cache import enable as cache
    fast(); ppm(); estimates(); cache()
    from cix.bwt import (bwt_transform, mtf_encode, _runa_runb_tokens,
                         _pack_runa_runb, encode_bwt_block, decode_bwt_block)
    from cix.ppm import encode_ppm
    for label in ('canterbury/alice29.txt','canterbury/kennedy.xls','calgary/book1','calgary/obj2'):
        data = (Path('benchmark-work')/label).read_bytes()[:262144]
        primary, transformed = bwt_transform(data)
        tokens, sides = _runa_runb_tokens(mtf_encode(transformed))
        incumbent, description = encode_bwt_block(data)
        assert decode_bwt_block(incumbent,source_length=len(data))==data
        rows = []
        for order in range(5):
            start = time.perf_counter()
            payload = encode_ppm(tokens,max_order=order)
            blob = _pack_runa_runb(6,primary,tokens,sides,b'\x01'+payload)
            assert decode_bwt_block(blob,source_length=len(data))==data
            rows.append(dict(order=order,size=len(blob),round_trip=True,seconds=time.perf_counter()-start))
        print(json.dumps(dict(file=label,bytes_tested=len(data),diagnostic_only=True,
                              incumbent_size=len(incumbent),incumbent_mode=description,rows=rows)),flush=True)


if __name__ == '__main__':
    main()
