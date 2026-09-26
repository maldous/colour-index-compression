#!/usr/bin/env python3
"""Bounded universal model tournament.

This is deliberately small enough for frequent architectural experiments. It uses one
fixed format-agnostic policy across generated sources plus a few public Canterbury files.
No source name is ever passed to the CIX encoder.
"""

from __future__ import annotations

import bz2
import copy
import gzip
import json
import lzma
import math
import os
import random
import time
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path

try:
    import brotli
except ImportError:
    brotli = None
try:
    import zstandard as zstd
except ImportError:
    zstd = None

from cix.adaptive import decode_adaptive, encode_adaptive
from cix.cli import config_for_level
from cix.expertmix import decode_expert_mix, encode_expert_mix
from cix.mixer import decode_mixer, encode_mixer
from cix.multinomial import StreamConfig, StreamEncoder, decompress
from cix.ppm import decode_ppm, encode_ppm


CANTERBURY = {
    "alice29.txt": "https://raw.githubusercontent.com/nabcouwer/cantrbry/master/alice29.txt",
    "cp.html": "https://raw.githubusercontent.com/nabcouwer/cantrbry/master/cp.html",
    "fields.c": "https://raw.githubusercontent.com/nabcouwer/cantrbry/master/fields.c",
    "grammar.lsp": "https://raw.githubusercontent.com/nabcouwer/cantrbry/master/grammar.lsp",
    "xargs.1": "https://raw.githubusercontent.com/nabcouwer/cantrbry/master/xargs.1",
}


