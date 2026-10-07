import io
import random
import struct
import tarfile
import pytest
from benchmarks import ecoff_fields as codec
from tests.test_ecoff_constraints import object_file


@pytest.mark.parametrize('mode', range(4))
def test_structural_dependencies_and_exceptions(mode):
    data = object_file(True)
    raw, stats = codec.transform(data, mode)
    assert codec.inverse(raw) == data
    if mode:
        assert stats['exact_name_predictions'] == 4
        assert stats['symbols'] == 4
    assert codec.inverse(codec.transform(b'unknown\x00literal', mode)[0]) == b'unknown\x00literal'


def test_modular_residuals_arbitrary_fields_and_tar_names():
    rng = random.Random(387)
    for bits in (24, 32, 64):
        for _ in range(100):
            a, b = rng.randrange(1 << bits), rng.randrange(1 << bits)
            assert codec.delta(codec.delta(a, b, bits), b, bits, True) == a
    data = bytearray(object_file())
    sections = codec.base.sections(data); so, _ = sections[b'.dynsym']; ro, _ = sections[b'.rel.dyn']
    for i in range(4):
        struct.pack_into('<QIBBH', data, so + i * 24 + 8, rng.getrandbits(64), rng.getrandbits(32),
                         rng.getrandbits(8), rng.getrandbits(8), rng.getrandbits(16))
        struct.pack_into('<QII', data, ro + i * 16, rng.getrandbits(64), rng.getrandbits(32), rng.getrandbits(32))
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode='w') as archive:
        for name in ('opaque', 'another-opaque'):
            info = tarfile.TarInfo(name); info.size = len(data); archive.addfile(info, io.BytesIO(data))
    source = stream.getvalue() + b'literal tail'
    for mode in (1, 2, 3):
        raw, stats = codec.transform(source, mode)
        assert codec.inverse(raw) == source
        assert stats['field_objects'] == 2


def test_invalid_name_remains_literal_and_bad_metadata_rejected():
    data = bytearray(object_file()); so, _ = codec.base.sections(data)[b'.dynsym']
    struct.pack_into('<I', data, so, 0xffffffff)
    raw, stats = codec.transform(bytes(data), 3)
    assert stats['field_objects'] == 0 and codec.inverse(raw) == data
    for bad in (raw[:-1], raw[:-13] + bytes([255]) * 8 + raw[-5:]):
        with pytest.raises(ValueError):
            codec.inverse(bad)
