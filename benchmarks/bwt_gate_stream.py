"""Experimental exact BWT token-PPM portfolio; leaves canonical codec and decoder unchanged."""
import argparse
import hashlib
import json
from pathlib import Path
import time


def enable():
    from cix import bwt
    from cix.ppm import encode_ppm
    def materialize(primary, mtf):
        tokens, sides = bwt._runa_runb_tokens(mtf)
        if len(tokens) < 32:
            return None
        candidates = []
        for order in range(5):
            payload = encode_ppm(tokens, max_order=order)
            candidates.append(bwt._pack_runa_runb(6, primary, tokens, sides, b'\x01'+payload))
        return min(candidates, key=len)
    bwt._encode_bwt_v6 = materialize


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    from benchmarks.fast_runtime import enable as fast
    from benchmarks.native_ppm import enable as ppm
    from benchmarks.native_ppm_estimates import enable as estimates
    from benchmarks.comb_cache import enable as cache
    fast(); ppm(); estimates(); cache(); enable()
    from cix.multinomial import StreamEncoder, decompress
    from cix.cli import config_for_level
    from benchmarks.local_compare import source_digest
    out = Path(args.output); out.mkdir(parents=True, exist_ok=True)
    policy = dict(core_sha256=source_digest(Path.cwd()),
                  experiment_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  level=3, bwt_ppm_orders=list(range(5)), minimum_tokens=32)
    for item in json.loads(Path(args.manifest).read_text()):
        path = Path(item['path']); name = item['corpus']+'-'+path.name
        data = path.read_bytes()
        assert len(data)==item['size'] and hashlib.sha256(data).hexdigest()==item['sha256']
        baseline_path = Path('results/leaderboard/tier1')/(name+'.json')
        baseline = json.loads(baseline_path.read_text())
        old = baseline_path.with_suffix('.cixm').read_bytes()
        assert baseline['round_trip'] and hashlib.sha256(old).hexdigest()==baseline['compressed_sha256']
        assert baseline['identity']['source_tree_sha256']==policy['core_sha256']
        started = time.perf_counter(); encoder = StreamEncoder(config_for_level(3))
        chunks = [encoder.feed(data[i:i+65536]) for i in range(0,len(data),65536)]
        chunks.append(encoder.finish()); blob = b''.join(chunks)
        encode_seconds = time.perf_counter()-started
        started = time.perf_counter()
        assert decompress(blob)==data and decompress(old)==data
        selected = blob if len(blob)<len(old) else old
        (out/(name+'.cixm')).write_bytes(blob)
        result = dict(file=path.name, corpus=item['corpus'], original=len(data), input_sha256=item['sha256'],
                      policy=policy, size=len(blob), baseline_size=len(old), selected_size=len(selected),
                      round_trip=True, compressed_sha256=hashlib.sha256(blob).hexdigest(),
                      encode_seconds=encode_seconds, decode_seconds=time.perf_counter()-started)
        (out/(name+'.json')).write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result),flush=True)


if __name__ == '__main__':
    main()
