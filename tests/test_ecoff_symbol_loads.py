import io
import struct
import tarfile
import pytest
from benchmarks import ecoff_symbol_loads as codec


def object_file(order=(b'alpha', b'beta'), repeated=False):
    names = b'\0' + b''.join(name + b'\0' for name in order)
    offsets = [1]
    for name in order[:-1]:
        offsets.append(offsets[-1] + len(name) + 1)
    table = bytes(24) + b''.join(struct.pack('<IIQIBBH', p, 0, 0x100 + i * 8, 0, 0x12, 0, 0xff01) for i, p in enumerate(offsets))
    got_virtual = 0x200000000; gp = got_virtual + 32752
    loads = [(-32752, 29), (-32744, 29), (123, 29), (-32752, 28), (-32752, 29)]
    code = b''.join(struct.pack('<I', (0x29 << 26) | (27 << 21) | (rb << 16) | (disp & 65535)) for disp, rb in loads)
    tags = [(0x7000000a, 0), (0x70000013, 1), (0x70000011, len(order) + 1), (0, 0)]
    parts = [(b'.dynstr', 0, names), (b'.dynsym', 0, table),
             (b'.hash', 0, struct.pack('<'+'I'*(len(order)+5), 2, len(order)+1, *([0]*(len(order)+3)))),
             (b'.got', got_virtual, b''.join(struct.pack('<Q', 0x100+i*8) for i in range(len(order)))),
             (b'.dynamic', 0, b''.join(struct.pack('<IIQ', tag, 0, value) for tag, value in tags)),
             (b'.text', 0x120000000, code)]
    out = bytearray(104 + 64 * len(parts)); struct.pack_into('<HHIQIHH', out, 0, 0x183, len(parts), 0, 0, 0, 80, 0x2007)
    struct.pack_into('<Q', out, 96, gp)
    for i, (name, virtual, raw) in enumerate(parts):
        start = len(out); out.extend(raw)
        struct.pack_into('<8sQQQQQQHHI', out, 104 + 64*i, name, virtual, virtual, len(raw), start, 0, 0, 0, 0, 0)
    return bytes(out)


@pytest.mark.parametrize('mode', range(5))
def test_modes_restore_exceptions_and_preserve_opcode(mode):
    data = object_file(); raw, stats = codec.transform(data, mode)
    assert stats['eligible_loads'] == 4 and stats['normalized_loads'] == 3
    assert codec.inverse(raw) == data
    assert codec.inverse(codec.transform(b'unsupported', mode)[0]) == b'unsupported'
    with pytest.raises(ValueError):
        codec.inverse(raw[:-1])


def test_duplicate_symbol_slots_are_literal():
    data = object_file((b'alpha', b'alpha'))
    raw, stats = codec.transform(data, 2)
    assert stats['normalized_loads'] == 0 and codec.inverse(raw) == data


def test_global_symbol_ids_are_stable_across_slot_permutations():
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode='w') as tar:
        for i, data in enumerate([object_file(), object_file((b'beta', b'alpha'))]):
            info = tarfile.TarInfo(str(i)); info.size = len(data); tar.addfile(info, io.BytesIO(data))
    data = stream.getvalue(); fields = codec.fields(data, 2)
    assert fields[0][1][(-32752)&65535] == fields[4][1][(-32744)&65535]
    raw, stats = codec.transform(data, 2)
    assert stats['normalized_loads'] == 6 and codec.inverse(raw) == data


def test_out_of_alphabet_index_rejected():
    data = object_file(); raw, _ = codec.transform(data, 2)
    n = int.from_bytes(raw[-13:-5], 'little'); start = len(raw)-13-n
    skeleton = bytearray(codec.parent.inverse(raw[:start])); where = codec.fields(data, 2)[0][0]
    struct.pack_into('<H', skeleton, where, 65535)
    corrupt, _ = codec.parent.transform(bytes(skeleton), 4)
    with pytest.raises(ValueError, match='outside reachable'):
        codec.inverse(corrupt + raw[start:])
