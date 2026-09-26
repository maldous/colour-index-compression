"""Native Prediction-by-Partial-Matching model for CIX.

This is a format-agnostic causal context model. It uses escape/backoff with exclusion:
try the longest available byte context, escape when the next symbol has not been seen,
exclude symbols already offered, and back off until a symbol is coded. The final
order -1 model is uniform over the remaining byte alphabet.

No trained table is transmitted; encoder and decoder update identical context counts.
"""
from __future__ import annotations

import math

from collections import defaultdict

from .multinomial import _ArithmeticDecoder, _ArithmeticEncoder, vdecode, vencode

PPM_VERSION=1
CONTEXT_LIMIT=16384


def _ctx(history:bytearray,order:int)->bytes:
    return bytes(history[-order:]) if order else b""


def _rescale(counts:dict[int,int])->None:
    if sum(counts.values())<=CONTEXT_LIMIT:
        return
    for symbol in list(counts):
        counts[symbol]=max(1,(counts[symbol]+1)//2)


def _eligible(counts:dict[int,int]|None,excluded:set[int])->list[int]:
    if not counts:
        return []
    return [s for s in sorted(counts) if s not in excluded]


def estimate_ppm_bits(
    data: bytes,
    *,
    max_order: int,
    prefix_history: bytes = b"",
    sample_limit: int = 4096,
) -> float:
    """Estimate PPM description length without emitting an arithmetic stream."""
    if not 0 <= max_order <= 8:
        raise ValueError("PPM order outside supported range")

    sample = data[:sample_limit]
    tables: dict[bytes, dict[int, int]] = {}
    history = bytearray(prefix_history[-max_order:] if max_order else b"")
    bits = 0.0

    for symbol in sample:
        excluded: set[int] = set()
        coded = False
        highest = min(max_order, len(history))

        for order in range(highest, -1, -1):
            context = _ctx(history, order)
            counts = tables.get(context)
            symbols = _eligible(counts, excluded)
            if not symbols:
                continue

            assert counts is not None
            mass = sum(counts[s] for s in symbols)
            escape = max(1, len(symbols))
            total = mass + escape

            if symbol in counts and symbol not in excluded:
                bits += math.log2(total) - math.log2(counts[symbol])
                coded = True
                break

            bits += math.log2(total) - math.log2(escape)
            excluded.update(symbols)

        if not coded:
            remaining = 256 - len(excluded)
            bits += math.log2(max(1, remaining))

        highest = min(max_order, len(history))
        for order in range(highest, -1, -1):
            context = _ctx(history, order)
            counts = tables.get(context)
            if counts is None:
                counts = {}
                tables[context] = counts
            counts[symbol] = counts.get(symbol, 0) + 1
            _rescale(counts)

        if max_order:
            history.append(symbol)
            if len(history) > max_order:
                del history[:-max_order]

    if not sample:
        return 0.0
    return bits * (len(data) / len(sample))


def encode_ppm(
    data:bytes,
    *,
    max_order:int=4,
    prefix_history:bytes=b"",
)->bytes:
    if not 0<=max_order<=8:
        raise ValueError("PPM order outside supported range")

    tables:dict[bytes,dict[int,int]]={}
    history=bytearray(prefix_history[-max_order:] if max_order else b"")
    encoder=_ArithmeticEncoder()

    for symbol in data:
        excluded:set[int]=set()
        coded=False
        highest=min(max_order,len(history))

        for order in range(highest,-1,-1):
            context=_ctx(history,order)
            counts=tables.get(context)
            symbols=_eligible(counts,excluded)
            if not symbols:
                continue

            assert counts is not None
            mass=sum(counts[s] for s in symbols)
            escape=max(1,len(symbols))
            total=mass+escape

            if symbol in counts and symbol not in excluded:
                low=0
                for candidate in symbols:
                    high=low+counts[candidate]
                    if candidate==symbol:
                        encoder.encode(low,high,total)
                        coded=True
                        break
                    low=high
                if coded:
                    break
            else:
                encoder.encode(mass,total,total)
                excluded.update(symbols)

        if not coded:
            remaining=[s for s in range(256) if s not in excluded]
            try:
                rank=remaining.index(symbol)
            except ValueError as exc:
                raise AssertionError("PPM target excluded without being coded") from exc
            encoder.encode(rank,rank+1,len(remaining))

        # Update every suffix context after coding.
        highest=min(max_order,len(history))
        for order in range(highest,-1,-1):
            context=_ctx(history,order)
            counts=tables.get(context)
            if counts is None:
                counts={}
                tables[context]=counts
            counts[symbol]=counts.get(symbol,0)+1
            _rescale(counts)

        if max_order:
            history.append(symbol)
            if len(history)>max_order:
                del history[:-max_order]

    payload,bit_length=encoder.finish()
    return bytes((PPM_VERSION,max_order))+vencode(bit_length)+payload


def decode_ppm(
    blob:bytes,
    *,
    source_length:int,
    prefix_history:bytes=b"",
)->bytes:
    if len(blob)<2 or blob[0]!=PPM_VERSION:
        raise ValueError("unknown PPM version")
    max_order=blob[1]
    if not 0<=max_order<=8:
        raise ValueError("invalid PPM order")

    bit_length,pos=vdecode(blob,2)
    byte_length=(bit_length+7)//8
    if pos+byte_length!=len(blob):
        raise ValueError("PPM payload length mismatch")

    decoder=_ArithmeticDecoder(blob[pos:],bit_length)
    tables:dict[bytes,dict[int,int]]={}
    history=bytearray(prefix_history[-max_order:] if max_order else b"")
    out=bytearray()

    for _ in range(source_length):
        excluded:set[int]=set()
        symbol=None
        highest=min(max_order,len(history))

        for order in range(highest,-1,-1):
            context=_ctx(history,order)
            counts=tables.get(context)
            symbols=_eligible(counts,excluded)
            if not symbols:
                continue

            assert counts is not None
            mass=sum(counts[s] for s in symbols)
            escape=max(1,len(symbols))
            total=mass+escape
            target=decoder.target(total)

            if target< mass:
                low=0
                for candidate in symbols:
                    high=low+counts[candidate]
                    if target<high:
                        decoder.update(low,high,total)
                        symbol=candidate
                        break
                    low=high
                if symbol is None:
                    raise ValueError("PPM symbol interval not found")
                break

            decoder.update(mass,total,total)
            excluded.update(symbols)

        if symbol is None:
            remaining=[s for s in range(256) if s not in excluded]
            target=decoder.target(len(remaining))
            if not 0<=target<len(remaining):
                raise ValueError("PPM fallback target outside alphabet")
            symbol=remaining[target]
            decoder.update(target,target+1,len(remaining))

        out.append(symbol)

        highest=min(max_order,len(history))
        for order in range(highest,-1,-1):
            context=_ctx(history,order)
            counts=tables.get(context)
            if counts is None:
                counts={}
                tables[context]=counts
            counts[symbol]=counts.get(symbol,0)+1
            _rescale(counts)

        if max_order:
            history.append(symbol)
            if len(history)>max_order:
                del history[:-max_order]

    return bytes(out)
