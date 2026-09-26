"""Deterministic fixed-point PAQ-style logistic mixer experiment.

No floating point participates in the encoded representation. Log2 odds are computed with
integer fixed-point arithmetic; inverse squash uses the corresponding monotonic table.
The predictor set is entirely format-agnostic: contiguous/sparse byte contexts, generic
lags, and a match predictor. Recent decoded history is deterministically replayed before
each block so the model does not reset at streaming boundaries.
"""
from __future__ import annotations

from bisect import bisect_left

from .multinomial import _ArithmeticDecoder, _ArithmeticEncoder, vdecode, vencode

VERSION = 1
PROB_SCALE = 4096
LOG_FRAC = 12
LOG_SCALE = 1 << LOG_FRAC
WEIGHT_SCALE = 1 << 10
CLIP_LOG = 12 * LOG_SCALE
COUNT_LIMIT = 2048
HISTORY_MAX = 65536
HISTORY_MIN = 4096
ETA_SHIFTS = (5, 6, 7)

PATTERNS = (
    (),
    (1,),
    (1, 2),
    (1, 2, 3),
    (1, 2, 3, 4),
    (1, 3),
    (1, 4),
    (1, 5),
    (2, 3),
    (2, 4),
    (3, 6),
    (4, 8),
    (1, 4, 8),
)
LAGS = (1, 2, 4, 8, 16, 32)
MATCH_ORDER = 4


def _fixed_log2(value: int) -> int:
    if value <= 0:
        raise ValueError("fixed log2 requires a positive integer")

    integer = value.bit_length() - 1
    q = 32
    one = 1 << q
    y = (value << q) >> integer
    fraction = 0

    for index in range(LOG_FRAC):
        y = (y * y) >> q
        if y >= 2 * one:
            y >>= 1
            fraction |= 1 << (LOG_FRAC - 1 - index)

    return integer * LOG_SCALE + fraction


_STRETCH = [0] + [
    _fixed_log2(probability)
    - _fixed_log2(PROB_SCALE - probability)
    for probability in range(1, PROB_SCALE)
]


def _squash(log_odds: int) -> int:
    if log_odds <= _STRETCH[1]:
        return 1
    if log_odds >= _STRETCH[-1]:
        return PROB_SCALE - 1

    index = bisect_left(_STRETCH, log_odds, 1)
    if abs(_STRETCH[index] - log_odds) < abs(
        log_odds - _STRETCH[index - 1]
    ):
        return index
    return index - 1


def _context(history: bytearray, pattern: tuple[int, ...]):
    if not pattern:
        return ()
    if len(history) < max(pattern):
        return None
    return tuple(history[-offset] for offset in pattern)


def _context_probability(counts: list[int] | None) -> int:
    if counts is None:
        return PROB_SCALE // 2
    zero, one = counts
    result = ((2 * one + 1) * PROB_SCALE) // (2 * (zero + one + 1))
    return min(PROB_SCALE - 1, max(1, result))


