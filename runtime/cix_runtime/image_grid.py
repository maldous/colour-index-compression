"""Automatic image, volume, and grid candidate catalogue."""
from __future__ import annotations

import hashlib

from .legacy import grid_backend
from .legacy import grid_conditional
from .legacy import grid_context
from .legacy import grid_feedback
from .legacy import grid_grouped
from .legacy import grid_interval
from .legacy import multiscale_volume as multi
from .legacy import record_float_grid as grid
from .legacy import spatial_image_codec as spatial
from .legacy import volume_image_codec as volume
from .model import Candidate

MIB = 1 << 20
PAQ_GRID_MEMORY = 4_500_000_000


def _decode(fn):
    return lambda frame, max_output_bytes, memory_bytes: fn(
        frame, max_output_bytes, memory_bytes
    )


def _bounded_legacy(fn):
    def decode(frame, max_output_bytes, memory_bytes):
        data = fn(frame)
        if len(data) > max_output_bytes or len(data) > memory_bytes:
            raise ValueError("decoded output exceeds bound")
        return data

    return decode


def _framed_legacy(fn, length_offset):
    def decode(frame, max_output_bytes, memory_bytes):
        n, _ = multi.vdecode(frame, length_offset)
        if n > max_output_bytes or n > memory_bytes:
            raise ValueError("legacy grid output exceeds bound")
        return _bounded_legacy(fn)(frame, max_output_bytes, memory_bytes)

    return decode


DECODERS = {
    spatial.MAGIC: _decode(spatial.decode),
    volume.MAGIC: _decode(volume.decode),
    multi.MAGIC: _decode(multi.decode),
    grid.MAGIC: _framed_legacy(grid.decode, 6),
    grid_feedback.MAGIC: _framed_legacy(grid_feedback.decode, 6),
    grid_interval.MAGIC: _framed_legacy(grid_interval.decode, 5),
    grid_context.MAGIC: _framed_legacy(grid_context.decode, 5),
    grid_conditional.MAGIC: _framed_legacy(grid_conditional.decode, 5),
    grid_backend.MAGIC: grid_backend.decode,
    grid_grouped.MAGIC: grid_grouped.decode,
}


def _candidate(ident, family, encoder, memory, parameters):
    return Candidate(
        ident,
        family,
        encoder,
        memory,
        memory,
        parameters=parameters,
    )


def _mode3_identity(data, region):
    """Encode current bytes once and construct the equivalent CIXI2 envelope."""
    cixv = volume.encode(data, region, 3, 10)
    pos = 6
    fields = []
    for _ in range(8):
        value, pos = multi.vdecode(cixv, pos)
        fields.append(value)
    original, offset, length, z, height, width, meta_size, payload_size = fields
    if cixv[:5] != volume.MAGIC or cixv[5] != 3 or length != z * height * width * 2:
        raise ValueError("unexpected mode-3 frame")
    crc = cixv[pos : pos + 4]
    pos += 4
    metadata = cixv[pos : pos + meta_size]
    payload = cixv[pos + meta_size :]
    if len(crc) != 4 or len(metadata) != meta_size or len(payload) != payload_size:
        raise ValueError("invalid mode-3 frame bounds")
    cixi = (
        multi.MAGIC
        + b"\0\0\0"
        + b"".join(
            multi.vencode(value)
            for value in (original, offset, z, height, width, meta_size)
        )
        + crc
        + metadata
        + multi.vencode(payload_size)
        + payload
    )
    selected, selected_format = (
        (cixi, "CIXI2") if len(cixi) < len(cixv) else (cixv, "CIXV1")
    )
    return selected, {
        "logical_candidate_bytes": {"CIXV1": len(cixv), "CIXI2": len(cixi)},
        "selected_format": selected_format,
        "payload_sha256": hashlib.sha256(payload).hexdigest(),
        "shared_current_encode": True,
    }


def _shared_identity_candidate(region, memory):
    cache = {"data": None, "result": None}

    def report(data):
        if cache["data"] is not data:
            cache["data"] = data
            cache["result"] = _mode3_identity(data, region)
        return cache["result"]

    candidate = _candidate(
        "volume-mode3-effort10-shared-cixi2",
        "volume-multiscale-identity",
        lambda data: report(data)[0],
        memory,
        {
            "mode": 3,
            "effort": 10,
            "backend": "jpegxl",
            "logical_formats": ["CIXV1", "CIXI2"],
            "current_data_only": True,
        },
    )
    object.__setattr__(candidate, "encode_with_report", report)
    return candidate


def catalog(data: bytes) -> tuple[list[Candidate], list[dict]]:
    """Return candidates admitted solely from validated supplied bytes."""
    candidates = []
    diagnostics = []
    regions = spatial.regions(data)

    if grid.recognizes(data):
        grid_memory = PAQ_GRID_MEMORY + 8 * len(data)
        candidates.append(
            _candidate(
                "grouped-prediction-context3-paq-v215-8",
                "grouped-grid",
                lambda source: grid_grouped.encode(source, 3, "-8")[0],
                grid_memory,
                {
                    "context": 3,
                    "backend": "paq-v215",
                    "options": "-8",
                    "format": "CIXB21",
                },
            )
        )
        for mode in (1, 2, 3, 4):
            candidates.append(
                _candidate(
                    f"bounded-grid-mode{mode}-paq-v215-8",
                    "bounded-grid",
                    lambda source, mode=mode: grid_backend.encode(
                        source, mode, 1, "-8"
                    )[0],
                    grid_memory,
                    {
                        "mode": mode,
                        "backend": "paq-v215",
                        "options": "-8",
                        "format": "CIXB1E",
                    },
                )
            )
        diagnostics.append(
            {
                "family": "grouped-grid",
                "eligible": True,
                "reason": "validated WCSTools seven-int/28-byte-record subset",
            }
        )

    if not regions:
        if candidates:
            return candidates, diagnostics
        return [], [
            {
                "family": "image-grid",
                "eligible": False,
                "reason": "no validated DICOM region; raster-240 declined pending paid-layout proof",
            }
        ]

    for index, region in enumerate(regions):
        for backend, effort in (("jxl", 7), ("jxl", 10), ("jls", 0), ("j2k", 0)):
            candidates.append(
                _candidate(
                    f"image-{backend}-effort{effort}-{index}",
                    "spatial-image",
                    lambda source, region=region, backend=backend, effort=effort:
                    spatial.encode_region(source, region, backend, effort),
                    1024 * MIB,
                    {
                        "region": region,
                        "backend": backend,
                        "effort": effort,
                        "format": "CIXI1",
                    },
                )
            )
        if region["height"] <= region["slice_height"]:
            continue
        for mode in range(6):
            candidates.append(
                _candidate(
                    f"volume-mode{mode}-effort9-{index}",
                    "volume",
                    lambda source, region=region, mode=mode: volume.encode(
                        source, region, mode, 9
                    ),
                    1536 * MIB,
                    {
                        "region": region,
                        "mode": mode,
                        "effort": 9,
                        "backend": "jpegxl",
                        "format": "CIXV1",
                    },
                )
            )
        candidates.append(_shared_identity_candidate(region, 1536 * MIB))

    diagnostics.append(
        {
            "family": "image-grid",
            "eligible": True,
            "reason": "input-derived implicit-VR DICOM region",
            "regions": len(regions),
        }
    )
    return candidates, diagnostics
