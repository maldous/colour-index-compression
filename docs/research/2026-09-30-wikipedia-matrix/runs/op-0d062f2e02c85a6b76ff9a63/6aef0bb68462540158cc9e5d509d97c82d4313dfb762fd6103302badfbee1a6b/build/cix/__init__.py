"""Colour Index Compression research package."""

from .multinomial import (
    ContextModel,
    StreamConfig,
    StreamEncoder,
    StreamDecoder,
    compress,
    decompress,
    encode_type_class,
    decode_type_class,
)

__all__ = [
    "ContextModel",
    "StreamConfig",
    "StreamEncoder",
    "StreamDecoder",
    "compress",
    "decompress",
    "encode_type_class",
    "decode_type_class",
]
