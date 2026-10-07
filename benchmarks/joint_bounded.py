"""Experimental exact PPM/rounded-mixer block portfolio.

One fixed policy: 256 KiB blocks, at most 64 KiB prior history, PPM orders 3/5/7,
raw fallback, and rounded mixers in 64 KiB subblocks. The five-byte magic distinguishes this frame from incumbent CIX.
The encoder holds input/output in memory, but model growth is bounded per block.
"""
import zlib
from cix.multinomial import vencode, vdecode

MAGIC = b'CIXT\x01'
BLOCK_SIZE = 262144
MAX_BLOCK_SIZE = 1048576
ORDERS = (3, 5, 7)


def encode(data, *, block_size=BLOCK_SIZE):
    from cix.ppm import encode_ppm
    from benchmarks.mixer_rounded_bounded import encode as encode_mixer
    if not 1 <= block_size <= MAX_BLOCK_SIZE:
        raise ValueError('invalid block size')
    result = bytearray(MAGIC + vencode(len(data)) + vencode(block_size)
                       + zlib.crc32(data).to_bytes(4, 'big'))
    for offset in range(0, len(data), block_size):
        block = data[offset:offset + block_size]
        history = data[max(0, offset - 65536):offset]
        best = b'\x00' + block
        for order in ORDERS:
            candidate = b'\x01' + encode_ppm(block, max_order=order, prefix_history=history)
            if len(candidate) < len(best):
                best = candidate
        mixed = b"\x02" + encode_mixer(block)
        if len(mixed) < len(best):
            best = mixed
        result.extend(vencode(len(best)))
        result.extend(best)
    return bytes(result)


def decode(frame):
    from cix.ppm import decode_ppm
    if frame[:5] != MAGIC:
        raise ValueError('invalid bounded PPM frame')
    length, pos = vdecode(frame, 5)
    block_size, pos = vdecode(frame, pos)
    if not 1 <= block_size <= MAX_BLOCK_SIZE or pos + 4 > len(frame):
        raise ValueError('invalid or truncated header')
    checksum = int.from_bytes(frame[pos:pos + 4], 'big')
    pos += 4
    output = bytearray()
    while len(output) < length:
        expected = min(block_size, length - len(output))
        size, pos = vdecode(frame, pos)
        if not 1 <= size <= expected + 1 or pos + size > len(frame):
            raise ValueError('invalid block framing')
        mode = frame[pos]
        payload = frame[pos + 1:pos + size]
        if mode == 0:
            block = payload
        elif mode == 1:
            block = decode_ppm(payload, source_length=expected, prefix_history=bytes(output[-65536:]))
        elif mode == 2:
            from benchmarks.mixer_rounded_bounded import decode as decode_mixer
            nested_length, _ = vdecode(payload, 5)
            if nested_length != expected:
                raise ValueError('nested mixer length mismatch')
            block = decode_mixer(payload)
        else:
            raise ValueError('unknown block mode')
        if len(block) != expected:
            raise ValueError('block length mismatch')
        output.extend(block)
        pos += size
    if pos != len(frame):
        raise ValueError('trailing bytes')
    if zlib.crc32(output) != checksum:
        raise ValueError('checksum mismatch')
    return bytes(output)