def generated_sources() -> dict[str, bytes]:
    rng = random.Random(20260927)
    n = 8192

    random_bytes = bytes(rng.randrange(256) for _ in range(n))
    biased = bytes(0 if rng.random() < 0.92 else rng.randrange(1, 16) for _ in range(n))

    markov = bytearray()
    value = rng.randrange(256)
    for _ in range(n):
        if rng.random() < 0.04:
            value = rng.randrange(256)
        markov.append(value)

    periodic = bytearray()
    pattern = bytes(rng.randrange(256) for _ in range(37))
    for i in range(n):
        value = pattern[i % len(pattern)]
        if rng.random() < 0.015:
            value ^= 1 << rng.randrange(8)
        periodic.append(value)

    counter = b"".join(i.to_bytes(4, "little") for i in range(n // 4))

    timestamps = bytearray()
    value = 1_700_000_000_000
    for i in range(n // 8):
        value += 1000 + ((i % 9) - 4)
        timestamps += value.to_bytes(8, "little")

    repetitive = (b"universal-colour-index-model|" * ((n // 29) + 1))[:n]

    structured = b"".join(
        (
            f"{i:06d}|item-{i % 137:03d}|group-{i % 17:02d}|"
            f"{(i * 31) % 10007:05d}|{i % 2}\n"
        ).encode()
        for i in range(400)
    )[:n]

    mixed = (
        random_bytes[:2048]
        + biased[:1536]
        + repetitive[:1536]
        + counter[:1536]
        + structured[:1536]
    )

    return {
        "gen-random": random_bytes,
        "gen-biased": biased,
        "gen-markov": bytes(markov),
        "gen-periodic": bytes(periodic),
        "gen-counter": counter,
        "gen-time": bytes(timestamps),
        "gen-repeat": repetitive,
        "gen-structured": structured,
        "gen-mixed": mixed,
    }


def real_sources(work: Path) -> dict[str, bytes]:
    work.mkdir(parents=True, exist_ok=True)
    out = {}
    for name, url in CANTERBURY.items():
        path = work / name
        if not path.exists():
            urllib.request.urlretrieve(url, path)
        out[f"canterbury-{name}"] = path.read_bytes()
    return out


def tournament_config() -> StreamConfig:
    config = config_for_level(6)
    config.min_block = 2048
    config.max_block = 8192
    config.probe_stride = 1024
    config.history_bytes = 1 << 18
    config.lz_window_bytes = 1 << 18
    config.lz_chain = 16
    config.context_beam = 2
    config.transform_beam = 2
    config.adaptive_beam = 1
    config.record_beam = 1
    config.periodic_beam = 1
    config.ppm_beam = 1
    config.enable_chains = False
    return config


def profiles() -> dict[str, StreamConfig]:
    base = tournament_config()
    result = {"full": base}

    def variant(name, **changes):
        cfg = copy.deepcopy(base)
        for key, value in changes.items():
            setattr(cfg, key, value)
        result[name] = cfg

    variant("no-lz", enable_lz=False)
    variant("no-bwt", enable_bwt=False)
    variant("no-adaptive", enable_adaptive=False, enable_persistent_adaptive=False)
    variant("no-ppm", enable_ppm=False)
    variant("no-expert", enable_expert_mix=False)
    variant("no-periodic-record", enable_periodic=False, enable_record=False)
    variant("no-numeric", enable_numeric=False)
    variant("no-sparse-runs", enable_sparse=False, enable_runs=False)
    variant("no-dedup", enable_dedup=False)

    core = copy.deepcopy(base)
    core.enable_lz = False
    core.enable_bwt = False
    core.enable_transforms = False
    core.enable_bitplanes = False
    core.enable_numeric = False
    core.enable_dedup = False
    core.enable_adaptive = False
    core.enable_persistent_adaptive = False
    core.enable_sparse = False
    core.enable_runs = False
    core.enable_record = False
    core.enable_periodic = False
    core.enable_ppm = False
    core.enable_expert_mix = False
    core.context_beam = 2
    result["multinomial-core"] = core
    return result


@dataclass
class CodecResult:
    profile: str
    source: str
    original: int
    compressed: int
    seconds: float
    models: list[str]


def compress_cix(data: bytes, config: StreamConfig) -> tuple[bytes, float, list[str]]:
    start = time.perf_counter()
    encoder = StreamEncoder(config)
    blob = encoder.feed(data) + encoder.finish()
    seconds = time.perf_counter() - start
    if decompress(blob) != data:
        raise RuntimeError("CIX round-trip failed")
    return blob, seconds, list(encoder.block_descriptions)


def predictor_probe(name: str, data: bytes) -> dict[str, int]:
    probes = {}

    payload = encode_adaptive(data, order=2, bucket_bits=10)
    if decode_adaptive(payload, source_length=len(data)) != data:
        raise RuntimeError("adaptive probe round-trip failed")
    probes["adaptive-o2"] = len(payload)

    payload = encode_ppm(data, max_order=4)
    if decode_ppm(payload, source_length=len(data)) != data:
        raise RuntimeError("PPM probe round-trip failed")
    probes["ppm-o4"] = len(payload)

    orders = (0, 1, 2, 4)
    payload = encode_expert_mix(data, orders=orders)
    if decode_expert_mix(payload, source_length=len(data)) != data:
        raise RuntimeError("expert probe round-trip failed")
    probes["byte-expert"] = len(payload)

    payload = encode_mixer(data, orders=orders)
    if decode_mixer(payload, source_length=len(data)) != data:
        raise RuntimeError("mixer probe round-trip failed")
    probes["bit-mixer"] = len(payload)

    return probes


def main():
    sources = generated_sources()
    sources.update(real_sources(Path("benchmark-work/tournament")))
    configs = profiles()
    rows: list[CodecResult] = []

    for source_name, data in sources.items():
        for profile_name, config in configs.items():
            blob, seconds, models = compress_cix(data, config)
            rows.append(
                CodecResult(
                    profile_name,
                    source_name,
                    len(data),
                    len(blob),
                    seconds,
                    models,
                )
            )
            print(
                "CIX",
                source_name,
                profile_name,
                f"{100*len(blob)/len(data):.3f}%",
                f"{seconds:.3f}s",
                flush=True,
            )

    predictor_rows = {}
    for source_name, data in sources.items():
        predictor_rows[source_name] = predictor_probe(source_name, data)
        print("PRED", source_name, predictor_rows[source_name], flush=True)

    reference_rows = {}
    for source_name, data in sources.items():
        reference_rows[source_name] = {
            "gzip": len(gzip.compress(data, 9)),
            "bzip2": len(bz2.compress(data, 9)),
            "xz": len(lzma.compress(data, preset=9)),
            "brotli": len(brotli.compress(data, quality=11)) if brotli else None,
            "zstd": len(zstd.ZstdCompressor(level=19).compress(data)) if zstd else None,
        }

    payload = {
        "cix": [asdict(row) for row in rows],
        "predictors": predictor_rows,
        "references": reference_rows,
    }
    Path("tournament-results.json").write_text(json.dumps(payload, indent=2))

    # Aggregate byte delta from full; positive means the removed family helped.
    full_by_source = {
        row.source: row.compressed
        for row in rows if row.profile == "full"
    }
    summary = []
    for profile_name in configs:
        if profile_name == "full":
            continue
        delta = sum(
            row.compressed - full_by_source[row.source]
            for row in rows if row.profile == profile_name
        )
        summary.append((delta, profile_name))
    summary.sort(reverse=True)

    print("ABLATION_RANKING", summary, flush=True)

    # Geometric mean normalized ratio across all sources.
    for profile_name in configs:
        values = [
            row.compressed / row.original
            for row in rows if row.profile == profile_name
        ]
        gm = math.exp(sum(math.log(x) for x in values) / len(values))
        print("PROFILE_GM", profile_name, gm, flush=True)


if __name__ == "__main__":
    main()
