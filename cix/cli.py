"""Command-line entry points for cix and uncix."""

from __future__ import annotations

import argparse
from pathlib import Path

from .fileformat import compress_file, decompress_file
from .multinomial import ContextModel, StreamConfig


def config_for_level(level: int, extreme: bool = False) -> StreamConfig:
    if extreme:
        return StreamConfig.extreme()

    level = max(1, min(9, level))

    if level <= 2:
        return StreamConfig(
            min_block=4096,
            max_block=8192,
            probe_stride=2048,
            history_bytes=1 << 18,
            lz_window_bytes=1 << 18,
            lz_chain=8,
            enable_bwt=False,
            enable_chains=False,
            enable_record=False,
            enable_periodic=False,
            enable_ppm=False,
            enable_expert_mix=False,
            enable_adaptive=False,
            enable_persistent_adaptive=False,
            context_beam=1,
            transform_beam=1,
            context_models=(ContextModel(1, 8), ContextModel(2, 8)),
        )

    if level <= 5:
        return StreamConfig(
            min_block=2048,
            max_block=16384,
            probe_stride=1024,
            history_bytes=1 << 20,
            lz_window_bytes=1 << 20,
            lz_chain=24,
            enable_chains=False,
            record_beam=1,
            periodic_beam=1,
            context_beam=2,
            transform_beam=3,
            adaptive_beam=1,
            enable_ppm=True,
            ppm_order=3,
            enable_expert_mix=False,
            context_models=(
                ContextModel(1, 8),
                ContextModel(2, 8),
                ContextModel(2, 10),
                ContextModel(4, 10),
            ),
        )

    if level <= 8:
        return StreamConfig(
            min_block=2048,
            max_block=16384,
            probe_stride=1024,
            split_gain_bits=96.0,
            history_bytes=1 << 20,
            lz_window_bytes=1 << 20,
            lz_chain=48,
            record_beam=2,
            periodic_beam=3,
            context_beam=4,
            transform_beam=6,
            adaptive_beam=3,
            enable_ppm=True,
            ppm_order=4,
        )

    return StreamConfig(
        min_block=4096,
        max_block=32768,
        probe_stride=1024,
        split_gain_bits=64.0,
        history_bytes=4 << 20,
        lz_window_bytes=4 << 20,
        lz_chain=96,
        enable_chains=True,
        record_beam=4,
        periodic_beam=6,
        context_beam=6,
        transform_beam=10,
        adaptive_beam=5,
        enable_ppm=True,
        ppm_order=5,
        ppm_beam=2,
        enable_expert_mix=True,
        expert_orders=(0, 1, 2, 3, 4),
        context_models=(
            ContextModel(1, 6),
            ContextModel(1, 8),
            ContextModel(2, 8),
            ContextModel(2, 10),
            ContextModel(3, 10),
            ContextModel(4, 10),
            ContextModel(4, 12),
            ContextModel(6, 12),
            ContextModel(8, 12),
        ),
    )


