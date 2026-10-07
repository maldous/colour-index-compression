"""Larger conditional-free prefix streams for the generic mixer diagnostic."""
import hashlib,json,time
from pathlib import Path


def main():
    from benchmarks.fast_runtime import enable as fast
    from benchmarks.native_ppm import enable as ppm
    from benchmarks.native_ppm_estimates import enable as estimates
    from benchmarks.comb_cache import enable as cache
    fast();ppm();estimates();cache()
    from benchmarks.contextual_mixer import encode,decode
    from benchmarks.ppm_bounded import encode as ppm_encode,decode as ppm_decode
    from cix.multinomial import compress,decompress
    from cix.cli import config_for_level
    for label in ('canterbury/alice29.txt','canterbury/kennedy.xls','calgary/obj2'):
        data=(Path('benchmark-work')/label).read_bytes()[:65536]
        rows=[]
        for bits in (0,2):
            started=time.perf_counter();blob=encode(data,bits);elapsed=time.perf_counter()-started
            assert decode(blob)==data
            rows.append(dict(context_bits=bits,size=len(blob),encode_seconds=elapsed,round_trip=True))
        blob=ppm_encode(data);assert ppm_decode(blob)==data;ppm_size=len(blob)
        blob=compress(data,config_for_level(3));assert decompress(blob)==data
        print(json.dumps(dict(case=label,bytes_tested=len(data),input_sha256=hashlib.sha256(data).hexdigest(),
                              diagnostic_only=True,cix_size=len(blob),bounded_ppm_size=ppm_size,rows=rows)),flush=True)


if __name__=='__main__':main()
