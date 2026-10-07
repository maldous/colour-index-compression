"""Independent finite SMC1 checks. Root executes this only under the scheduler."""
from __future__ import annotations

import hashlib
import json
import struct
import subprocess
import sys
import zlib
from pathlib import Path

EXPECTED_CIX = Path(
    "/home/user/src/colour-index-compression/benchmark-work/release-d3a2/final/cix"
)
EXPECTED_CIX_SHA256 = "f9b8262086be9704d8d9425ccbf5cbf5274096ae88334ea1501aa4773034fac3"
MAX_ARCHIVE = 32768
MAX_SOURCE = 4096


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def call(args: list[str], expected: int = 0, timeout: int = 20) -> dict:
    completed = subprocess.run(args, capture_output=True, timeout=timeout)
    record = {
        "command": args,
        "exit": completed.returncode,
        "stdout": completed.stdout.decode("utf-8", "replace")[-4096:],
        "stderr": completed.stderr.decode("utf-8", "replace")[-4096:],
    }
    require(completed.returncode == expected, f"command status: {record}")
    return record


def ops_csv(operators: list[int]) -> str:
    return ",".join(map(str, operators))


def lane_count(n: int, width: int, phase: int, lane: int) -> int:
    return (n - (phase + lane) + width - 1) // width


def transform(source: bytes, width: int, phase: int, operators: list[int]) -> bytes:
    require(source and 1 <= width <= 8 and 0 <= phase < width, "test geometry")
    require(width <= len(source) - phase and len(operators) == width, "test geometry")
    require(operators[0] == 0 and all(0 <= op <= 4 for op in operators), "test ops")
    out = bytearray(source[:phase])
    for lane in range(width):
        for row in range(lane_count(len(source), width, phase, lane)):
            pos = phase + row * width + lane
            op = operators[lane]
            if row == 0 or op == 0:
                value = source[pos]
            elif op == 1:
                value = (source[pos] - source[pos - width]) & 255
            elif op == 2:
                value = (source[pos] - source[pos - 1]) & 255
            elif op == 3:
                value = source[pos] ^ source[pos - 1]
            else:
                value = source[pos] ^ source[pos - width]
            out.append(value)
    require(len(out) == len(source), "independent transform length")
    return bytes(out)


def inverse(data: bytes, width: int, phase: int, operators: list[int]) -> bytes:
    n = len(data)
    out = bytearray(data[:phase]) + bytearray(n - phase)
    cursor = phase
    for lane in range(width):
        for row in range(lane_count(n, width, phase, lane)):
            pos = phase + row * width + lane
            value = data[cursor]
            cursor += 1
            op = operators[lane]
            if row == 0 or op == 0:
                out[pos] = value
            elif op == 1:
                out[pos] = (value + out[pos - width]) & 255
            elif op == 2:
                out[pos] = (value + out[pos - 1]) & 255
            elif op == 3:
                out[pos] = value ^ out[pos - 1]
            else:
                out[pos] = value ^ out[pos - width]
    require(cursor == n, "independent inverse length")
    return bytes(out)


def parse_outer(archive: bytes) -> dict:
    require(25 <= len(archive) <= MAX_ARCHIVE, "outer length")
    require(archive[:4] == b"SMC1" and archive[4] == 1, "outer magic/version")
    backend = archive[5]
    n, transformed_n, checksum = struct.unpack_from("<III", archive, 6)
    width, phase, count = archive[18:21]
    require(0 < n <= MAX_SOURCE and transformed_n == n, "outer source lengths")
    require(1 <= width <= 8 and phase < width and width <= n - phase, "outer geometry")
    require(count == width, "outer operator count")
    operators = list(archive[21 : 21 + width])
    require(len(operators) == width and operators[0] == 0, "outer operators")
    require(all(0 <= op <= 4 for op in operators), "outer operators")
    payload_len = struct.unpack_from("<I", archive, 21 + width)[0]
    payload_offset = 25 + width
    require(payload_offset + payload_len == len(archive), "outer payload framing")
    return {
        "backend": backend,
        "n": n,
        "crc32": checksum,
        "width": width,
        "phase": phase,
        "operators": operators,
        "payload_offset": payload_offset,
        "payload": archive[payload_offset:],
    }


