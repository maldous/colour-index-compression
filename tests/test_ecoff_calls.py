import struct
import pytest
from benchmarks import ecoff_calls as codec


def object_file():
    virtual = 0x120000000
    def call(disp, reg=26):
        return (0x34 << 26) | (reg << 21) | (disp & codec.MASK)
    text = struct.pack('<8I', call(1), call(-2), call(4), call((1 << 20) - 1), call(-(1 << 20)), call(0, 25), 0, 0)
    names = b'\0first\0second\0'
    symbols = b''.join(struct.pack('<IIQIBBH', offset, 0, value, 0, 0x12, 0, 0xff01)
                       for offset, value in [(0, 0), (1, virtual), (7, virtual + 8)])
    parts = [(b'.dynstr', 0x1000, names), (b'.dynsym', 0x2000, symbols),
             (b'.hash', 0x3000, struct.pack('<7I', 2, 3, 0, 0, 0, 0, 0)),
             (b'.pdata', virtual - 1024, struct.pack('<4i', 1024, 0, 1032, 0)),
             (b'.text', virtual, text), (b'.init', virtual + 32, struct.pack('<I', call(-9))),
             (b'.fini', virtual + 36, b'\0' * 4)]
    out = bytearray(104 + 64 * len(parts)); struct.pack_into('<HHIQIHH', out, 0, 0x183, len(parts), 0, 0, 0, 80, 0x2007)
    for i, (name, address, data) in enumerate(parts):
        pointer = len(out); out.extend(data)
        struct.pack_into('<8sQQQQQQHHI', out, 104 + 64 * i, name, address, address, len(data), pointer, 0, 0, 0, 0, 0)
    return bytes(out) + b'tail'


@pytest.mark.parametrize('mode', range(6))
def test_call_indices_signed_edges_and_exceptions(mode):
    data = object_file(); raw, stats = codec.transform(data, mode)
    assert codec.inverse(raw) == data
    assert stats['calls'] == 6 and stats['targets_in_candidates'] == 3
    if mode == 4:
        assert stats['choice_model_bits'] == pytest.approx(stats['candidate_combinatorial_bits'])
    assert codec.inverse(codec.transform(b'plain input', mode)[0]) == b'plain input'


def test_arithmetic_uniform_control_and_adaptive_rescaling():
    alphabets = [3] * 70000; contexts = [0] * len(alphabets); digits = [i % 3 for i in range(len(alphabets))]
    for adaptive in (False, True):
        payload, bits = codec.arithmetic(digits, alphabets, contexts, adaptive)
        restored, decoded_bits = codec.arithmetic(None, alphabets, contexts, adaptive, payload)
        assert restored == digits and decoded_bits == pytest.approx(bits)
    raw, _ = codec.transform(object_file(), 3)
    with pytest.raises(ValueError):
        codec.inverse(raw[:-1])