def _compress_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cix",
        description="Adaptive streaming Colour/Index compressor",
    )
    parser.add_argument("files", nargs="+")
    parser.add_argument("-o", "--output")
    parser.add_argument("-1", dest="level", action="store_const", const=1)
    parser.add_argument("-2", dest="level", action="store_const", const=2)
    parser.add_argument("-3", dest="level", action="store_const", const=3)
    parser.add_argument("-4", dest="level", action="store_const", const=4)
    parser.add_argument("-5", dest="level", action="store_const", const=5)
    parser.add_argument("-6", dest="level", action="store_const", const=6)
    parser.add_argument("-7", dest="level", action="store_const", const=7)
    parser.add_argument("-8", dest="level", action="store_const", const=8)
    parser.add_argument("-9", dest="level", action="store_const", const=9)
    parser.set_defaults(level=6)
    parser.add_argument("--extreme", action="store_true")
    parser.add_argument(
        "--chunk-mode",
        choices=("fixed", "adaptive", "content", "hybrid"),
        default=None,
    )
    parser.add_argument("--min-block", type=int)
    parser.add_argument("--max-block", type=int)
    parser.add_argument("--history", type=int)
    parser.add_argument("--structured-block", type=int)
    parser.add_argument("--lz-window", type=int)
    parser.add_argument("--lz-chain", type=int)
    parser.add_argument("--context-beam", type=int)
    parser.add_argument("--transform-beam", type=int)
    parser.add_argument("--record-beam", type=int)
    parser.add_argument("--periodic-beam", type=int)
    parser.add_argument("--content-mask-bits", type=int)
    parser.add_argument("--ppm-order", type=int, choices=range(0, 9))
    parser.add_argument("--ppm-beam", type=int)
    parser.add_argument("--no-lz", action="store_true")
    parser.add_argument("--no-bwt", action="store_true")
    parser.add_argument("--no-chains", action="store_true")
    parser.add_argument("--no-bitplanes", action="store_true")
    parser.add_argument("--no-transforms", action="store_true")
    parser.add_argument("--no-numeric", action="store_true")
    parser.add_argument("--no-dedup", action="store_true")
    parser.add_argument("--no-record", action="store_true")
    parser.add_argument("--no-periodic", action="store_true")
    parser.add_argument("--no-adaptive", action="store_true")
    parser.add_argument("--no-persistent-adaptive", action="store_true")
    parser.add_argument("--no-sparse", action="store_true")
    parser.add_argument("--no-runs", action="store_true")
    parser.add_argument("--no-ppm", action="store_true")
    parser.add_argument("--no-expert-mix", action="store_true")
    return parser


def main_compress(argv: list[str] | None = None) -> int:
    args = _compress_parser().parse_args(argv)
    if args.output and len(args.files) != 1:
        raise SystemExit("--output requires exactly one input file")

    config = config_for_level(args.level, args.extreme)
    if args.chunk_mode:
        config.chunk_mode = args.chunk_mode
    if args.min_block:
        config.min_block = args.min_block
    if args.max_block:
        config.max_block = args.max_block
    if args.history:
        config.history_bytes = args.history
        config.lz_window_bytes = min(config.lz_window_bytes, args.history)
    if args.structured_block:
        config.structured_block_target = args.structured_block
    if args.lz_window:
        config.lz_window_bytes = args.lz_window
    if args.lz_chain:
        config.lz_chain = args.lz_chain
    if args.context_beam:
        config.context_beam = args.context_beam
    if args.transform_beam:
        config.transform_beam = args.transform_beam
    if args.record_beam:
        config.record_beam = args.record_beam
    if args.periodic_beam:
        config.periodic_beam = args.periodic_beam
    if args.content_mask_bits:
        config.content_mask_bits = args.content_mask_bits
    if args.ppm_order is not None:
        config.ppm_order = args.ppm_order
    if args.ppm_beam is not None:
        config.ppm_beam = max(1, args.ppm_beam)

    if config.structured_block_target < config.max_block:
        config.structured_block_target = config.max_block

    config.enable_lz = not args.no_lz
    config.enable_bwt = not args.no_bwt
    config.enable_chains = not args.no_chains
    config.enable_bitplanes = not args.no_bitplanes
    config.enable_transforms = not args.no_transforms
    config.enable_numeric = not args.no_numeric
    config.enable_dedup = not args.no_dedup
    config.enable_record = not args.no_record
    config.enable_periodic = not args.no_periodic
    config.enable_adaptive = not args.no_adaptive
    config.enable_persistent_adaptive = not args.no_persistent_adaptive
    config.enable_sparse = not args.no_sparse
    config.enable_runs = not args.no_runs
    config.enable_ppm = not args.no_ppm
    config.enable_expert_mix = not args.no_expert_mix

    for file_name in args.files:
        destination = args.output if len(args.files) == 1 else None
        result = compress_file(file_name, destination, config=config)
        print(result)
    return 0


def main_decompress(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="uncix",
        description="Decompress a .cix file and restore its original basename",
    )
    parser.add_argument("files", nargs="+")
    parser.add_argument("-o", "--output")
    args = parser.parse_args(argv)

    if args.output and len(args.files) != 1:
        raise SystemExit("--output requires exactly one input file")

    for file_name in args.files:
        destination = args.output if len(args.files) == 1 else None
        result = decompress_file(file_name, destination)
        print(result)
    return 0
