"""Diagnostic generic LZ window test, never a full-member leaderboard score."""
import hashlib
import json
from pathlib import Path
import random
import time


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--whole-block-portfolio", action="store_true")
    args = parser.parse_args()
    from benchmarks.fast_runtime import enable
    enable()
    from benchmarks.native_ppm import enable
    enable()
    from benchmarks.native_ppm_estimates import enable
    enable()
    from benchmarks.comb_cache import enable
    enable()
    from cix.lz import parse_lz, _encode_parse, decode_lz_block, encode_lz_block
    rng = random.Random(78217)
    history = rng.randbytes(786432)
    cases = [('generated-distant-repeat', history[:16384], history)]
    for label in ('canterbury/kennedy.xls', 'calgary/book1', 'calgary/obj2'):
        source = (Path('benchmark-work') / label).read_bytes()
        offset = min(len(source) // 2, 524288)
        cases.append((label + '-middle-probe', source[offset:offset + 16384], source[max(0, offset-1048576):offset]))
    for name, data, prefix in cases:
        rows = []
        for window in (131072, 1048576):
            start = time.perf_counter()
            parse = parse_lz(data, prefix_history=prefix, window=window, chain=32, min_match=4, lazy=True)
            blob, description = _encode_parse(parse, data, prefix, (), 4, 'generic-window-probe')
            elapsed = time.perf_counter() - start
            assert decode_lz_block(blob, source_length=len(data), prefix_history=prefix) == data
            rows.append(dict(window=window, parser='hash-chain', size=len(blob), encode_seconds=elapsed,
                             round_trip=True, sha256=hashlib.sha256(blob).hexdigest()))
        start = time.perf_counter()
        blob, _ = encode_lz_block(data, prefix_history=prefix, window=1048576, chain=24)
        elapsed = time.perf_counter() - start
        assert decode_lz_block(blob, source_length=len(data), prefix_history=prefix) == data
        rows.append(dict(window=131072, parser='incumbent-suffix-array', size=len(blob),
                         encode_seconds=elapsed, round_trip=True, sha256=hashlib.sha256(blob).hexdigest()))
        if args.whole_block_portfolio:
            from cix.multinomial import encode_best_block, EncodedBlock, MODE_LZ
            from cix.cli import config_for_level
            start = time.perf_counter()
            incumbent = encode_best_block(data, prefix_history=prefix, config=config_for_level(3))
            parsed = parse_lz(data, prefix_history=prefix, window=1048576, chain=32, min_match=4, lazy=True)
            payload, _ = _encode_parse(parsed, data, prefix, (), 4, "generic-window-probe")
            assert decode_lz_block(payload, source_length=len(data), prefix_history=prefix) == data
            candidate = EncodedBlock(MODE_LZ, len(data), payload, "long-window")
            rows.append(dict(parser="whole-block-portfolio", incumbent_mode=incumbent.description, incumbent_framed=len(incumbent.framed), candidate_framed=len(candidate.framed), selected_framed=min(len(incumbent.framed), len(candidate.framed)), seconds=time.perf_counter()-start))
        print(json.dumps(dict(case=name, original=len(data), prefix_bytes=len(prefix),
                              diagnostic_only=True, rows=rows)), flush=True)


if __name__ == '__main__':
    main()
