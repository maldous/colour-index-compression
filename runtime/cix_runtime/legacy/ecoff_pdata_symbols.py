"""Compose the winning regional procedure predictor with shared-symbol loads.

Predict each address word from the previous decoded word in its table. Modulo
32-bit residuals preserve flags, wraparound and nonmonotone exceptional data.
The procedure table's other word remains unchanged. Test both layers together;
their byte savings are never assumed additive.
"""
import struct
from . import ecoff_symbol_loads as parent, ecoff_pdata as procedure

MAGIC = b'ECPD2'


def transform(data, mode=1):
    if mode not in (0, 1):
        raise ValueError('invalid combined procedure mode')
    skeleton, _ = parent.transform(data, 2)
    out = bytearray(skeleton); descriptors = procedure.tables(skeleton)
    if mode:
        for start, n in descriptors:
            previous = 0
            for i in range(n):
                word = struct.unpack_from('<I', skeleton, start + 8 * i)[0]
                struct.pack_into('<I', out, start + 8 * i, (word - previous) & 0xffffffff)
                previous = word
    return bytes(out) + bytes([mode]) + MAGIC, {
        "mode": mode,
        "original_bytes": len(data),
        "transformed_bytes": len(out) + 6,
        "tables": len(descriptors),
        "predicted_addresses": sum(count for _, count in descriptors),
        "constraint_metadata_bytes": 6,
    }


def inverse(raw):
    if len(raw) < 6 or raw[-5:] != MAGIC or raw[-6] > 1:
        raise ValueError('invalid combined procedure trailer')
    mode = raw[-6]; out = bytearray(raw[:-6])
    if mode:
        for start, n in procedure.tables(out):
            previous = 0
            for i in range(n):
                word = (struct.unpack_from('<I', out, start + 8 * i)[0] + previous) & 0xffffffff
                struct.pack_into('<I', out, start + 8 * i, word); previous = word
    return parent.inverse(bytes(out))
