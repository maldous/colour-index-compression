#!/usr/bin/env python3
"""Bounded byte-parity checks for retained pure-Python helper codecs.

This is scheduler-run only. It never invokes PAQ, archive corpus runners, or a
complete compressor route.  The baseline package is imported as ``cix_runtime``
from a staged site directory; the edited tree is imported as
``runtime.cix_runtime`` from the repository parent.
"""
from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path
import struct
import sys
from typing import Callable


def _load(baseline_site: Path, repository: Path):
    sys.path.insert(0, str(baseline_site.resolve()))
    baseline = lambda name: importlib.import_module(f"cix_runtime.legacy.{name}")
    sys.path.insert(0, str(repository.resolve()))
    current = lambda name: importlib.import_module(f"runtime.cix_runtime.legacy.{name}")
    return baseline, current


def _equal(label: str, baseline_value, current_value) -> None:
    if baseline_value != current_value:
        raise AssertionError(f"byte parity failed: {label}")


def _cross_decode(label: str, encoded: bytes, decoder: Callable, expected) -> None:
    decoded = decoder(encoded)
    if decoded != expected:
        raise AssertionError(f"cross decode failed: {label}")


def _remaining_counts(baseline, current) -> int:
    old, new = baseline("mysql_remaining_counts"), current("mysql_remaining_counts")
    cases = (([0, 1, 0, 2, 1], [2, 2, 1]), ([0, 1, 2, 3], [1, 1, 1, 1]))
    total = 0
    for ids, counts in cases:
        for mode in range(1, 5):
            old_encoded, new_encoded = old.order_encode(ids, counts, mode), new.order_encode(ids, counts, mode)
            _equal(f"remaining-count:{ids}:{mode}", old_encoded, new_encoded)
            _cross_decode(f"remaining old->new:{mode}", old_encoded, lambda blob: new.order_decode(blob, counts), ids)
            _cross_decode(f"remaining new->old:{mode}", new_encoded, lambda blob: old.order_decode(blob, counts), ids)
            total += 1
    return total


def _ordered_subsets(baseline, current) -> int:
    old, new = baseline("ordered_subset"), current("ordered_subset")
    cases = (([], 7), ([0], 7), ([1, 3, 6], 7), ([0, 2, 4, 7], 8))
    total = 0
    for values, universe in cases:
        for method in (0, 1):
            old_encoded, new_encoded = old.encode(values, universe, method), new.encode(values, universe, method)
            _equal(f"subset:{values}:{method}", old_encoded, new_encoded)
            _cross_decode(f"subset old->new:{method}", old_encoded, lambda blob: new.decode(blob, 0, universe, len(values), method), (values, len(old_encoded)))
            _cross_decode(f"subset new->old:{method}", new_encoded, lambda blob: old.decode(blob, 0, universe, len(values), method), (values, len(new_encoded)))
            total += 1
    return total


def _type_classes(baseline, current) -> int:
    old, new = baseline("multinomial"), current("multinomial")
    streams = (b"", b"a", b"banana", bytes((index * 17) % 5 for index in range(31)))
    total = 0
    for stream in streams:
        old_encoded, new_encoded = old.encode_type_class(stream), new.encode_type_class(stream)
        _equal(f"type-class:{len(stream)}", old_encoded, new_encoded)
        _cross_decode("type class old->new", old_encoded, new.decode_type_class, (stream, len(old_encoded)))
        _cross_decode("type class new->old", new_encoded, old.decode_type_class, (stream, len(new_encoded)))
        old_known, new_known = old.encode_type_class_known_n(stream), new.encode_type_class_known_n(stream)
        _equal(f"type-class-known:{len(stream)}", old_known, new_known)
        _cross_decode("known old->new", old_known, lambda blob: new.decode_type_class_known_n(blob, 0, len(stream)), (stream, len(old_known)))
        _cross_decode("known new->old", new_known, lambda blob: old.decode_type_class_known_n(blob, 0, len(stream)), (stream, len(new_known)))
        total += 2
    counts = [0] * 256
    stream = b"abracadabra"
    for value in stream:
        counts[value] += 1
    old_payload = old._range_encode_type_sequence(stream, counts)
    new_payload = new._range_encode_type_sequence(stream, counts)
    _equal("type-class-range", old_payload, new_payload)
    payload, bits = old_payload
    _cross_decode("range old->new", payload, lambda blob: new._range_decode_type_sequence(blob, bits, counts), stream)
    payload, bits = new_payload
    _cross_decode("range new->old", payload, lambda blob: old._range_decode_type_sequence(blob, bits, counts), stream)
    return total + 1


