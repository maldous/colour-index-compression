"""An ordered subset's exact combinadic rank and same-information arithmetic.

Both controls know the universe size and number of selected positions. They
exclude repeated and out-of-order positions. All serialization is physical.
"""
from math import comb
from .multinomial import vencode, vdecode, _ArithmeticEncoder, _ArithmeticDecoder


def choose(n, k):
    return comb(n, k) if 0 <= k <= n else 0


def validate(values, universe):
    if universe < 0 or list(values) != sorted(set(values)) or any(x < 0 or x >= universe for x in values):
        raise ValueError('invalid ordered subset')


def encode(values, universe, method=0):
    validate(values, universe)
    if method == 0:
        rank = sum(choose(x, i + 1) for i, x in enumerate(values))
        size = ((choose(universe, len(values)) - 1).bit_length() + 7) // 8
        return rank.to_bytes(size, 'big')
    if method != 1:
        raise ValueError('invalid subset method')
    coder = _ArithmeticEncoder()
    arithmetic(values, universe, len(values), coder)
    payload, bits = coder.finish()
    return vencode(bits) + payload


def _arithmetic_position(values, universe, remaining, minimum, coder, index):
    low = minimum; high = universe - remaining
    while low < high:
        mid = (low + high) // 2
        left = choose(universe - low, remaining) - choose(universe - mid - 1, remaining)
        right = choose(universe - mid - 1, remaining) - choose(universe - high - 1, remaining)
        total = left + right
        scale = 1 << 20
        frequency = min(scale - 1, max(1, (left * scale + total // 2) // total))
        take_left = values[index] <= mid if values is not None else coder.target(scale) < frequency
        start, end = (0, frequency) if take_left else (frequency, scale)
        if values is None:
            coder.update(start, end, scale)
        else:
            coder.encode(start, end, scale)
        if take_left:
            high = mid
        else:
            low = mid + 1
    return low


def arithmetic(values, universe, count, coder):
    decoded = []; minimum = 0
    for i in range(count):
        selected = _arithmetic_position(values, universe, count - i, minimum, coder, i)
        decoded.append(selected); minimum = selected + 1
    return decoded


def _decode_rank(blob, pos, universe, count):
        possibilities = choose(universe, count)
        size = ((possibilities - 1).bit_length() + 7) // 8
        if pos + size > len(blob):
            raise ValueError('truncated subset rank')
        rank = int.from_bytes(blob[pos:pos + size], 'big'); pos += size
        if rank >= possibilities:
            raise ValueError('subset rank outside class')
        result = [0] * count; upper = universe - 1
        for k in range(count, 0, -1):
            low = k - 1; high = upper
            while low < high:
                mid = (low + high + 1) // 2
                if choose(mid, k) <= rank:
                    low = mid
                else:
                    high = mid - 1
            result[k - 1] = low; rank -= choose(low, k); upper = low - 1
        return result, pos


def _decode_arithmetic(blob, pos, universe, count):
    bits, pos = vdecode(blob, pos); size = (bits + 7) // 8
    if pos + size > len(blob):
        raise ValueError('truncated subset arithmetic')
    coder = _ArithmeticDecoder(blob[pos:pos + size], bits)
    return arithmetic(None, universe, count, coder), pos + size


def decode(blob, pos, universe, count, method=0):
    if not 0 <= count <= universe or universe > (1 << 30):
        raise ValueError('invalid subset dimensions')
    if method == 0:
        return _decode_rank(blob, pos, universe, count)
    if method != 1:
        raise ValueError('invalid subset method')
    return _decode_arithmetic(blob, pos, universe, count)
