#!/usr/bin/env python3
"""Frozen projection adapter: explicit byte raster -> existing CIXV1 mode 5.

No detection, portfolio search or PAQ fallback occurs in this path. The complete
projection frame is widened to uint16 pixels, padded with zeros, and compressed
using the unchanged volume codec. Every padding/dimension instruction is paid.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from benchmarks import volume_image_codec as volume
from benchmarks import hutter_wikipedia_projections as projections
from cix.multinomial import vdecode

MAGIC = b"CIXPROJ1"
HEADER = struct.Struct(">8sBQQI")
METADATA = b'{"cix":"V1m5","width":256,"effort":9}'.ljust(37, b' ')
WIDTH = 256
MODE = 5
EFFORT = 9
MAX_INPUT = 16 * 1024 * 1024
MAX_PROJECTED = MAX_INPUT + 4096


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for part in iter(lambda: f.read(1 << 20), b''):
            h.update(part)
    return h.hexdigest()


def check_runtime(manifest):
    record = json.loads(Path(manifest).read_text())
    for name, version in record['packages'].items():
        if importlib.metadata.version(name) != version:
            raise ValueError(f'frozen runtime version mismatch: {name}')
    for entry in record['files']:
        if digest(entry['path']) != entry['sha256']:
            raise ValueError(f'frozen runtime file mismatch: {entry["path"]}')


def raster(frame):
    if not 0 < len(frame) <= MAX_PROJECTED:
        raise ValueError('projection length outside frozen adapter bounds')
    height = (len(frame) + WIDTH - 1) // WIDTH
    pixels = np.zeros(height * WIDTH, dtype='<u2')
    pixels[:len(frame)] = np.frombuffer(frame, dtype=np.uint8)
    data = pixels.tobytes()
    return data, {'offset': 0, 'length': len(data), 'slice_height': height, 'width': WIDTH}


def inner_accounting(frame):
    if frame[:6] != volume.MAGIC + bytes((MODE,)):
        raise ValueError('frozen CIX volume mode mismatch')
    pos = 6
    fields = []
    for _ in range(8):
        value, pos = vdecode(frame, pos)
        fields.append(value)
    original, offset, length, z, height, width, metadata, payload = fields
    if offset != 0 or original != length or z != 1 or width != WIDTH or length != height * WIDTH * 2:
        raise ValueError('frozen raster dimensions mismatch')
    if original > 2 * (MAX_PROJECTED + WIDTH) or pos + 4 + metadata + payload != len(frame):
        raise ValueError('frozen inner size mismatch')
    return {'inner_framing_bytes': pos + 4, 'inner_metadata_bytes': metadata,
            'jxl_payload_bytes': payload, 'inner_total_bytes': len(frame),
            'raster_bytes': length, 'width': width, 'height': height, 'z': z,
            'actual_coding_path': 'CIXV1 mode5 -> lossless JPEG XL effort9 single-thread',
            'paq_fallback': False}


def encode(source, archive, recipe, runtime_manifest):
    check_runtime(runtime_manifest)
    raw = Path(source).read_bytes()
    if len(raw) > MAX_INPUT:
        raise ValueError('source outside bounded projection limit')
    projected = projections.project(raw, recipe)
    matrix, region = raster(projected)
    inner = volume.encode(matrix, region, mode=MODE, effort=EFFORT)
    accounting = inner_accounting(inner)
    result = HEADER.pack(MAGIC, projections.RECIPES[recipe], len(raw), len(projected), len(METADATA)) + METADATA + inner
    Path(archive).write_bytes(result)
    _, _, _, projection_payload = projections._unframe(projected)
    return {'recipe': recipe, 'original_bytes': len(raw), 'projected_bytes': len(projected),
            'projection_framing_bytes_before_backend': len(projected) - len(projection_payload),
            'projection_payload_bytes_before_backend': len(projection_payload),
            'padding_pixels': len(matrix) // 2 - len(projected),
            'outer_framing_bytes': HEADER.size, 'outer_metadata_bytes': len(METADATA),
            'total_bytes': len(result), 'archive_sha256': digest(archive),
            **accounting}


def decode(archive, output, runtime_manifest):
    check_runtime(runtime_manifest)
    blob = Path(archive).read_bytes()
    if len(blob) < HEADER.size + len(METADATA):
        raise ValueError('truncated projection archive')
    magic, recipe, original, projected, meta = HEADER.unpack_from(blob)
    if (magic != MAGIC or recipe not in projections.RECIPE_BY_ID or original > MAX_INPUT
            or not 0 < projected <= MAX_PROJECTED or meta != len(METADATA)
            or blob[HEADER.size:HEADER.size + meta] != METADATA):
        raise ValueError('invalid projection archive header')
    inner = blob[HEADER.size + meta:]
    info = inner_accounting(inner)
    if info['height'] != (projected + WIDTH - 1) // WIDTH:
        raise ValueError('noncanonical raster padding')
    pixels = np.frombuffer(volume.decode(inner), dtype='<u2')
    if np.any(pixels[:projected] > 255) or np.any(pixels[projected:]):
        raise ValueError('invalid raster byte or padding')
    frame = pixels[:projected].astype(np.uint8).tobytes()
    if projections._unframe(frame)[0] != projections.RECIPE_BY_ID[recipe]:
        raise ValueError('projection recipe mismatch')
    raw = projections.restore(frame)
    if len(raw) != original:
        raise ValueError('restored source size mismatch')
    Path(output).write_bytes(raw)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('encode', 'decode'))
    parser.add_argument('input', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--recipe', choices=tuple(projections.RECIPES), default='p1')
    parser.add_argument('--runtime-manifest', type=Path, required=True)
    args = parser.parse_args()
    if args.operation == 'encode':
        print(json.dumps(encode(args.input, args.output, args.recipe, args.runtime_manifest), sort_keys=True))
    else:
        decode(args.input, args.output, args.runtime_manifest)


if __name__ == '__main__':
    main()
