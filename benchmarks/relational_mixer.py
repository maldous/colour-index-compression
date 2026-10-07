"""CIXQ6 causal byte relations: successor histories and modular differences.

No external labels or dictionaries. Modes are fixed decoder-visible ablations.
Mode 0 is a Q5 payload-compatible native acceleration control.
"""
from contextlib import contextmanager
import ctypes
from pathlib import Path
import zlib
from cix import fixedmix as m
from cix.multinomial import vencode, vdecode
from benchmarks.ppm_expert_mixer import policy as ppm_policy

MAGIC = b'CIXQ\x06'
LIBRARY = 'results/leaderboard/native_relational_mixer.so'


def distribution(tables, history):
    weights = [0] * 256
    excluded = set()
    remaining = 1 << 24
    for order in range(min(len(tables)-1, len(history)), -1, -1):
        key = bytes(history[-order:]) if order else b''
        counts = tables[order].get(key, {})
        eligible = [(s, c) for s, c in counts.items() if s not in excluded]
        if not eligible:
            continue
        mass = sum(c for _, c in eligible)
        distinct = len(eligible)
        for symbol, count in eligible:
            weights[symbol] += remaining * count // (mass + distinct)
            excluded.add(symbol)
        remaining = remaining * distinct // (mass + distinct)
    unseen = 256 - len(excluded)
    for s in range(256):
        if s not in excluded and unseen:
            weights[s] += remaining // unseen
    return weights


@contextmanager
def policy(bits, mode):
    if mode not in range(4):
        raise ValueError('unknown relation mode')
    with ppm_policy(bits):
        base = m._State
        class State(base):
            def __init__(self, eta_shift):
                super().__init__(eta_shift)
                count = 23 + (2 if mode & 1 else 0) + (1 if mode & 2 else 0)
                for row in self.weights:
                    row[:] = [1024 // count] * count
                self.initial_weights = [row[:] for row in self.weights]
                self.successors = [0] * 256
                self.relations = [{}, {}]
                self.delta_tables = [{}, {}]
                self.delta_history = bytearray()
            def probabilities(self, bit_position, prefix_bits):
                _, stretches, keys = super().probabilities(bit_position, prefix_bits)
                prev = self.history[-1] if self.history else 0
                self.relation_keys = []
                if mode & 1:
                    for table, context in zip(self.relations, (self.successors[prev], (prev << 16) | self.successors[prev])):
                        key = (context << 8) | (1 << bit_position) | prefix_bits
                        self.relation_keys.append(key)
                        stretches.append(m._STRETCH[m._context_probability(table.get(key))] if self.history else m._STRETCH[2048])
                if mode & 2:
                    if bit_position == 0:
                        weights = distribution(self.delta_tables, self.delta_history)
                        self.delta_cumulative = [0]
                        for byte in range(256):
                            self.delta_cumulative.append(self.delta_cumulative[-1] + weights[(byte-prev) & 255] + 1)
                    c = self.delta_cumulative
                    lo = prefix_bits << (8-bit_position)
                    hi = lo + (1 << (8-bit_position)); mid = (lo+hi)//2
                    p = max(1, min(4095, 4096*(c[hi]-c[mid])//(c[hi]-c[lo])))
                    stretches.append(m._STRETCH[p])
                mixed = self.bias[bit_position] + sum(w*s for w,s in zip(self.weights[bit_position], stretches))//1024
                return m._squash(mixed), stretches, keys
            def update(self, bit_position, prefix_bits, bit, probability_one, stretches, keys):
                super().update(bit_position, prefix_bits, bit, probability_one, stretches, keys)
                if mode & 1 and self.history:
                    for table, key in zip(self.relations, self.relation_keys):
                        counts = table.setdefault(key, [0, 0]); counts[bit] += 1
                        if sum(counts) > 2048:
                            counts[:] = [(c+1)//2 for c in counts]
            def finish_byte(self, byte):
                prev = self.history[-1] if self.history else 0
                if mode & 1 and self.history:
                    self.successors[prev] = ((self.successors[prev] << 8) | byte) & 65535
                if mode & 2:
                    delta = (byte-prev) & 255
                    for order in range(min(1, len(self.delta_history))+1):
                        key = bytes(self.delta_history[-order:]) if order else b''
                        counts = self.delta_tables[order].setdefault(key, {})
                        counts[delta] = counts.get(delta, 0) + 1
                        if sum(counts.values()) > 16384:
                            for symbol in counts:
                                counts[symbol] = (counts[symbol]+1)//2
                    self.delta_history[:] = bytes([delta])
                super().finish_byte(byte)
        m._State = State
        try:
            yield
        finally:
            m._State = base


def frame(payload, data, bits, mode):
    return MAGIC + bytes([bits, mode]) + vencode(len(data)) + zlib.crc32(data).to_bytes(4, 'big') + payload


def unpack(blob):
    if blob[:5] == b'CIXQ\x05':
        bits, mode, start = blob[5], 0, 6
    elif blob[:5] == MAGIC and len(blob) >= 7:
        bits, mode, start = blob[5], blob[6], 7
    else:
        raise ValueError('unknown relational frame')
    if bits not in (0, 2, 4) or mode not in range(4):
        raise ValueError('invalid model parameters')
    length, pos = vdecode(blob, start)
    if pos+4 > len(blob):
        raise ValueError('truncated checksum')
    return bits, mode, length, int.from_bytes(blob[pos:pos+4], 'big'), blob[pos+4:]


def encode(data, bits=2, mode=3):
    with policy(bits, mode):
        payload = m.encode_fixed_mix(data, eta_shift=6)
    return frame(payload, data, bits, mode)


def decode(blob):
    bits, mode, length, checksum, payload = unpack(blob)
    with policy(bits, mode):
        data = m.decode_fixed_mix(payload, source_length=length)
    if zlib.crc32(data) != checksum:
        raise ValueError('checksum mismatch')
    return data


class Native:
    def __init__(self, library=LIBRARY):
        self.lib = ctypes.CDLL(str(Path(library).resolve()))
        common = [ctypes.c_uint, ctypes.c_uint, ctypes.POINTER(ctypes.c_int32), ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_size_t)]
        self.lib.cix_relation_encode.argtypes = [ctypes.c_void_p, ctypes.c_size_t] + common
        self.lib.cix_relation_decode.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_size_t] + common
        self.lib.cix_relation_encode.restype = self.lib.cix_relation_decode.restype = ctypes.c_int
        self.lib.cix_ppm_free.argtypes = [ctypes.c_void_p]
        self.table = (ctypes.c_int32*4096)(*m._STRETCH)
    def call(self, fn, *args):
        pointer, size = ctypes.c_void_p(), ctypes.c_size_t()
        if fn(*args, self.table, ctypes.byref(pointer), ctypes.byref(size)):
            raise ValueError('native relational coder rejected input')
        try:
            return ctypes.string_at(pointer, size.value)
        finally:
            self.lib.cix_ppm_free(pointer)
    def encode(self, data, bits=2, mode=3):
        payload = self.call(self.lib.cix_relation_encode, data, len(data), bits, mode)
        return frame(payload, data, bits, mode)
    def decode(self, blob):
        bits, mode, length, checksum, payload = unpack(blob)
        if length > 1 << 30:
            raise ValueError('experimental frame too large')
        data = self.call(self.lib.cix_relation_decode, payload, len(payload), length, bits, mode)
        if len(data) != length or zlib.crc32(data) != checksum:
            raise ValueError('length or checksum mismatch')
        return data