def replace_payload(archive: bytes, payload: bytes) -> bytes:
    info = parse_outer(archive)
    width = info["width"]
    prefix = archive[: 21 + width]
    rebuilt = prefix + struct.pack("<I", len(payload)) + payload
    require(len(rebuilt) <= MAX_ARCHIVE, "mutated archive cap")
    return rebuilt


def encode_varint(value: int) -> bytes:
    out = bytearray()
    while value >= 128:
        out.append((value & 127) | 128)
        value >>= 7
    out.append(value)
    return bytes(out)


def parse_varint(data: bytes, pos: int) -> tuple[int, int, int]:
    start = pos
    value = 0
    shift = 0
    while True:
        require(pos < len(data) and shift < 70, "fixture varint")
        byte = data[pos]
        pos += 1
        value |= (byte & 127) << shift
        if byte < 128:
            return value, start, pos
        shift += 7


def first_m6_frame(payload: bytes) -> dict:
    require(payload[:5] == b"CIXM6", "M6 seed magic")
    history, hs, he = parse_varint(payload, 5)
    mode_pos = he
    require(mode_pos < len(payload) and payload[mode_pos] != 255, "M6 seed frame")
    source_len, ss, se = parse_varint(payload, mode_pos + 1)
    payload_len, ps, pe = parse_varint(payload, se)
    body_end = pe + payload_len
    require(body_end < len(payload) and payload[body_end] == 255, "one-block M6 seed")
    footer_len, fs, fe = parse_varint(payload, body_end + 1)
    require(fe + 4 == len(payload), "M6 seed footer")
    return {
        "history": history,
        "history_start": hs,
        "history_end": he,
        "mode_pos": mode_pos,
        "source_len": source_len,
        "source_start": ss,
        "source_end": se,
        "payload_len": payload_len,
        "payload_start": ps,
        "payload_end": pe,
        "body_end": body_end,
        "footer_len": footer_len,
        "footer_start": fs,
        "footer_end": fe,
        "footer_crc": fe,
    }


def replace_slice(data: bytes, start: int, end: int, replacement: bytes) -> bytes:
    return data[:start] + replacement + data[end:]


def independent_cases() -> list[tuple[int, int, int, list[int]]]:
    cases = []
    index = 0
    for width in range(1, 9):
        phases = [0] if width == 1 else [0, width - 1]
        for phase in phases:
            for variant in range(2):
                tail = 1 if variant == 1 and width > 1 else 0
                n = phase + 2 * width + tail
                if index == 0:
                    n = 1
                elif width == 8 and phase == 7 and variant == 1:
                    n = 32
                operators = [0] + [((lane + phase + variant) % 5) for lane in range(1, width)]
                cases.append((index, n, phase, operators))
                index += 1
    require(len(cases) == 30, "independent case count")
    require(min(n for _, n, _, _ in cases) == 1 and max(n for _, n, _, _ in cases) == 32, "length boundary coverage")
    require({op for _, _, _, ops in cases for op in ops} == set(range(5)), "operator coverage")
    return cases


def discover_archives(work: Path) -> list[Path]:
    unique = {}
    for path in sorted(work.rglob("*")):
        if not path.is_file() or path.stat().st_size > MAX_ARCHIVE:
            continue
        with path.open("rb") as stream:
            if stream.read(4) != b"SMC1":
                continue
        digest = sha_file(path)
        unique.setdefault(digest, path)
    return list(unique.values())


def rejected(wrapper: Path, cix: Path, checks: Path, name: str, archive: bytes) -> dict:
    archive_path = checks / f"bad-{name}.smc"
    output_path = checks / f"bad-{name}.out"
    archive_path.write_bytes(archive)
    if output_path.exists():
        output_path.unlink()
    record = call(
        [str(wrapper), "decode", "--cix", str(cix), str(archive_path), str(output_path)],
        expected=1,
    )
    require(not output_path.exists(), f"malformed output exists: {name}")
    return {"name": name, "archive_sha256": sha_file(archive_path), "run": record}


