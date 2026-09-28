"""Diagnostic BWT block-size tournament; full members, not a leaderboard codec."""
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
    from cix.bwt import encode_bwt_block, decode_bwt_block
    from cix.multinomial import EncodedBlock, MODE_BWT, MODE_RAW
    for label in ('canterbury/alice29.txt','canterbury/kennedy.xls','calgary/book1','calgary/obj2'):
        data = (Path('benchmark-work')/label).read_bytes()
        for block_size in (65536,262144):
            total = 0; selected_modes = []; started = time.perf_counter()
            for offset in range(0,len(data),block_size):
                block = data[offset:offset+block_size]
                payload, description = encode_bwt_block(block)
                assert decode_bwt_block(payload,source_length=len(block))==block
                encoded = EncodedBlock(MODE_BWT,len(block),payload,description)
                raw = EncodedBlock(MODE_RAW,len(block),block,'raw')
                selected = min((raw,encoded),key=lambda value:len(value.framed))
                total += len(selected.framed);selected_modes.append(selected.description)
            print(json.dumps(dict(file=label,original=len(data),input_sha256=hashlib.sha256(data).hexdigest(),
                                  block_size=block_size,framed_block_bytes=total,round_trip=True,
                                  diagnostic_only=True,excludes_stream_header=True,seconds=time.perf_counter()-started,
                                  modes=selected_modes)),flush=True)


if __name__ == '__main__':
    main()
