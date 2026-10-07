import pytest
from benchmarks import markup_prose as codec


@pytest.mark.parametrize('mode', (0, 1, 2))
def test_prose_order_tags_tabs_and_arbitrary_literals(mode):
    data = bytes(range(256)) + b'\t<p>Hello <i>world</i>.</p>\t<x a="\t">same</x>\r\n<bad' + b'<long a="' + b'x'*300 + b'">'
    raw, stats = codec.transform(data, mode)
    assert codec.inverse(raw) == data
    assert codec.inverse(codec.transform(b'', mode)[0]) == b''
    assert codec.inverse(codec.transform(b'plain\t\ttext', mode)[0]) == b'plain\t\ttext'
    if mode:
        skeleton = raw[:stats['skeleton_bytes']]
        assert b'Hello \tworld\t.' in skeleton
    with pytest.raises(ValueError):
        codec.inverse(raw[:-1])


def test_more_tags_than_dictionary_capacity_remain_literal():
    data = b''.join(b'<t'+str(i).encode()+b'>x\t' for i in range(4100))
    raw, stats = codec.transform(data, 1)
    assert stats['dictionary_entries'] == 4096 and codec.inverse(raw) == data


def test_unknown_identity_rejected():
    raw, _ = codec.transform(b'<p>x</p>', 1)
    n = int.from_bytes(raw[-13:-5], 'little'); start = len(raw)-13-n
    metadata = raw[start:-13]; size, p = codec.vdecode(metadata, 1); table, p = codec.read(metadata, p)
    metadata = metadata[:p] + codec.pack(b'\x7f\x01')
    bad = raw[:start] + metadata + len(metadata).to_bytes(8, 'little') + codec.MAGIC
    with pytest.raises(ValueError, match='outside dictionary'):
        codec.inverse(bad)
