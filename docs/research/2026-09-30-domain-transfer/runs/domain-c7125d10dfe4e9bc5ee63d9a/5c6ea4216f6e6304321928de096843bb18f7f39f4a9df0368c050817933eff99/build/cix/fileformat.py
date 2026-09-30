"""File wrapper around the open-ended CIX stream.

The payload can be emitted incrementally. Original filename metadata lives at the very
end so it never has to precede the compressed stream.
"""

from __future__ import annotations

import os
import struct
from pathlib import Path

from .multinomial import StreamConfig, StreamDecoder, StreamEncoder

FILE_MAGIC = b"CIXF1"
IO_CHUNK = 1 << 20


def _footer(name: str) -> bytes:
    metadata = Path(name).name.encode("utf-8")
    return metadata + struct.pack("<I", len(metadata)) + FILE_MAGIC


def split_file_wrapper(blob: bytes) -> tuple[bytes, str]:
    if len(blob) < 9 or blob[-5:] != FILE_MAGIC:
        raise ValueError("not a CIX file wrapper")
    metadata_len = struct.unpack_from("<I", blob, len(blob) - 9)[0]
    metadata_start = len(blob) - 9 - metadata_len
    if metadata_start < 0:
        raise ValueError("invalid CIX file metadata length")
    name = blob[metadata_start : metadata_start + metadata_len].decode("utf-8")
    return blob[:metadata_start], Path(name).name


def compress_file(
    source: str | os.PathLike[str],
    destination: str | os.PathLike[str] | None = None,
    *,
    config: StreamConfig | None = None,
) -> Path:
    source_path = Path(source)
    if destination is None:
        destination_path = source_path.with_suffix(source_path.suffix + ".cix")
    else:
        destination_path = Path(destination)

    encoder = StreamEncoder(config or StreamConfig())

    with source_path.open("rb") as src, destination_path.open("wb") as dst:
        while True:
            chunk = src.read(IO_CHUNK)
            if not chunk:
                break
            dst.write(encoder.feed(chunk))
        dst.write(encoder.finish())
        dst.write(_footer(source_path.name))

    return destination_path


def decompress_file(
    source: str | os.PathLike[str],
    destination: str | os.PathLike[str] | None = None,
) -> Path:
    source_path = Path(source)

    with source_path.open("rb") as src:
        src.seek(0, os.SEEK_END)
        total_size = src.tell()
        if total_size < 9:
            raise ValueError("file too small to be CIX")

        src.seek(total_size - 9)
        metadata_len = struct.unpack("<I", src.read(4))[0]
        if src.read(5) != FILE_MAGIC:
            raise ValueError("not a CIX file wrapper")

        metadata_start = total_size - 9 - metadata_len
        if metadata_start < 0:
            raise ValueError("invalid CIX metadata")
        src.seek(metadata_start)
        original_name = Path(src.read(metadata_len).decode("utf-8")).name

        if destination is None:
            destination_path = source_path.with_name(original_name)
        else:
            destination_path = Path(destination)

        decoder = StreamDecoder()
        src.seek(0)
        remaining = metadata_start
        with destination_path.open("wb") as dst:
            while remaining:
                chunk = src.read(min(IO_CHUNK, remaining))
                if not chunk:
                    raise ValueError("truncated CIX payload")
                remaining -= len(chunk)
                dst.write(decoder.feed(chunk))
            decoder.finish()

    return destination_path
