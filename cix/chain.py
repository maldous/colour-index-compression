"""Short beam of reversible transform -> native CIX model chains."""

from __future__ import annotations

from .bitplanes import decode_bitplanes, encode_bitplanes
from .bwt import decode_bwt_block, encode_bwt_block
from .lz import decode_lz_block, encode_lz_block
from .multinomial import (
    ContextModel,
    decode_context_type_classes,
    decode_type_class_known_n,
    encode_context_type_classes,
    encode_type_class_known_n,
)
from .transforms import SPEC_BY_ID, apply_transform, invert_transform

CHAIN_VERSION = 1
INNER_MULTINOMIAL = 1
INNER_CONTEXT = 2
INNER_LZ = 3
INNER_BWT = 4
INNER_BITPLANE = 5

# High-value transforms worth chaining with a second model. Direct transform mode still
# tries the full transform portfolio independently.
CHAIN_SPEC_IDS = (12, 13, 16, 20, 21, 29, 30, 31, 32, 33)


def encode_chain_block(
    data: bytes,
    *,
    context_models: tuple[ContextModel, ...] = (),
) -> tuple[bytes, str]:
    candidates: list[tuple[bytes, str]] = []

    for spec_id in CHAIN_SPEC_IDS:
        spec = SPEC_BY_ID[spec_id]
        transformed = apply_transform(data, spec)

        plain = encode_type_class_known_n(transformed)
        candidates.append(
            (
                bytes((CHAIN_VERSION, spec.id, INNER_MULTINOMIAL)) + plain,
                f"{spec.name}->multinomial",
            )
        )

        for model in context_models[:5]:
            payload = encode_context_type_classes(
                transformed,
                order=model.order,
                bucket_bits=model.bucket_bits,
            )
            candidates.append(
                (
                    bytes((CHAIN_VERSION, spec.id, INNER_CONTEXT)) + payload,
                    f"{spec.name}->context-o{model.order}-b{model.bucket_bits}",
                )
            )

        if len(transformed) >= 16:
            try:
                payload, description = encode_lz_block(
                    transformed,
                    context_models=context_models[:4],
                    window=min(1 << 20, max(4096, len(transformed) * 4)),
                    chain=32,
                )
                candidates.append(
                    (
                        bytes((CHAIN_VERSION, spec.id, INNER_LZ)) + payload,
                        f"{spec.name}->{description}",
                    )
                )
            except Exception:
                pass

        if 32 <= len(transformed) <= 65536:
            try:
                payload, description = encode_bwt_block(transformed)
                candidates.append(
                    (
                        bytes((CHAIN_VERSION, spec.id, INNER_BWT)) + payload,
                        f"{spec.name}->{description}",
                    )
                )
            except Exception:
                pass

        if len(transformed) >= 2:
            try:
                payload, description = encode_bitplanes(transformed)
                candidates.append(
                    (
                        bytes((CHAIN_VERSION, spec.id, INNER_BITPLANE)) + payload,
                        f"{spec.name}->{description}",
                    )
                )
            except Exception:
                pass

    if not candidates:
        raise ValueError("no chain candidates")
    return min(candidates, key=lambda item: len(item[0]))


def decode_chain_block(blob: bytes, *, source_length: int) -> bytes:
    if len(blob) < 3 or blob[0] != CHAIN_VERSION:
        raise ValueError("unknown transform-chain version")

    spec = SPEC_BY_ID.get(blob[1])
    if spec is None:
        raise ValueError("unknown transform-chain transform")

    inner_mode = blob[2]
    payload = blob[3:]

    if inner_mode == INNER_MULTINOMIAL:
        transformed, used = decode_type_class_known_n(
            payload, 0, source_length
        )
        if used != len(payload):
            raise ValueError("unused chained multinomial bytes")

    elif inner_mode == INNER_CONTEXT:
        transformed, used = decode_context_type_classes(
            payload, 0, source_length
        )
        if used != len(payload):
            raise ValueError("unused chained context bytes")

    elif inner_mode == INNER_LZ:
        transformed = decode_lz_block(
            payload,
            source_length=source_length,
        )

    elif inner_mode == INNER_BWT:
        transformed = decode_bwt_block(
            payload,
            source_length=source_length,
        )

    elif inner_mode == INNER_BITPLANE:
        transformed = decode_bitplanes(
            payload,
            source_length=source_length,
        )

    else:
        raise ValueError("unknown transform-chain inner model")

    restored = invert_transform(transformed, spec)
    if len(restored) != source_length:
        raise ValueError("transform-chain source length mismatch")
    return restored
