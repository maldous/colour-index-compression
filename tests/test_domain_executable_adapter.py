import struct

import pytest

from benchmarks import domain_executable_adapter as adapter


def elf_fixture(addends=(0x2010,)):
    data = bytearray(768)
    data[:16] = b"\x7fELF" + bytes([2, 1, 1]) + bytes(9)
    struct.pack_into("<H", data, 18, 62)
    struct.pack_into("<Q", data, 40, 64)
    struct.pack_into("<HHH", data, 58, 64, 4, 0)
    def section(index, kind, address, offset, size, entsize=0):
        struct.pack_into("<IIQQQQIIQQ", data, 64 + index * 64, 0, kind, 0, address, offset, size, 0, 0, 8, entsize)
    section(1, 1, 0x1000, 0, 0x100)
    section(2, 1, 0x2000, 0, 0x100)
    section(3, 4, 0, 320, 24 * len(addends), 24)
    for index, addend in enumerate(addends):
        struct.pack_into("<QQq", data, 320 + index * 24, 0x4000 + index * 8, 8, addend)
    return bytes(data)


def test_address_frame_round_trip_and_coverage():
    data = elf_fixture()
    row = adapter.inspect(data)
    assert row["relative_relocations"] == row["normalized_addends"] == 1
    frame = adapter.encode(data, "address")
    assert adapter.decode(frame) == data
    assert len(frame) > len(data)


def test_packed_ids_round_trip_for_zero_one_and_multiple_candidates():
    for addends in ((0x9000,), (0x2010,), (0x2010, 0x1010, 0x2020)):
        data = elf_fixture(addends)
        packed = adapter.encode(data, "address-packed")
        assert adapter.decode(packed) == data
    data = elf_fixture((0x2010, 0x1010, 0x2020))
    assert len(adapter.encode(data, "address-packed")) < len(adapter.encode(data, "address"))


def test_raw_frame_is_complete_and_rejects_tampered_membership():
    data = elf_fixture()
    frame = adapter.encode(data, "raw")
    assert adapter.decode(frame) == data
    tampered = bytearray(frame)
    tampered[-1] |= 1
    with pytest.raises(ValueError):
        adapter.decode(bytes(tampered))


def test_unmapped_addend_is_preserved_and_unsupported_elf_rejected():
    data = elf_fixture((0x9000,))
    assert adapter.inspect(data)["normalized_addends"] == 0
    assert adapter.decode(adapter.encode(data, "address")) == data
    with pytest.raises(ValueError, match="ELF magic"):
        adapter.encode(b"not an elf")


def test_packed_rank_rejects_malformed_fixed_width_metadata():
    frame = adapter.encode(elf_fixture((0x2010, 0x1010)), "address-packed")
    with pytest.raises(ValueError):
        adapter.decode(frame[:-1])
