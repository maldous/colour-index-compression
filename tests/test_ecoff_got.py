import io
import struct
import tarfile
import pytest
from benchmarks import ecoff_got as codec


def object_file(values, addresses):
    names = b'\0alpha\0beta\0'
    symbols = b''.join(struct.pack('<IIQIBBH', off, 0, value, 0, 0x12, 0, 0xff01)
                       for off, value in zip((0, 1, 7), values))
    dynamic = b''.join(struct.pack('<IIQ', tag, 0, val | (0xdeadbeef << 32)) for tag, val in
                       ((0x7000000a, 0), (0x70000013, 0), (0x70000011, 3), (0, 0)))
    parts = [(b'.dynstr', names), (b'.dynsym', symbols), (b'.hash', struct.pack('<7I', 2, 3, 0, 0, 0, 0, 0)),
             (b'.dynamic', dynamic), (b'.got', struct.pack('<3Q', *addresses))]
    out = bytearray(104 + len(parts) * 64)
    struct.pack_into('<HHIQIHH', out, 0, 0x183, len(parts), 0, 0, 0, 80, 0x2007)
    for i, (name, raw) in enumerate(parts):
        offset = len(out); out.extend(raw)
        struct.pack_into('<8sQQQQQQHHI', out, 104 + 64 * i, name, 0, 0, len(raw), offset, 0, 0, 0, 0, 0)
    return bytes(out)


def archive():
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode='w') as tar:
        for name, data in [('unknown-a', object_file((0, 0, 42), (0, 99, 1234567))),
                           ('unknown-b', object_file((0, 99, 42), (0, 99, 42)))]:
            info = tarfile.TarInfo(name); info.size = len(data); tar.addfile(info, io.BytesIO(data))
    return stream.getvalue() + b'arbitrary trailer'


@pytest.mark.parametrize('mode', range(4))
def test_global_definitions_choices_exceptions(mode):
    data = archive()
    for shared, expected in ((False, 4), (True, 5)):
        raw, stats = codec.transform(data, mode, shared)
        assert codec.inverse(raw) == data
        assert stats['mapped_addresses'] == 6
        assert stats['in_candidates'] == expected
        if mode == 2:
            assert stats['choice_model_bits'] == pytest.approx(stats['candidate_combinatorial_bits'])


def test_variable_radix_multiple_blocks_and_adaptive_rescale():
    alphabets = [2, 3, 5, 1, 15] * 2500; digits = [i % k for i, k in enumerate(alphabets)]; contexts = [0] * len(digits)
    for mode in range(4):
        packed, _, _ = codec.encode_choices(digits, alphabets, contexts, mode)
        assert codec.decode_choices(packed, alphabets, contexts, mode) == digits
    for literal in (b'', b'nonobject input', object_file((0, 7, 8), (0, 7, 0xffffffffffffffff))):
        assert codec.inverse(codec.transform(literal)[0]) == literal


def test_corrupted_metadata_and_rank_rejected():
    raw, _ = codec.transform(archive(), 1)
    with pytest.raises(ValueError):
        codec.inverse(raw[:-1])
    with pytest.raises(ValueError, match='outside state space'):
        codec.decode_choices(b'\xff', [3], [0], 1)