def _reliability_probability(
    predicted: int | None,
    reliability: list[list[int]],
    bit_position: int,
) -> int:
    if predicted is None:
        return PROB_SCALE // 2

    good, bad = reliability[bit_position]
    confidence = (
        (2 * good + 1) * PROB_SCALE
    ) // (2 * (good + bad + 1))
    confidence = min(PROB_SCALE - 1, max(PROB_SCALE // 2, confidence))
    bit = (predicted >> (7 - bit_position)) & 1
    return confidence if bit else PROB_SCALE - confidence


class _State:
    def __init__(self, eta_shift: int) -> None:
        self.history = bytearray()
        self.tables = [dict() for _ in PATTERNS]
        expert_count = len(PATTERNS) + len(LAGS) + 1
        initial = max(1, WEIGHT_SCALE // expert_count)
        self.weights = [[initial] * expert_count for _ in range(8)]
        self.bias = [0] * 8
        self.eta_shift = eta_shift
        self.lag_reliability = [
            [[1, 1] for _ in range(8)]
            for _ in LAGS
        ]
        self.match_reliability = [[1, 1] for _ in range(8)]
        self.matches: dict[bytes, int] = {}

    def probabilities(self, bit_position: int, prefix_bits: int):
        probabilities = []
        keys = []

        for index, pattern in enumerate(PATTERNS):
            context = _context(self.history, pattern)
            key = (
                (context, bit_position, prefix_bits)
                if context is not None else None
            )
            keys.append(key)
            probabilities.append(
                _context_probability(
                    self.tables[index].get(key)
                    if key is not None else None
                )
            )

        for lag_index, lag in enumerate(LAGS):
            predicted = (
                self.history[-lag]
                if len(self.history) >= lag else None
            )
            probabilities.append(
                _reliability_probability(
                    predicted,
                    self.lag_reliability[lag_index],
                    bit_position,
                )
            )

        predicted = (
            self.matches.get(bytes(self.history[-MATCH_ORDER:]))
            if len(self.history) >= MATCH_ORDER
            else None
        )
        probabilities.append(
            _reliability_probability(
                predicted,
                self.match_reliability,
                bit_position,
            )
        )

        stretches = [_STRETCH[p] for p in probabilities]
        mixed = self.bias[bit_position] + (
            sum(
                weight * stretch
                for weight, stretch
                in zip(self.weights[bit_position], stretches)
            ) // WEIGHT_SCALE
        )
        return _squash(mixed), stretches, keys

    def update(
        self,
        bit_position: int,
        prefix_bits: int,
        bit: int,
        probability_one: int,
        stretches: list[int],
        keys,
    ) -> None:
        error = (
            PROB_SCALE - probability_one
            if bit else -probability_one
        )

        bias_delta = (
            error * LOG_SCALE
        ) // (PROB_SCALE * (1 << self.eta_shift))
        self.bias[bit_position] = max(
            -CLIP_LOG,
            min(CLIP_LOG, self.bias[bit_position] + bias_delta),
        )

        denominator = (
            PROB_SCALE * LOG_SCALE * (1 << self.eta_shift)
        )
        weights = self.weights[bit_position]
        for index, stretch in enumerate(stretches):
            delta = (
                error * stretch * WEIGHT_SCALE
            ) // denominator
            weights[index] = max(
                -4 * WEIGHT_SCALE,
                min(4 * WEIGHT_SCALE, weights[index] + delta),
            )

        for index, key in enumerate(keys):
            if key is None:
                continue
            counts = self.tables[index].get(key)
            if counts is None:
                counts = [0, 0]
                self.tables[index][key] = counts
            counts[bit] += 1
            if counts[0] + counts[1] > COUNT_LIMIT:
                counts[0] = (counts[0] + 1) // 2
                counts[1] = (counts[1] + 1) // 2

        for lag_index, lag in enumerate(LAGS):
            if len(self.history) < lag:
                continue
            predicted = (
                self.history[-lag] >> (7 - bit_position)
            ) & 1
            reliability = self.lag_reliability[lag_index][bit_position]
            reliability[0 if predicted == bit else 1] += 1
            if sum(reliability) > COUNT_LIMIT:
                reliability[0] = (reliability[0] + 1) // 2
                reliability[1] = (reliability[1] + 1) // 2

        if len(self.history) >= MATCH_ORDER:
            predicted_byte = self.matches.get(
                bytes(self.history[-MATCH_ORDER:])
            )
            if predicted_byte is not None:
                predicted = (
                    predicted_byte >> (7 - bit_position)
                ) & 1
                reliability = self.match_reliability[bit_position]
                reliability[0 if predicted == bit else 1] += 1
                if sum(reliability) > COUNT_LIMIT:
                    reliability[0] = (reliability[0] + 1) // 2
                    reliability[1] = (reliability[1] + 1) // 2

    def finish_byte(self, byte: int) -> None:
        if len(self.history) >= MATCH_ORDER:
            self.matches[
                bytes(self.history[-MATCH_ORDER:])
            ] = byte
        self.history.append(byte)
        if len(self.history) > HISTORY_MAX:
            del self.history[:-HISTORY_MAX]


def _observe_byte(state: _State, byte: int) -> None:
    prefix_bits = 0
    for bit_position in range(8):
        bit = (byte >> (7 - bit_position)) & 1
        probability, stretches, keys = state.probabilities(
            bit_position, prefix_bits
        )
        state.update(
            bit_position,
            prefix_bits,
            bit,
            probability,
            stretches,
            keys,
        )
        prefix_bits = (prefix_bits << 1) | bit
    state.finish_byte(byte)


def _prime(
    prefix_history: bytes,
    block_length: int,
    eta_shift: int,
) -> _State:
    state = _State(eta_shift)
    training_length = min(
        len(prefix_history),
        HISTORY_MAX,
        max(HISTORY_MIN, block_length * 2),
    )
    for byte in prefix_history[-training_length:]:
        _observe_byte(state, byte)
    return state


def _encode(
    data: bytes,
    *,
    eta_shift: int,
    prefix_history: bytes,
) -> bytes:
    state = _prime(prefix_history, len(data), eta_shift)
    encoder = _ArithmeticEncoder()

    for byte in data:
        prefix_bits = 0
        for bit_position in range(8):
            bit = (byte >> (7 - bit_position)) & 1
            probability, stretches, keys = state.probabilities(
                bit_position, prefix_bits
            )
            zero = PROB_SCALE - probability

            if bit:
                encoder.encode(zero, PROB_SCALE, PROB_SCALE)
            else:
                encoder.encode(0, zero, PROB_SCALE)

            state.update(
                bit_position,
                prefix_bits,
                bit,
                probability,
                stretches,
                keys,
            )
            prefix_bits = (prefix_bits << 1) | bit

        state.finish_byte(byte)

    payload, bit_length = encoder.finish()
    eta_id = ETA_SHIFTS.index(eta_shift)
    return bytes((VERSION, eta_id)) + vencode(bit_length) + payload


def encode_fixed_mix(
    data: bytes,
    *,
    prefix_history: bytes = b"",
    eta_shift: int | None = None,
) -> bytes:
    if eta_shift is not None:
        if eta_shift not in ETA_SHIFTS:
            raise ValueError("unsupported fixed-mix learning rate")
        return _encode(
            data,
            eta_shift=eta_shift,
            prefix_history=prefix_history,
        )

    return min(
        (
            _encode(
                data,
                eta_shift=shift,
                prefix_history=prefix_history,
            )
            for shift in ETA_SHIFTS
        ),
        key=len,
    )


def decode_fixed_mix(
    blob: bytes,
    *,
    source_length: int,
    prefix_history: bytes = b"",
) -> bytes:
    if len(blob) < 2 or blob[0] != VERSION:
        raise ValueError("unknown fixed-mix version")

    eta_id = blob[1]
    if eta_id >= len(ETA_SHIFTS):
        raise ValueError("invalid fixed-mix learning rate")
    eta_shift = ETA_SHIFTS[eta_id]

    bit_length, pos = vdecode(blob, 2)
    if pos + (bit_length + 7) // 8 != len(blob):
        raise ValueError("fixed-mix payload length mismatch")

    decoder = _ArithmeticDecoder(blob[pos:], bit_length)
    state = _prime(prefix_history, source_length, eta_shift)
    out = bytearray()

    for _ in range(source_length):
        byte = 0
        prefix_bits = 0

        for bit_position in range(8):
            probability, stretches, keys = state.probabilities(
                bit_position, prefix_bits
            )
            zero = PROB_SCALE - probability
            target = decoder.target(PROB_SCALE)

            if target < zero:
                bit = 0
                decoder.update(0, zero, PROB_SCALE)
            else:
                bit = 1
                decoder.update(zero, PROB_SCALE, PROB_SCALE)

            state.update(
                bit_position,
                prefix_bits,
                bit,
                probability,
                stretches,
                keys,
            )
            byte = (byte << 1) | bit
            prefix_bits = (prefix_bits << 1) | bit

        out.append(byte)
        state.finish_byte(byte)

    return bytes(out)
