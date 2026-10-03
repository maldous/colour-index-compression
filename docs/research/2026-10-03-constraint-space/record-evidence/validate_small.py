#!/usr/bin/env python3
"""Independent small-space oracle validation for frozen ERC1 and RDIC binaries.

Usage: validate_small.py ERC_DECODER RDIC_BINARY [--supplement-dir DIRECTORY]

The supplied binaries are treated as opaque. Inputs, archives, and restored
files live in a temporary directory outside Git; persistent output is limited
to results.json and each child process's stdout/stderr under supplement/.
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import subprocess
import tempfile
import zlib
from pathlib import Path


ALPHABET = (17, 230)


def crc(data: bytes) -> bytes:
    return zlib.crc32(data).to_bytes(4, "little")


def rank_width(cardinality: int) -> int:
    return (cardinality - 1).bit_length()


def packed(rank: int, width: int) -> bytes:
    if rank < 0 or rank.bit_length() > width:
        raise ValueError("rank does not fit its canonical width")
    return rank.to_bytes((width + 7) // 8, "big")


def bit_word(value: int, bits: int) -> bytes:
    return bytes(ALPHABET[(value >> (bits - 1 - bit)) & 1] for bit in range(bits))


def erc_table(mode: int, mask: int, count: int) -> list[int]:
    table: list[int] = []
    for value in range(16):
        equality = all(
            not (mask & (1 << position))
            or ((value >> (3 - position)) & 1) == ((value >> (2 - position)) & 1)
            for position in range(3)
        )
        matching_count = value.bit_count() == count
        if (mode == 2 or equality) and (mode == 1 or matching_count):
            table.append(value)
    return table


def erc_archive(mode: int, mask: int, count: int, table: list[int], rank: int) -> bytes:
    cardinality = len(table) ** 2
    width = rank_width(cardinality)
    header = (
        b"ERC1"
        + bytes((1, mode))
        + (8).to_bytes(4, "little")
        + bytes((4,))
        + mask.to_bytes(2, "little")
        + bytes((count,))
        + bytes(ALPHABET)
        + width.to_bytes(4, "little")
    )
    if len(header) != 20:
        raise AssertionError("ERC1 header size")
    archive = header + packed(rank, width)
    return archive + crc(archive)


def colex_rank(dictionary: tuple[int, ...]) -> int:
    return sum(math.comb(word, index + 1) for index, word in enumerate(dictionary))


def rdic_archive(dictionary: tuple[int, ...], sequence_rank: int) -> bytes:
    count = len(dictionary)
    dictionary_cardinality = math.comb(4, count)
    sequence_cardinality = count**2
    dictionary_width = rank_width(dictionary_cardinality)
    sequence_width = rank_width(sequence_cardinality)
    header = (
        b"RDIC"
        + bytes((1, 1))
        + (4).to_bytes(4, "little")
        + bytes((2,))
        + count.to_bytes(2, "little")
        + bytes(ALPHABET)
    )
    if len(header) != 15:
        raise AssertionError("RDIC header size")
    archive = header + packed(colex_rank(dictionary), dictionary_width)
    archive += packed(sequence_rank, sequence_width)
    return archive + crc(archive)


def run_decoder(decoder: Path, archive: bytes, expected: bytes, label: str, work: Path, logs: Path) -> None:
    archive_path = work / f"{label}.archive"
    output_path = work / f"{label}.restored"
    archive_path.write_bytes(archive)
    result = subprocess.run(
        [str(decoder), "decode", str(archive_path), str(output_path)],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=5,
    )
    (logs / f"{label}.stdout").write_bytes(result.stdout)
    (logs / f"{label}.stderr").write_bytes(result.stderr)
    if result.returncode != 0:
        raise RuntimeError(f"{label}: decoder exited {result.returncode}")
    if not output_path.exists() or output_path.read_bytes() != expected:
        raise RuntimeError(f"{label}: restored bytes differ from the independent oracle")


def validate_erc(decoder: Path, work: Path, logs: Path) -> int:
    cases = (("e", 1, 1, 0), ("c", 2, 0, 2), ("ec", 3, 1, 2))
    checked = 0
    for name, mode, mask, count in cases:
        table = erc_table(mode, mask, count)
        expected_size = {"e": 8, "c": 6, "ec": 2}[name]
        if len(table) != expected_size:
            raise AssertionError(f"{name}: oracle local cardinality")
        for rank in range(len(table) ** 2):
            first, second = divmod(rank, len(table))
            expected = bit_word(table[first], 4) + bit_word(table[second], 4)
            run_decoder(
                decoder,
                erc_archive(mode, mask, count, table, rank),
                expected,
                f"erc-{name}-{rank:02d}",
                work,
                logs,
            )
            checked += 1
    if checked != 104:
        raise AssertionError(f"ERC1 case count was {checked}, expected 104")
    return checked


def validate_rdic(decoder: Path, work: Path, logs: Path) -> int:
    checked = 0
    for dictionary in itertools.combinations(range(4), 2):
        for sequence_rank in range(4):
            first, second = divmod(sequence_rank, 2)
            expected = bit_word(dictionary[first], 2) + bit_word(dictionary[second], 2)
            run_decoder(
                decoder,
                rdic_archive(dictionary, sequence_rank),
                expected,
                f"rdic-{''.join(map(str, dictionary))}-{sequence_rank}",
                work,
                logs,
            )
            checked += 1
    if checked != 24:
        raise AssertionError(f"RDIC case count was {checked}, expected 24")
    return checked


def validate_rdic_overfull_auto(binary: Path, work: Path, logs: Path) -> dict[str, int]:
    source = b"".join(bit_word(word, 12) for word in range(300))
    if len(source) != 3600:
        raise AssertionError("b12 source length")
    input_path = work / "rdic-overfull-b12.input"
    archive_path = work / "rdic-overfull-b12.archive"
    output_path = work / "rdic-overfull-b12.restored"
    input_path.write_bytes(source)
    encoded = subprocess.run(
        [str(binary), "encode", str(input_path), str(archive_path)],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=5,
    )
    (logs / "rdic-overfull-b12-encode.stdout").write_bytes(encoded.stdout)
    (logs / "rdic-overfull-b12-encode.stderr").write_bytes(encoded.stderr)
    if encoded.returncode != 0 or not archive_path.exists():
        raise RuntimeError("RDIC auto encoder did not skip the overfull b12 dictionary")
    archive = archive_path.read_bytes()
    if len(archive) < 19 or archive[:4] != b"RDIC":
        raise RuntimeError("RDIC auto encoder emitted an invalid envelope")
    if archive[5] == 1 and archive[10] == 12:
        raise RuntimeError("RDIC auto encoder selected an overfull b12 dictionary")
    decoded = subprocess.run(
        [str(binary), "decode", str(archive_path), str(output_path)],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=5,
    )
    (logs / "rdic-overfull-b12-decode.stdout").write_bytes(decoded.stdout)
    (logs / "rdic-overfull-b12-decode.stderr").write_bytes(decoded.stderr)
    if decoded.returncode != 0 or not output_path.exists() or output_path.read_bytes() != source:
        raise RuntimeError("RDIC auto overfull control did not restore byte-exactly")
    return {
        "input_bytes": len(source),
        "archive_bytes": len(archive),
        "selected_mode": archive[5],
        "selected_bits": archive[10],
        "selected_dictionary_entries": int.from_bytes(archive[11:13], "little"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("erc_decoder", type=Path)
    parser.add_argument("rdic_binary", type=Path)
    parser.add_argument(
        "--supplement-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "supplement",
        help="persistent results and raw child logs; archives stay in a temporary directory",
    )
    arguments = parser.parse_args()
    logs = arguments.supplement_dir
    logs.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="constraint-record-oracle-", dir="/home/user/src/colour-index-compression/benchmark-work/equality-records") as temporary:
        work = Path(temporary)
        erc_cases = validate_erc(arguments.erc_decoder, work, logs)
        rdic_cases = validate_rdic(arguments.rdic_binary, work, logs)
        overfull = validate_rdic_overfull_auto(arguments.rdic_binary, work, logs)
    result = {
        "erc1_cases": erc_cases,
        "rdic_cases": rdic_cases,
        "total_fresh_decoder_cases": erc_cases + rdic_cases + 1,
        "rdic_overfull_b12": overfull,
    }
    (logs / "results.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
