from runtime.cix_runtime import specialized


def test_catalog_is_total_on_arbitrary_bytes():
    candidates, diagnostics = specialized.catalog(b"\x03\x00\x00bad")
    assert isinstance(candidates, list)
    assert diagnostics
    assert not candidates


def test_fixed_star_recognizer_requires_full_extent():
    data = (0).to_bytes(8, "little", signed=True) + (1).to_bytes(4, "little", signed=True) * 5
    from runtime.cix_runtime.legacy.record_float_grid import recognizes
    assert recognizes(data) is False
    candidates, _ = specialized.catalog(data)
    assert not any(c.family in {"grid", "grouped-grid"} for c in candidates)


def test_extracted_legacy_magics_are_recognized_for_dispatch():
    assert specialized.recognizes_magic(b"CIXB\x1d")
    assert specialized.recognizes_magic(b"CIXB\x13")


def _embedded_ecoff_fixture() -> bytes:
    """A TAR member forces locator offsets to be nonzero and input-derived."""
    import io
    import struct
    import tarfile
    names = b"\0alpha\0beta\0"
    virtual = 0x120002000
    symbols = b"".join(struct.pack("<IIQIBBH", offset, 0, value, 0, 0x12, 0, 0xff01)
                       for offset, value in zip((0, 1, 7), (0, 99, 42)))
    relocations = b"".join(struct.pack("<QII", virtual + 8 * index, (symbol << 8) | 2, 0)
                            for index, symbol in enumerate((1, 2)))
    parts = ((b".dynstr", 0, names), (b".dynsym", 0, symbols),
             (b".hash", 0, struct.pack("<7I", 2, 3, 0, 0, 0, 0, 0)),
             (b".rdata", virtual, struct.pack("<2Q", 99, 42)),
             (b".rel.dyn", 0, relocations))
    obj = bytearray(104 + 64 * len(parts))
    struct.pack_into("<HHIQIHH", obj, 0, 0x183, len(parts), 0, 0, 0, 80, 0x2007)
    for index, (name, address, raw) in enumerate(parts):
        offset = len(obj)
        obj.extend(raw)
        struct.pack_into("<8sQQQQQQHHI", obj, 104 + 64 * index, name, address, address,
                         len(raw), offset, 0, 0, 0, 0, 0)
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w") as archive:
        info = tarfile.TarInfo("nested-object")
        info.size = len(obj)
        archive.addfile(info, io.BytesIO(obj))
    return stream.getvalue() + b"ordinary trailing bytes"


def test_catalog_admits_embedded_ecoff_locator_without_outer_magic():
    candidates, diagnostics = specialized.catalog(_embedded_ecoff_fixture())
    pointer = next(row for row in diagnostics if row["family"] == "executable-pointer")
    assert pointer["eligible"]
    assert any(candidate.id == "ecoff-pointer-mode5-paq" for candidate in candidates)


def _embedded_ecoff_section_fixture() -> bytes:
    """A valid section/function object carried in a TAR member, not an ELF."""
    import io
    import struct
    import tarfile

    text = 0x120000000
    rdata = 0x200000000
    names = b"\0.text\0.rdata\0funcA\0funcB\0"
    symbols = b"".join(
        struct.pack("<IIQIBBH", offset, 0, value, 0, 0x12, 0, 0xff01)
        for offset, value in ((0, 0), (1, text + 4), (7, rdata), (14, text + 8), (20, text + 16))
    )
    targets = (text + 8, text + 12, text + 3, (1 << 64) - 1, rdata + 16, rdata + 8)
    relocations = b"".join(
        struct.pack("<QII", rdata + index * 8, (symbol << 8) | 2, 0)
        for index, symbol in enumerate((1, 1, 1, 1, 2, 2))
    )
    parts = (
        (b".dynstr", 0, names),
        (b".dynsym", 0, symbols),
        (b".hash", 0, struct.pack("<9I", 2, 5, 0, 0, 0, 0, 0, 0, 0)),
        (b".pdata", text - 1024, struct.pack("<6i", 1024, 0, 1032, 0, 1040, 0)),
        (b".text", text, bytes(32)),
        (b".rdata", rdata, struct.pack("<6Q", *targets)),
        (b".rel.dyn", 0, relocations),
    )
    obj = bytearray(104 + 64 * len(parts))
    struct.pack_into("<HHIQIHH", obj, 0, 0x183, len(parts), 0, 0, 0, 80, 0x2007)
    for index, (name, address, raw) in enumerate(parts):
        offset = len(obj)
        obj.extend(raw)
        struct.pack_into("<8sQQQQQQHHI", obj, 104 + 64 * index, name, 0, address,
                         len(raw), offset, 0, 0, 0, 0, 0)
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w") as archive:
        entry = tarfile.TarInfo("nested-section-object")
        entry.size = len(obj)
        archive.addfile(entry, io.BytesIO(obj))
    return stream.getvalue() + b"unrelated trailer"


def test_section_pointer_carrier_admits_joint_discount_without_elf_magic():
    source = _embedded_ecoff_section_fixture()
    assert not source.startswith(b"\x7fELF")
    candidates, diagnostics = specialized.catalog(source)
    section = next(row for row in diagnostics if row["family"] == "executable-section")
    assert section["eligible"]
    assert any(candidate.id == "executable-joint-discount" for candidate in candidates)
