from runtime.cix_runtime.legacy import image_grid
from runtime.cix_runtime.legacy import spatial_image_codec as spatial
from runtime.cix_runtime.legacy import grid_conditional, grid_grouped
from runtime.cix_runtime.legacy import record_float_grid


def _dicom_volume():
    def tag(group, element, value):
        return group.to_bytes(2, "little") + element.to_bytes(2, "little") + len(value).to_bytes(4, "little") + value
    pixels = bytes(2 * 2 * 2 * 2)  # two 2x2 16-bit slices
    return (tag(0x28, 0x10, (2).to_bytes(2, "little"))
            + tag(0x28, 0x11, (2).to_bytes(2, "little"))
            + tag(0x28, 0x100, (16).to_bytes(2, "little"))
            + tag(0x7FE0, 0x0010, pixels))


def test_catalog_uses_validated_dicom_not_path_or_name():
    candidates, diagnostics = image_grid.catalog(_dicom_volume())
    assert any(x.id.startswith("volume-mode3-effort10") for x in candidates)
    shared = next(x for x in candidates if x.id == "volume-mode3-effort10-shared-cixi2")
    assert callable(shared.encode_with_report)
    assert shared.parameters["logical_formats"] == ["CIXV1", "CIXI2"]
    assert diagnostics[0]["eligible"]


def test_raster_header_is_not_an_automatic_route_without_paid_layout_proof():
    assert spatial.regions(bytes(240)) == []
    candidates, diagnostics = image_grid.catalog(bytes(240))
    assert not candidates
    assert diagnostics[0]["eligible"] is False


def test_decoder_table_uses_exact_five_byte_magics():
    assert all(len(magic) == 5 for magic in image_grid.DECODERS)
    assert {b"CIXI\x01", b"CIXV\x01", b"CIXI\x02", b"CIXB\x1e"} <= set(image_grid.DECODERS)
    assert b"CIXB\x21" in image_grid.DECODERS


def test_wcstools_recognizer_requires_valid_count_and_exact_extent():
    import struct
    header = struct.pack("<7i", 0, 0, 2, 0, 1, 1, 28)
    assert record_float_grid.recognizes(header + bytes(56))
    assert not record_float_grid.recognizes(header + bytes(55))
    assert not record_float_grid.recognizes(header + bytes(57))
    bad_count = struct.pack("<7i", 0, 0, 8_000_001, 0, 1, 1, 28)
    assert not record_float_grid.recognizes(bad_count + bytes(56))


def test_grouped_transform_matches_historical_source_fixture():
    """Exact extraction parity on a tiny, independently generated schema fixture."""
    import struct
    from benchmarks import grid_conditional_corrections as historical
    count = 32
    data = struct.pack("<7i", 0, 1, count, 0, 1, 1, 28)
    data += b"".join(struct.pack("<dd2shff", i / 100.0, i / 200.0,
                                b"A0", i, i / 1000.0, -i / 2000.0)
                     for i in range(count))
    actual, _ = grid_conditional.transform(data, 3, 0)
    expected, _ = historical.transform(data, 3, 0)
    assert actual == expected
    assert grid_grouped.MAGIC == b"CIXB\x21"
