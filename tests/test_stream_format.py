import os
from pathlib import Path

from cix.fileformat import compress_file, decompress_file
from cix.multinomial import (
    ContextModel,
    MODE_REFERENCE,
    StreamConfig,
    StreamDecoder,
    StreamEncoder,
    TYPECLASS_RANGE,
    compress,
    decode_type_class,
    decompress,
    encode_type_class,
    vdecode,
)


def test_large_multinomial_uses_range_realization_and_round_trips():
    data = (bytes(range(32)) * 100) + (b"A" * 300)
    encoded = encode_type_class(data)

    # Skip source length, active alphabet metadata and histogram metadata by decoding
    # once; the important assertion is physical round-trip on a block above the
    # range-coder threshold. TYPECLASS_RANGE is also required to be present.
    restored, consumed = decode_type_class(encoded)
    assert restored == data
    assert consumed == len(encoded)
    assert TYPECLASS_RANGE in encoded


def test_custom_history_window_is_self_describing():
    prefix = (b"0123456789abcdef" * 1024)
    data = prefix + prefix + prefix

    config = StreamConfig(
        min_block=4096,
        max_block=8192,
        probe_stride=1024,
        history_bytes=8192,
        lz_window_bytes=8192,
        enable_bwt=False,
        enable_chains=False,
        context_models=(ContextModel(1, 8), ContextModel(2, 8)),
    )
    blob = compress(data, config)

    # Decoder is deliberately constructed without knowing the encoder config.
    assert decompress(blob) == data


def test_stream_decoder_handles_single_byte_packets():
    data = (
        os.urandom(512)
        + (b"ABCDEF123456" * 120)
        + b"".join(i.to_bytes(4, "little") for i in range(300))
    )
    config = StreamConfig(
        min_block=1024,
        max_block=4096,
        probe_stride=512,
        history_bytes=16384,
        lz_window_bytes=16384,
        enable_lz=False,
        enable_bwt=False,
        enable_transforms=False,
        enable_numeric=False,
        enable_bitplanes=False,
        enable_chains=False,
        enable_sparse=False,
        enable_runs=False,
        enable_adaptive=False,
        enable_stateful=False,
        context_models=(ContextModel(1, 8), ContextModel(2, 8)),
    )

    encoder = StreamEncoder(config)
    blob = encoder.feed(data) + encoder.finish()

    decoder = StreamDecoder()
    restored = bytearray()
    for byte in blob:
        restored += decoder.feed(bytes((byte,)))
    decoder.finish()
    assert bytes(restored) == data


def test_content_defined_duplicate_block_can_use_reference():
    unit = (
        b"this is an exactly repeated content-defined region;"
        b"it should be cheap to reference once seen.\n"
    ) * 80
    data = unit + unit + unit

    config = StreamConfig(
        min_block=len(unit),
        max_block=len(unit),
        probe_stride=len(unit),
        chunk_mode="fixed",
        history_bytes=len(unit) * 2,
        lz_window_bytes=len(unit) * 2,
        enable_lz=False,
        enable_bwt=False,
        enable_transforms=False,
        enable_numeric=False,
        enable_bitplanes=False,
        enable_chains=False,
        enable_dedup=True,
        dedup_blocks=8,
        context_models=(),
    )

    encoder = StreamEncoder(config)
    blob = encoder.feed(data) + encoder.finish()
    assert decompress(blob) == data
    assert any(
        description.startswith("dedup-block-distance-")
        for description in encoder.block_descriptions
    )
    assert bytes((MODE_REFERENCE,)) in blob


def test_file_wrapper_restores_original_basename(tmp_path: Path):
    source = tmp_path / "payload.json"
    source.write_bytes(
        (b'{"student":"alice","active":true}\n' * 200)
        + os.urandom(512)
    )

    compressed = compress_file(
        source,
        config=StreamConfig(
            min_block=512,
            max_block=2048,
            probe_stride=256,
            history_bytes=4096,
            lz_window_bytes=4096,
            enable_chains=False,
        ),
    )
    original = source.read_bytes()
    source.unlink()

    restored = decompress_file(compressed)
    assert restored.name == "payload.json"
    assert restored.read_bytes() == original
