"""Unscored PAQ loss attribution for function-constrained Alpha call targets.

Map complete transformed code bytes into a probability trace qualified against
unmodified PAQ. Candidate tables and membership are assumed known here. The
reported savings exclude their delivery cost and are NOT a physical codec.
"""
import array
import hashlib
import json
import math
import struct
import sys
from pathlib import Path
from benchmarks import ecoff_call_entries as codec


def shuffled_code(data):
    out = bytearray()
    for word, (inst,) in enumerate(struct.iter_unpack('<I', data)):
        op = inst >> 26
        if inst >> 21 == codec.CALL:
            inst = (inst & ~codec.MASK) | ((inst + word) & codec.MASK)
        if op in (0x14, 0x15, 0x16, 0x17):
            inst = (inst & 0xfc000000) | ((inst & 0xffe0) << 10) | ((inst >> 11) & 0x7fe0) | (inst & 31)
        elif op == 0x18:
            inst = (inst & 0xfc000000) | ((inst & 0xffff) << 10) | ((inst >> 16) & 0x3ff)
        elif op in (0x10, 0x11, 0x12, 0x13, 0x1c):
            inst = (inst & 0xfc000000) | ((inst << 13) & 0x3fc0000) | ((inst >> 8) & 0x3ffe0) | (inst & 31)
        out.extend(inst.to_bytes(4, 'big'))
    return bytes(out)


def outcome_bytes(events):
    if len(events) % 8:
        raise ValueError('trace is not byte aligned')
    return bytes(sum(((events[i+j] >> 31) & 1) << (7-j) for j in range(8)) for i in range(0, len(events), 8))


def constrained_loss(events, candidates, actual):
    """Original PAQ predictions, eliminating forced trie branches only."""
    remaining = list(candidates); forced_bits = 0; total = 0.0; removed = 0.0
    if actual not in remaining:
        raise ValueError('actual target outside candidate set')
    for bit, record in zip(range(20, -1, -1), events):
        p, y = record & 0x7fffffff, record >> 31
        if y != (actual >> bit) & 1:
            raise ValueError('trace target mismatch')
        probability = (p if y else (1 << 31)-p) / (1 << 31)
        loss = -math.log2(probability); total += loss
        possible = {v >> bit & 1 for v in remaining}
        if len(possible) == 1:
            forced_bits += 1; removed += loss
        remaining = [v for v in remaining if (v >> bit & 1) == y]
    assert len(remaining) == 1
    return dict(paq_bits=total, forced_bits=forced_bits, forced_paq_bits=removed,
                remaining_paq_bits=total-removed)


def analyze(folder):
    folder = Path(folder); proof = json.loads((folder/'complete.json').read_text())
    if not proof['round_trip'] or not proof['trace_equals_reference']:
        raise ValueError('unqualified trace')
    data = (folder/'source.bin').read_bytes(); raw = (folder/'predictions.u32').read_bytes()
    sha = lambda b: hashlib.sha256(b).hexdigest()
    if sha(data) != proof['input_sha256'] or sha(raw) != proof['trace_sha256']:
        raise ValueError('trace/input provenance changed')
    records = array.array('I'); records.frombytes(raw)
    if sys.byteorder != 'little': records.byteswap()
    stream = outcome_bytes(records); objects = codec.parent.objects(data)
    headers = {}
    for off, d, sec, symbols in objects:
        start, length = sec[b'.text']; length += sec[b'.init'][1] + sec[b'.fini'][1]
        count = struct.unpack_from('<H', d, 2)[0]
        virtual = next(struct.unpack_from('<Q', d, 104+i*64+16)[0]
                       for i in range(count) if d[104+i*64:104+i*64+8].rstrip(b'\0') == b'.text')
        headers[off+start] = (virtual, length)
    rows = []
    for functions, calls in codec.groups(data):
        start = calls[0][0]-calls[0][1]*4; virtual, length = headers[start]
        transformed = shuffled_code(data[start:start+length]); found = stream.find(transformed)
        if found < 0 or stream.find(transformed, found+1) >= 0:
            raise ValueError('complete code region not uniquely attributable in trace')
        candidates = sorted({((v-virtual)//4-1) & codec.MASK for v in functions})
        stats = dict(calls=len(calls), candidate_addresses=len(candidates), matched=0,
                     paq_bits=0.0, forced_bits=0, forced_paq_bits=0.0, remaining_paq_bits=0.0,
                     code_bytes=length, trace_byte_offset=found)
        for where, word, pc in calls:
            inst = struct.unpack_from('<I', data, where)[0]; actual = ((inst & codec.MASK)+word) & codec.MASK
            if actual not in candidates:
                continue
            stats['matched'] += 1
            event = (found+word*4)*8+11
            for key, value in constrained_loss(records[event:event+21], candidates, actual).items(): stats[key] += value
        stats['forced_zero_metadata_bytes'] = stats['forced_paq_bits']/8
        rows.append(stats)
    result = dict(diagnostic_only=True, physical_codec=False, note='Optimistic savings before candidate-table delivery, membership and framing costs; PAQ probabilities unchanged on unforced decisions.',
                  qualified_trace=proof, analysis_sha256=sha(Path(__file__).read_bytes()), rows=rows)
    (folder/'constraint-analysis.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    analyze(sys.argv[1])
