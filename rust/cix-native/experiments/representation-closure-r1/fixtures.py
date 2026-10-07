#!/usr/bin/env python3
"""Frozen 8 KiB R1 controls; generation is separate from encoding."""
import argparse, hashlib, pathlib
N = 8192
def xorshift(seed=0x9e3779b97f4a7c15):
    while True:
        seed ^= (seed << 13) & ((1<<64)-1); seed ^= seed >> 7; seed ^= (seed << 17) & ((1<<64)-1)
        yield (seed >> 24) & 255
def data(kind):
    if kind == 'strong': return bytes((i // 2) & 255 for i in range(N))       # lag-2 delta sparse
    if kind == 'weak': return bytes(((i // 8) ^ i) & 255 for i in range(N))  # mixed lane relation
    if kind == 'absent':
        g=xorshift(); return bytes(next(g) for _ in range(N))
    raise ValueError(kind)
def main():
    p=argparse.ArgumentParser(); p.add_argument('kind',choices=('strong','weak','absent')); p.add_argument('output',type=pathlib.Path); a=p.parse_args()
    b=data(a.kind); a.output.write_bytes(b); print(hashlib.sha256(b).hexdigest())
if __name__ == '__main__': main()
