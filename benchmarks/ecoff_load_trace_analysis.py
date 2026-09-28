"""Unscored loss attribution for symbol-constrained Alpha load displacements.

The original PAQ probabilities are kept on ambiguous branches. Only decisions
forced by the candidate prefix trie are removed. Candidate delivery, membership,
and framing are excluded: this is neither a physical result nor an upper bound
on every possible conditional model.
"""
import array
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
from benchmarks import ecoff_symbol_loads as codec, ecoff_call_trace_analysis as mapping


def analyze(folder):
    folder = Path(folder); proof = json.loads((folder/'complete.json').read_text())
    if not proof['round_trip'] or not proof['trace_equals_reference']:
        raise ValueError('unqualified PAQ trace')
    data = (folder/'source.bin').read_bytes(); raw = (folder/'predictions.u32').read_bytes()
    sha = lambda value: hashlib.sha256(value).hexdigest()
    if sha(data) != proof['input_sha256'] or sha(raw) != proof['trace_sha256']:
        raise ValueError('trace/input hash mismatch')
    records = array.array('I'); records.frombytes(raw)
    if sys.byteorder != 'little': records.byteswap()
    stream = mapping.outcome_bytes(records); locations = []
    for off, obj, sec, _ in codec.symbols.objects(data):
        if b'.text' not in sec: continue
        start, size = sec[b'.text']; size += sec.get(b'.init', (0, 0))[1] + sec.get(b'.fini', (0, 0))[1]
        transformed = mapping.shuffled_code(obj[start:start+size]); found = stream.find(transformed)
        if found < 0 or stream.find(transformed, found+1) >= 0:
            raise ValueError('code not uniquely mapped into qualified trace')
        locations.append((off+start, size, found))
    stats = dict(eligible=0, matched=0, exceptions=0, paq_bits_all=0., paq_bits_matched=0.,
                 forced_bits=0, forced_paq_bits=0., remaining_paq_bits=0.)
    tries = {}
    for where, candidates, _ in codec.fields(data, 1):
        maps = [(start, found) for start, size, found in locations if start <= where < start+size]
        if len(maps) != 1: raise ValueError('load location ambiguous')
        start, found = maps[0]; event = (found+where-start)*8+16
        events = records[event:event+16]; actual = struct.unpack_from('<H', data, where)[0]
        stats['eligible'] += 1; losses = []
        for bit, record in zip(range(15, -1, -1), events):
            p, y = record & 0x7fffffff, record >> 31
            if y != (actual >> bit) & 1: raise ValueError('load trace bit mismatch')
            losses.append(-math.log2((p if y else (1<<31)-p)/(1<<31)))
        stats['paq_bits_all'] += sum(losses)
        if actual not in candidates:
            stats['exceptions'] += 1; continue
        stats['matched'] += 1; stats['paq_bits_matched'] += sum(losses)
        if id(candidates) not in tries:
            trie = {}
            for value in candidates:
                for bit in range(15, -1, -1):
                    key = (bit, value >> (bit+1)); trie[key] = trie.get(key, 0) | (1 << ((value>>bit)&1))
            tries[id(candidates)] = trie
        trie = tries[id(candidates)]
        for bit, loss in zip(range(15, -1, -1), losses):
            if trie[(bit, actual >> (bit+1))] != 3:
                stats['forced_bits'] += 1; stats['forced_paq_bits'] += loss
            else: stats['remaining_paq_bits'] += loss
    return dict(diagnostic_only=True, physical_codec=False, qualified_trace=proof,
                note=__doc__, source_hashes={str(Path(p)): sha(Path(p).read_bytes()) for p in [__file__,codec.__file__,mapping.__file__]},
                matched_code_regions=locations, measurements=stats)


if __name__ == '__main__':
    result = analyze(sys.argv[1]); Path(sys.argv[2]).write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result['measurements'], indent=2))
