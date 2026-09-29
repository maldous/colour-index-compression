#!/usr/bin/env python3
"""Synthetic scaling corpus v1. Fixed bytes, no corpus-trained generator.

All streams use 1 MiB construction blocks. SHAKE256(domain || seed || index)
provides deterministic independent pseudo-random blocks; no Python random state,
platform endianness, current time, filenames or external dictionaries are used.
The public generator seed is never supplied to any compressor/decompressor.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

VERSION = 'cix-evidence-synthetic-v1'
SEED = bytes.fromhex('f7b14cac799cf8423cdaef250c1345bb3061660925a526669731af3dab57199e')
BLOCK = 1 << 20
CLASSES = ['high_entropy', 'sequential_bytes', 'incrementing_u64', 'periodic',
           'low_entropy_ascii', 'grammar_ascii', 'csv_records', 'json_logs',
           'mutated_records', 'sparse_binary', 'delta_timeseries', 'mixed_entropy',
           'heterogeneous']
WORDS = ('the a this that each some our their small large quiet bright old new '
         'river forest road field house engine window signal system record '
         'moves meets carries follows changes reads writes waits returns '
         'near across under beside after before while because and but').split()


def random_bytes(domain, index, size=BLOCK):
    key = VERSION.encode() + b'\0' + domain.encode() + b'\0' + SEED + struct.pack('<Q', index)
    return hashlib.shake_256(key).digest(size)


def block(kind, index):
    if kind == 'high_entropy':
        return random_bytes(kind, index)
    if kind == 'sequential_bytes':
        return bytes(range(256)) * (BLOCK // 256)
    if kind == 'incrementing_u64':
        start = index * (BLOCK // 8)
        return b''.join(struct.pack('<Q', value) for value in range(start, start + BLOCK // 8))
    if kind == 'periodic':
        pattern = bytes((i * 73 + i // 5) % 256 for i in range(4093))
        offset = index * BLOCK % len(pattern)
        return (pattern * ((BLOCK + offset) // len(pattern) + 1))[offset:offset + BLOCK]
    if kind == 'low_entropy_ascii':
        table = bytes(ord('a') if x < 240 else ord(' ') if x < 252 else ord('\n') for x in range(256))
        return random_bytes(kind, index).translate(table)
    if kind == 'grammar_ascii':
        entropy = random_bytes(kind, index)
        sentences = []
        total = 0
        for i in range(0, len(entropy)-12, 12):
            words = [WORDS[x % len(WORDS)] for x in entropy[i:i+12]]
            sentence = (' '.join(words).capitalize() + '.\n').encode('ascii')
            sentences.append(sentence)
            total += len(sentence)
            if total >= BLOCK:
                break
        return b''.join(sentences)[:BLOCK]
    if kind in ('csv_records', 'json_logs'):
        entropy = random_bytes(kind, index)
        rows = []
        total = 0
        for i in range(BLOCK // 4):
            record_id = index * (BLOCK // 4) + i
            value = int.from_bytes(entropy[i*4:i*4+4], 'little')
            if kind == 'csv_records':
                row = f'{record_id:012d},{1700000000 + record_id},sensor-{record_id % 127:03d},{value % 100000 / 100:.2f},{value % 4}\n'.encode()
            else:
                # Fixed key order and ASCII are intentional synthetic structure.
                row = f'{{"id":{record_id},"time":{1700000000+record_id},"host":"node-{record_id%127:03d}","level":"{("info","warn","error")[value%3]}","value":{value%100000},"ok":{("true","false")[value%2]}}}\n'.encode()
            rows.append(row)
            total += len(row)
            if total >= BLOCK:
                break
        return b''.join(rows)[:BLOCK]
    if kind == 'mutated_records':
        template = bytearray(random_bytes('mutated-record-template', 0, 1024))
        entropy = random_bytes(kind, index, 4096)
        rows = []
        for i in range(BLOCK // 1024):
            row = template.copy()
            position = int.from_bytes(entropy[4*i:4*i+2], 'little') % 1024
            row[position] = entropy[4*i+2]
            row[(position + 1) % 1024] = entropy[4*i+3]
            rows.append(row)
        return b''.join(rows)
    if kind == 'sparse_binary':
        out = bytearray(BLOCK)
        entropy = random_bytes(kind, index, 256)
        for i in range(16):
            out[i*65536:i*65536+16] = entropy[i*16:i*16+16]
        return bytes(out)
    if kind == 'delta_timeseries':
        entropy = random_bytes(kind, index, BLOCK // 16)
        out = bytearray(BLOCK)
        for i in range(BLOCK // 16):
            tick = index * (BLOCK // 16) + i
            value = tick * 7 + entropy[i] % 5 - 2
            struct.pack_into('<Qq', out, i*16, 1700000000000 + tick*1000, value)
        return bytes(out)
    if kind == 'mixed_entropy':
        return (random_bytes(kind, index, BLOCK//4) + bytes(BLOCK//4) +
                block('sequential_bytes', index)[:BLOCK//4] + block('low_entropy_ascii', index)[:BLOCK//4])
    if kind == 'heterogeneous':
        # Contiguous 16 MiB regions rotate through the twelve other classes.
        return block(CLASSES[(index // 16) % 12], index)
    raise ValueError(kind)


def generate(kind, size, destination):
    digest = hashlib.sha256()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('xb') as stream:
        for index in range((size + BLOCK-1)//BLOCK):
            data = block(kind, index)[:min(BLOCK, size-index*BLOCK)]
            assert len(data) == min(BLOCK, size-index*BLOCK)
            stream.write(data)
            digest.update(data)
    return dict(generator=VERSION, generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                seed_hex=SEED.hex(), data_class=kind, original_bytes=size, sha256=digest.hexdigest(),
                path=str(destination.absolute()), evidence_layer='synthetic scaling',
                caveat='Deterministic synthetic data; not real-world evidence. Text/record blocks may end mid-record.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('kind', choices=CLASSES)
    parser.add_argument('size', type=int, help='Exact bytes, e.g. 10737418240 for 10 GiB')
    parser.add_argument('destination', type=Path)
    parser.add_argument('--manifest', type=Path, required=True)
    args = parser.parse_args()
    if args.size <= 0:
        parser.error('size must be positive')
    row = generate(args.kind, args.size, args.destination)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(row, indent=2)+'\n')
    print(json.dumps(row))


if __name__ == '__main__':
    main()
