import random
import struct
import zlib
from pathlib import Path
import pytest
pytest.importorskip('imagecodecs')
from cix.multinomial import vencode
from benchmarks import competitive_codec as codec


def legacy_raw(data):
    return b'CIXT\x01'+vencode(len(data))+vencode(262144)+zlib.crc32(data).to_bytes(4,'big')+(vencode(len(data)+1)+b'\0'+data if data else b'')


def test_physical_selection_raw_and_empty():
    for data in (b'',random.Random(53).randbytes(2000)):
        result,record=codec.encode(data,legacy_cache=legacy_raw(data))
        assert len(result)==min(r['size'] for r in record['trials'])
        assert codec.decode(result)==data


def test_spatial_selection_self_describes():
    header=bytearray(240);header[4:10]=bytes.fromhex('004000200010')
    data=bytes(header)+b'\x00\x01'*2048
    blob,record=codec.encode(data,legacy_cache=legacy_raw(data))
    assert record['selected'].startswith('image-')
    assert len(blob)==min(r['size'] for r in record['trials'])
    # Decoder sees neither the original data nor encoder's region metadata.
    assert codec.decode(blob)==data


def test_paq_header_contains_version_without_overhead():
    path=Path('results/leaderboard/paq-v215-smoke/xml-prefix-64k/stream.paq8px215')
    if not path.exists():pytest.skip('local PAQ smoke artifact unavailable')
    original=path.read_bytes()
    for version in ('v215','v216'):
        frame=codec.wrap_paq(original,version)
        assert len(frame)==len(original)
        assert codec.unwrap_paq(frame)==(version,original)


def test_float_grid_selected_and_independently_decoded():
    data=struct.pack('<7i',0,1,80,0,1,1,28)+b'\0'*28*80
    blob,record=codec.encode(data,legacy_cache=legacy_raw(data))
    assert record['selected'].startswith('float-grid-')
    assert len(blob)==min(row['size'] for row in record['trials'])
    assert codec.decode(blob)==data
    assert not codec.has_fixed_star_records(data[:-1])
    assert not codec.has_fixed_star_records(data[:24]+struct.pack('<i',27)+data[28:])


def test_reject_ambiguous_and_invalid_frames():
    for frame in (b'',b'paq8px1234',b'CIXP\x01\x03234',b'CIXU\x01\x03\0\0\0\0no'):
        with pytest.raises(ValueError):codec.decode(frame)
