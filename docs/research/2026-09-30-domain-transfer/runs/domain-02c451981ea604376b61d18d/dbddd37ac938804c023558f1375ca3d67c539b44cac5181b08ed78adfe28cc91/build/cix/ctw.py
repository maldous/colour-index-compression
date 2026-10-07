"""Binary Context Tree Weighting experiment for universal CIX.

This is a format-agnostic online Bayesian mixture over binary context trees. It operates
on the bitstream directly and therefore complements byte-level multinomial/PPM models.

The implementation uses the classic CTW recursion:
    P_w(node) = 1/2 P_KT(node) + 1/2 P_w(left) P_w(right)
with a Krichevsky-Trofimov estimator at every node. Probabilities are quantized before
arithmetic coding so encoder and decoder make identical interval decisions.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from .multinomial import _ArithmeticDecoder, _ArithmeticEncoder, vdecode, vencode

CTW_VERSION = 1
PROB_SCALE = 1 << 15
LOG_HALF = math.log(0.5)


def _logadd(a: float, b: float) -> float:
    if a < b:
        a, b = b, a
    return a + math.log1p(math.exp(b - a))


@dataclass
class _Node:
    depth: int
    zero: int = 0
    one: int = 0
    log_kt: float = 0.0
    log_w: float = 0.0
    children: list["_Node | None"] = field(default_factory=lambda: [None, None])

    def kt_increment(self, bit: int) -> float:
        count = self.one if bit else self.zero
        return math.log(count + 0.5) - math.log(self.zero + self.one + 1.0)


class _Tree:
    def __init__(self, depth: int, prefix_history: bytes = b"") -> None:
        if not 1 <= depth <= 24:
            raise ValueError("CTW depth outside supported range")
        self.depth = depth
        self.root = _Node(0)

        bits = []
        for byte in prefix_history:
            bits.extend((byte >> shift) & 1 for shift in range(7, -1, -1))
        if len(bits) >= depth:
            self.history = bits[-depth:]
        else:
            self.history = [0] * (depth - len(bits)) + bits

    def _path(self) -> tuple[list[_Node], list[int]]:
        nodes = [self.root]
        directions = []
        node = self.root
        for offset in range(self.depth):
            direction = self.history[-1 - offset]
            directions.append(direction)
            child = node.children[direction]
            if child is None:
                child = _Node(node.depth + 1)
                node.children[direction] = child
            node = child
            nodes.append(node)
        return nodes, directions

    def probability_one(self) -> float:
        nodes, directions = self._path()
        new_kt = [
            node.log_kt + node.kt_increment(1)
            for node in nodes
        ]

        new_w = new_kt[-1]
        for index in range(self.depth - 1, -1, -1):
            node = nodes[index]
            direction = directions[index]
            changed_child = new_w
            other = node.children[1 - direction]
            other_w = other.log_w if other is not None else 0.0
            split = changed_child + other_w
            new_w = _logadd(new_kt[index], split) + LOG_HALF

        probability = math.exp(new_w - self.root.log_w)
        return min(1.0 - 1e-12, max(1e-12, probability))

    def quantized_one(self) -> int:
        value = int(round(self.probability_one() * PROB_SCALE))
        return min(PROB_SCALE - 1, max(1, value))

    def update(self, bit: int) -> None:
        nodes, directions = self._path()

        for node in nodes:
            node.log_kt += node.kt_increment(bit)
            if bit:
                node.one += 1
            else:
                node.zero += 1

        nodes[-1].log_w = nodes[-1].log_kt
        for index in range(self.depth - 1, -1, -1):
            node = nodes[index]
            left = node.children[0]
            right = node.children[1]
            split = (
                (left.log_w if left is not None else 0.0)
                + (right.log_w if right is not None else 0.0)
            )
            node.log_w = _logadd(node.log_kt, split) + LOG_HALF

        self.history.append(bit)
        if len(self.history) > self.depth:
            del self.history[0]


def estimate_ctw_bits(
    data: bytes,
    *,
    depth: int = 16,
    prefix_history: bytes = b"",
    sample_limit: int = 4096,
) -> float:
    sample = data[:sample_limit]
    if not sample:
        return 0.0

    tree = _Tree(depth, prefix_history)
    bits = 0.0
    for byte in sample:
        for shift in range(7, -1, -1):
            bit = (byte >> shift) & 1
            one = tree.quantized_one()
            mass = one if bit else PROB_SCALE - one
            bits += math.log2(PROB_SCALE) - math.log2(mass)
            tree.update(bit)

    return bits * (len(data) / len(sample))


def encode_ctw(
    data: bytes,
    *,
    depth: int = 16,
    prefix_history: bytes = b"",
) -> bytes:
    tree = _Tree(depth, prefix_history)
    encoder = _ArithmeticEncoder()

    for byte in data:
        for shift in range(7, -1, -1):
            bit = (byte >> shift) & 1
            one = tree.quantized_one()
            zero = PROB_SCALE - one
            if bit:
                encoder.encode(zero, PROB_SCALE, PROB_SCALE)
            else:
                encoder.encode(0, zero, PROB_SCALE)
            tree.update(bit)

    payload, bit_length = encoder.finish()
    return bytes((CTW_VERSION, depth)) + vencode(bit_length) + payload


def decode_ctw(
    blob: bytes,
    *,
    source_length: int,
    prefix_history: bytes = b"",
) -> bytes:
    if len(blob) < 2 or blob[0] != CTW_VERSION:
        raise ValueError("unknown CTW version")
    depth = blob[1]
    if not 1 <= depth <= 24:
        raise ValueError("invalid CTW depth")

    bit_length, pos = vdecode(blob, 2)
    byte_length = (bit_length + 7) // 8
    if pos + byte_length != len(blob):
        raise ValueError("CTW payload length mismatch")

    tree = _Tree(depth, prefix_history)
    decoder = _ArithmeticDecoder(blob[pos:], bit_length)
    out = bytearray()

    for _ in range(source_length):
        byte = 0
        for _bit_pos in range(8):
            one = tree.quantized_one()
            zero = PROB_SCALE - one
            target = decoder.target(PROB_SCALE)
            if target < zero:
                bit = 0
                decoder.update(0, zero, PROB_SCALE)
            else:
                bit = 1
                decoder.update(zero, PROB_SCALE, PROB_SCALE)
            tree.update(bit)
            byte = (byte << 1) | bit
        out.append(byte)

    return bytes(out)