def make_outer(backend: int, source: bytes, width: int, phase: int, operators: list[int], payload: bytes) -> bytes:
    archive = bytearray(b"SMC1\x01")
    archive.append(backend)
    archive.extend(struct.pack("<III", len(source), len(source), zlib.crc32(source)))
    archive.extend(bytes([width, phase, width]))
    archive.extend(operators)
    archive.extend(struct.pack("<I", len(payload)))
    archive.extend(payload)
    return bytes(archive)


def run_checks(wrapper: Path, cix: Path, work: Path) -> dict:
    require(wrapper.is_file() and cix.is_file() and work.is_dir(), "arguments")
    require(cix.resolve() == EXPECTED_CIX.resolve(), "unexpected CIX path")
    require(sha_file(cix) == EXPECTED_CIX_SHA256, "unexpected CIX identity")
    archives = discover_archives(work)
    require(archives, "no SMC1 archives discovered")
    checks = work / "independent-checks"
    require(not checks.exists(), "independent-checks already exists")
    checks.mkdir()
    records: dict = {
        "wrapper": {"path": str(wrapper), "sha256": sha_file(wrapper)},
        "cix": {"path": str(cix), "sha256": sha_file(cix)},
        "work": str(work),
        "independent": [],
        "fresh_decodes": [],
        "malformed": [],
    }

    for case, n, phase, operators in independent_cases():
        width = len(operators)
        source = bytes((i * i * 17 + case * 31 + (i >> 1) * 7 + 13) & 255 for i in range(n))
        expected = transform(source, width, phase, operators)
        require(inverse(expected, width, phase, operators) == source, f"Python inverse {case}")
        source_path = checks / f"tiny-{case}.bin"
        transformed_path = checks / f"tiny-{case}.transformed"
        archive_path = checks / f"tiny-{case}.native.smc"
        restored_path = checks / f"tiny-{case}.restored"
        source_path.write_bytes(source)
        transform_run = call(
            [
                str(wrapper), "transform", "--width", str(width), "--phase", str(phase),
                "--ops", ops_csv(operators), str(source_path), str(transformed_path),
            ]
        )
        require(transformed_path.read_bytes() == expected, f"Rust/Python transform {case}")
        native_run = call(
            [
                str(wrapper), "native", "--width", str(width), "--phase", str(phase),
                "--ops", ops_csv(operators), str(source_path), str(archive_path),
            ]
        )
        info = parse_outer(archive_path.read_bytes())
        require(info["backend"] == 2 and len(archive_path.read_bytes()) == 25 + width + len(info["payload"]), "native accounting")
        decode_run = call(
            [str(wrapper), "decode", "--cix", str(cix), str(archive_path), str(restored_path)]
        )
        require(restored_path.read_bytes() == source, f"native restore {case}")
        records["independent"].append(
            {
                "case": case, "n": n, "width": width, "phase": phase,
                "operators": operators, "source_sha256": sha_bytes(source),
                "transformed_sha256": sha_bytes(expected), "archive_sha256": sha_file(archive_path),
                "archive_bytes": archive_path.stat().st_size,
                "runs": [transform_run, native_run, decode_run],
            }
        )

    empty = checks / "empty.bin"
    empty.write_bytes(b"")
    for operation, command in [
        ("empty-transform", [str(wrapper), "transform", "--width", "1", "--phase", "0", "--ops", "0", str(empty), str(checks / "empty.transformed")]),
        ("empty-native", [str(wrapper), "native", "--width", "1", "--phase", "0", "--ops", "0", str(empty), str(checks / "empty.smc")]),
    ]:
        output = Path(command[-1])
        record = call(command, expected=1)
        require(not output.exists(), operation)
        records["malformed"].append({"name": operation, "run": record})

    seeds: dict[int, tuple[Path, bytes, dict]] = {}
    for index, archive_path in enumerate(archives):
        archive = archive_path.read_bytes()
        info = parse_outer(archive)
        seeds.setdefault(info["backend"], (archive_path, archive, info))
        restored = checks / f"discovered-{index}.restored"
        run = call([str(wrapper), "decode", "--cix", str(cix), str(archive_path), str(restored)])
        data = restored.read_bytes()
        require(len(data) == info["n"] and zlib.crc32(data) == info["crc32"], "fresh discovered decode")
        records["fresh_decodes"].append(
            {
                "archive": str(archive_path), "archive_sha256": sha_bytes(archive),
                "backend": info["backend"], "complete_bytes": len(archive),
                "restored_sha256": sha_bytes(data), "run": run,
            }
        )
    require(set(seeds) >= {0, 1, 2}, f"missing backend archives: {sorted(seeds)}")

    base = bytearray(next(iter(seeds.values()))[1])
    outer_mutations: list[tuple[str, bytes]] = []
    for name, offset, value in [
        ("outer-magic", 0, 0), ("outer-version", 4, 2), ("outer-backend", 5, 255),
        ("outer-width-zero", 18, 0), ("outer-width-high", 18, 9),
        ("outer-phase", 19, base[18]), ("outer-count", 20, 0),
        ("outer-lane0-op", 21, 1), ("outer-op-high", 21, 255),
    ]:
        changed = bytearray(base)
        changed[offset] = value
        outer_mutations.append((name, bytes(changed)))
    changed = bytearray(base)
    changed[6:14] = struct.pack("<II", 0, 0)
    outer_mutations.append(("outer-empty", bytes(changed)))
    changed = bytearray(base)
    changed[6:14] = struct.pack("<II", MAX_SOURCE + 1, MAX_SOURCE + 1)
    outer_mutations.append(("outer-source-high", bytes(changed)))
    changed = bytearray(base)
    changed[10:14] = struct.pack("<I", struct.unpack_from("<I", changed, 6)[0] - 1)
    outer_mutations.append(("outer-transformed-length", bytes(changed)))
    changed = bytearray(base)
    changed[14:18] = struct.pack("<I", struct.unpack_from("<I", changed, 14)[0] ^ 1)
    outer_mutations.append(("outer-crc", bytes(changed)))
    outer_mutations.extend([("outer-truncated", bytes(base[:-1])), ("outer-trailing", bytes(base) + b"\0")])
    info = parse_outer(bytes(base))
    changed = bytearray(base)
    struct.pack_into("<I", changed, 21 + info["width"], len(info["payload"]) + 1)
    outer_mutations.append(("outer-payload-length", bytes(changed)))
    for name, data in outer_mutations:
        records["malformed"].append(rejected(wrapper, cix, checks, name, data))

    m6_archive = seeds[0][1]
    m6_info = seeds[0][2]
    m6 = m6_info["payload"]
    frame = first_m6_frame(m6)
    m6_changes = [
        ("m6-magic", b"X" + m6[1:]),
        ("m6-history-noncanonical", replace_slice(m6, frame["history_start"], frame["history_end"], b"\x80\x00")),
        ("m6-varint-overflow", replace_slice(m6, frame["history_start"], frame["history_end"], b"\xff" * 9 + b"\x02")),
        ("m6-mode", m6[: frame["mode_pos"]] + bytes([21]) + m6[frame["mode_pos"] + 1 :]),
        ("m6-source-zero", replace_slice(m6, frame["source_start"], frame["source_end"], b"\x00")),
        ("m6-source-total", replace_slice(m6, frame["source_start"], frame["source_end"], encode_varint(m6_info["n"] + 1))),
        (
            "m6-payload-cap",
            m6[: frame["source_start"]]
            + encode_varint(1)
            + m6[frame["source_end"] : frame["payload_start"]]
            + encode_varint(8 * 1 + 4097)
            + m6[frame["payload_end"] :],
        ),
        ("m6-payload-truncated", m6[: frame["body_end"] - 1] + m6[frame["body_end"] :]),
        ("m6-footer-length", replace_slice(m6, frame["footer_start"], frame["footer_end"], encode_varint(m6_info["n"] + 1))),
        ("m6-footer-crc", m6[: frame["footer_crc"]] + bytes([m6[frame["footer_crc"]] ^ 1]) + m6[frame["footer_crc"] + 1 :]),
        ("m6-tail", m6 + b"\0"),
    ]
    for name, payload in m6_changes:
        records["malformed"].append(rejected(wrapper, cix, checks, name, replace_payload(m6_archive, payload)))

    zstd_archive = seeds[1][1]
    zstd_info = seeds[1][2]
    concatenated = zstd_info["payload"] + zstd_info["payload"]
    if 25 + zstd_info["width"] + len(concatenated) <= MAX_ARCHIVE:
        records["malformed"].append(rejected(wrapper, cix, checks, "zstd-concatenated", replace_payload(zstd_archive, concatenated)))
    else:
        records["malformed"].append(rejected(wrapper, cix, checks, "zstd-trailing", replace_payload(zstd_archive, zstd_info["payload"] + b"\0")))
    changed = bytearray(zstd_archive)
    require(zstd_info["n"] > zstd_info["width"], "zstd content fixture")
    changed[6:14] = struct.pack("<II", zstd_info["n"] - 1, zstd_info["n"] - 1)
    records["malformed"].append(rejected(wrapper, cix, checks, "zstd-content-size", bytes(changed)))
    large_window_frame = bytes.fromhex("28b52ffd8088") + struct.pack("<I", 1) + bytes.fromhex("09000000")
    window_archive = make_outer(1, b"\0", 1, 0, [0], large_window_frame)
    window_record = rejected(wrapper, cix, checks, "zstd-window", window_archive)
    require("zstd frame bounds" in window_record["run"]["stderr"], "window guard diagnostic")
    records["malformed"].append(window_record)

    native_archive = seeds[2][1]
    native_info = seeds[2][2]
    native = native_info["payload"]
    route_offset = native_info["phase"]
    require(route_offset + 9 <= len(native), "native seed")
    changed = bytearray(native)
    changed[route_offset] = 255
    records["malformed"].append(rejected(wrapper, cix, checks, "native-route", replace_payload(native_archive, bytes(changed))))
    changed = bytearray(native)
    decoded = struct.unpack_from("<I", changed, route_offset + 1)[0]
    struct.pack_into("<I", changed, route_offset + 1, decoded + 1)
    records["malformed"].append(rejected(wrapper, cix, checks, "native-decoded-length", replace_payload(native_archive, bytes(changed))))
    changed = bytearray(native)
    struct.pack_into("<I", changed, route_offset + 5, MAX_ARCHIVE)
    records["malformed"].append(rejected(wrapper, cix, checks, "native-payload-length", replace_payload(native_archive, bytes(changed))))
    records["malformed"].append(rejected(wrapper, cix, checks, "native-trailing", replace_payload(native_archive, native + b"\0")))
    oversized_huffman = bytearray(19)
    oversized_huffman[0] = 1
    oversized_huffman[3:11] = (MAX_SOURCE + 1).to_bytes(8, "little")
    native_huffman_body = bytes([1]) + struct.pack("<II", 1, len(oversized_huffman)) + oversized_huffman
    native_huffman_archive = make_outer(2, b"\0", 1, 0, [0], native_huffman_body)
    huffman_record = rejected(wrapper, cix, checks, "native-huffman-embedded-length", native_huffman_archive)
    require("huffman header" in huffman_record["run"]["stderr"], "Huffman preallocation guard diagnostic")
    records["malformed"].append(huffman_record)

    records["status"] = "passed"
    records["summary"] = {
        "independent_cases": len(records["independent"]),
        "fresh_decodes": len(records["fresh_decodes"]),
        "malformed_rejections": len(records["malformed"]),
    }
    return records


def main() -> None:
    require(len(sys.argv) == 5, "usage: check.py WRAPPER CIX WORK OUTJSON")
    wrapper, cix, work, output = map(Path, sys.argv[1:])
    try:
        result = run_checks(wrapper.resolve(), cix.resolve(), work.resolve())
    except Exception as error:
        result = {"status": "failed", "error": repr(error)}
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2) + "\n")
        raise
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