def _wcstools_fixture() -> bytes:
    header = struct.pack("<7i", 0, 0, 1, 0, 1, 1, 28)
    # One independent 28-byte record; transform accepts arbitrary IEEE fields.
    record = bytes((index * 29 + 7) & 255 for index in range(28))
    return header + record


def _grid_helpers(baseline, current) -> int:
    fixture = _wcstools_fixture(); old_grid, new_grid = baseline("record_float_grid"), current("record_float_grid")
    old_context, new_context = baseline("grid_context"), current("grid_context")
    total = 0
    for mode in range(4):
        old_encoded, new_encoded = old_grid.transform(fixture, mode)[0], new_grid.transform(fixture, mode)[0]
        _equal(f"grid-coding:{mode}", old_encoded, new_encoded)
        _cross_decode("grid old->new", old_encoded, new_grid.inverse, fixture)
        _cross_decode("grid new->old", new_encoded, old_grid.inverse, fixture)
        total += 1
    for mode in range(5):
        old_encoded, new_encoded = old_context.transform(fixture, mode)[0], new_context.transform(fixture, mode)[0]
        _equal(f"grid-context:{mode}", old_encoded, new_encoded)
        _cross_decode("context old->new", old_encoded, new_context.inverse, fixture)
        _cross_decode("context new->old", new_encoded, old_context.inverse, fixture)
        total += 1
    return total


def _sdf_fixture() -> bytes:
    counts = b"  1  0  0  0  0  0            999 V2000\n"
    atom = b"    0.0000    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0\n"
    return b"CIX\n  parity\n\n" + counts + atom + b"M  END\n$$$$\n"


def _sdf_helpers(baseline, current) -> int:
    fixture = _sdf_fixture(); old_geometry, new_geometry = baseline("sdf_geometry"), current("sdf_geometry")
    old_hydrogen, new_hydrogen = baseline("sdf_hydrogen"), current("sdf_hydrogen")
    total = 0
    for mode in range(3):
        for representation in range(3):
            old_encoded, new_encoded = old_geometry.encode(fixture, mode, representation)[0], new_geometry.encode(fixture, mode, representation)[0]
            _equal(f"geometry:{mode}:{representation}", old_encoded, new_encoded)
            _cross_decode("geometry old->new", old_encoded, new_geometry.decode, fixture)
            _cross_decode("geometry new->old", new_encoded, old_geometry.decode, fixture)
            total += 1
    for model in range(3):
        for representation in range(4):
            old_encoded, new_encoded = old_hydrogen.encode(fixture, model, representation)[0], new_hydrogen.encode(fixture, model, representation)[0]
            _equal(f"hydrogen:{model}:{representation}", old_encoded, new_encoded)
            _cross_decode("hydrogen old->new", old_encoded, new_hydrogen.decode, fixture)
            _cross_decode("hydrogen new->old", new_encoded, old_hydrogen.decode, fixture)
            total += 1
    return total


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-site", type=Path, required=True)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--json", type=Path, required=True)
    args = parser.parse_args()
    baseline, current = _load(args.baseline_site, args.repository)
    checks = {
        "remaining_count": _remaining_counts(baseline, current),
        "ordered_subset": _ordered_subsets(baseline, current),
        "type_class": _type_classes(baseline, current),
        "grid": _grid_helpers(baseline, current),
        "sdf": _sdf_helpers(baseline, current),
    }
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps({"status": "PASS", "checks": checks, "total": sum(checks.values())}, indent=2) + "\n")


if __name__ == "__main__":
    main()
