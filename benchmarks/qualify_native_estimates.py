"""Require exact IEEE float equality for accelerated PPM estimates."""
import json
import random
import time
from benchmarks.native_ppm_estimates import load
from cix import ppm


def main():
    fixed, portfolio = load()
    rng = random.Random(77122)
    count = 0
    start = time.perf_counter()
    for order in range(9):
        for alphabet in (1, 7, 256):
            data = bytes(rng.randrange(alphabet) for _ in range(4097))
            prefix = bytes(rng.randrange(alphabet) for _ in range(5000))
            for history in (b'', prefix):
                for limit in (0, 137, 8192):
                    options = dict(max_order=order, prefix_history=history, sample_limit=limit)
                    for method in range(4):
                        for update in (False, True):
                            extra = dict(escape_method=method, update_exclusion=update)
                            actual = fixed(data, **options, **extra)
                            expected = ppm.estimate_ppm_bits(data, **options, **extra)
                            assert actual.hex() == expected.hex(), (order, alphabet, len(history), limit,
                                method, update, actual.hex(), expected.hex())
                            count += 1
                    if limit:
                        actual = portfolio(data, **options)
                        expected = ppm.estimate_ppm_portfolio_bits(data, **options)
                        assert actual.hex() == expected.hex(), ('portfolio', order, alphabet,
                            len(history), limit, actual.hex(), expected.hex())
                        count += 1
        print(json.dumps(dict(order=order, exact_float_cases=count,
                              seconds=time.perf_counter()-start)), flush=True)
    print('COMPLETE', count, flush=True)


if __name__ == '__main__':
    main()
