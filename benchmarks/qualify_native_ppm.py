"""Byte-exact native/Python PPM qualification; run after compiling the library."""
import json
import random
import time
from cix import ppm
from benchmarks.native_ppm import load


def main():
    variant, encode = load()
    rng = random.Random(49283)
    cases = [b'', b'x', b'ab' * 20, bytes(range(256)), rng.randbytes(2048),
             bytes(rng.randrange(8) for _ in range(2048)), b'x' * 17000]
    count = 0
    start = time.perf_counter()
    for data in cases:
        for order in (0, 1, 3, 8):
            for prefix in (b'', bytes(range(256)) * 20):
                for update in (False, True):
                    options = dict(max_order=order, prefix_history=prefix,
                                   update_exclusion=update)
                    for method in range(5):
                        if method < 4:
                            reference = ppm._encode_ppm_method(data, escape_method=method, **options)
                        else:
                            reference = ppm._encode_ppm_see(data, **options)
                        got = variant(data, escape_method=method if method < 4 else 0,
                                      secondary_escape=method == 4, **options)
                        assert reference == got, (len(data), order, len(prefix), update, method)
                        assert ppm.decode_ppm(got, source_length=len(data), prefix_history=prefix) == data
                        count += 1
                assert encode(data, max_order=order, prefix_history=prefix) == ppm.encode_ppm(
                    data, max_order=order, prefix_history=prefix)
                print(json.dumps(dict(verified_variants=count, length=len(data), order=order,
                                      prefix=len(prefix), seconds=time.perf_counter()-start)), flush=True)
    print('COMPLETE', count, flush=True)


if __name__ == '__main__':
    main()
