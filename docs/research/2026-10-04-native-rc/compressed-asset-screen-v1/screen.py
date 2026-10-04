#!/usr/bin/env python3
"""Bounded exact recompression experiment; never modifies its source archives."""
import hashlib
import importlib.util
import json
import lzma
import math
import os
import pathlib
import struct
import subprocess
import sys
import time
import zlib

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OUT = ROOT / "benchmark-work/compressed-asset-screen-v1"
SPEC = importlib.util.spec_from_file_location("finite_math", HERE.parent / "representation-feasibility/evaluate.py")
MATH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MATH)
CODECS = {0: "raw", 1: "zlib9", 2: "xz1"}
METHODS = {0: "identity", 1: "generator", 2: "sqrt", 3: "cube_root", 4: "reciprocal", 5: "math_description"}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def compress(data, codec):
    return zlib.compress(data, 9) if codec == 1 else lzma.compress(data, preset=1)


def decompress(data, codec):
    if codec == 0:
        return data
    if codec == 1:
        return zlib.decompress(data)
    if codec == 2:
        return lzma.decompress(data)
    raise ValueError("unknown codec")


def gen_params(kind, seed, offset, operation):
    return bytes([kind]) + seed + struct.pack(">HB", offset, operation)


def gen_transform(data, params, inverse=False):
    size = 1 if params[0] == 0 else 32
    assert len(params) == size + 4
    seed = params[1:1 + size]
    offset, width = struct.unpack(">HB", params[1 + size:])
    reference = hashlib.shake_256(b"CIX-asset-screen-v1:" + seed).digest(len(data) + offset)[offset:]
    if width == 0:
        return (int.from_bytes(data, "big") ^ int.from_bytes(reference, "big")).to_bytes(len(data), "big")
    assert width in (1, 2, 4) and len(data) % width == 0
    modulus = 1 << (8 * width)
    result = bytearray()
    for i in range(0, len(data), width):
        left = int.from_bytes(data[i:i + width], "big")
        right = int.from_bytes(reference[i:i + width], "big")
        value = (left + right if inverse else left - right) % modulus
        result.extend(value.to_bytes(width, "big"))
    return bytes(result)


def projection(data, method, inverse=False):
    width = (9 if method == 4 else 5) if inverse else 4
    assert len(data) % width == 0
    result = bytearray()
    for i in range(0, len(data), width):
        value = int.from_bytes(data[i:i + width], "big")
        if not inverse:
            if method == 2:
                q = math.isqrt(value << 34)
            elif method == 3:
                q = MATH.root_floor(value << 69, 3)
            else:
                q = (1 << 64) // (value + 1)
            result.extend(q.to_bytes(9 if method == 4 else 5, "big"))
        else:
            if method in (2, 3):
                k, shift = (2, 34) if method == 2 else (3, 69)
                scale = 1 << shift
                lower = (value ** k + scale - 1) // scale
                upper = ((value + 1) ** k - 1) // scale
                lower, upper = max(0, lower), min((1 << 32) - 1, upper)
                assert lower == upper
                original = lower
            else:
                assert value > 0
                lower = (1 << 64) // (value + 1) + 1
                upper = min((1 << 64) // value, 1 << 32)
                assert lower == upper
                original = lower - 1
            result.extend(original.to_bytes(4, "big"))
    return bytes(result)


def math_transform(data, tables):
    out = bytearray()
    counts = {}
    for i in range(0, len(data), 32):
        value = int.from_bytes(data[i:i + 32], "big")
        family, code = MATH.select(MATH.candidates(value, 256, tables))
        frame, _ = MATH.encode(256, code)
        assert 0 < len(frame) <= 255
        out.append(len(frame))
        out.extend(frame)
        counts[family] = counts.get(family, 0) + 1
    return bytes(out), counts


def inverse(data, method, params):
    if method == 0:
        assert not params
        return data
    if method == 1:
        return gen_transform(data, params, inverse=True)
    assert not params
    if method in (2, 3, 4):
        return projection(data, method, inverse=True)
    if method == 5:
        out, pos = bytearray(), 0
        while pos < len(data):
            length = data[pos]
            pos += 1
            n, value = MATH.decode(data[pos:pos + length])
            assert n == 256
            out.extend(value.to_bytes(32, "big"))
            pos += length
        assert pos == len(data)
        return bytes(out)
    raise ValueError("unknown method")


def whole_frame(data, codec, encoded):
    return b"RXP1" + struct.pack(">QB", len(data), int(codec != 0)) + (bytes([codec]) if codec else b"") + encoded


def patch_frame(data, candidate):
    offset, length = candidate["offset"], candidate["window_bytes"]
    params, encoded = candidate["params"], candidate["encoded"]
    header = b"RXP1" + struct.pack(">QBQIBBIH", len(data), 2, offset, length,
        candidate["method"], candidate["codec"], len(encoded), len(params))
    result = header + params + data[:offset] + encoded + data[offset + length:]
    assert len(result) == candidate["complete_bytes"]
    return result


def decode_frame(frame):
    assert frame[:4] == b"RXP1" and len(frame) >= 13
    n, kind = struct.unpack(">QB", frame[4:13])
    if kind in (0, 1):
        out = frame[13:] if kind == 0 else decompress(frame[14:], frame[13])
    else:
        assert kind == 2 and len(frame) >= 33
        offset, length, method, codec, count, plen = struct.unpack(">QIBBIH", frame[13:33])
        assert offset + length <= n
        params = frame[33:33 + plen]
        body = frame[33 + plen:]
        assert len(body) == n - length + count
        encoded = body[offset:offset + count]
        restored = inverse(decompress(encoded, codec), method, params)
        assert len(restored) == length
        out = body[:offset] + restored + body[offset + count:]
    assert len(out) == n
    return out


def public_candidate(candidate):
    return {k: v.hex() if k == "params" else v for k, v in candidate.items() if k != "encoded"}


def verify_fresh(frame, name, expected):
    path = OUT / (name + ".rxp")
    restored = OUT / (name + ".restored")
    path.write_bytes(frame)
    start = time.perf_counter()
    proc = subprocess.run([sys.executable, str(pathlib.Path(__file__).resolve()),
        "decode", str(path), str(restored)], capture_output=True, text=True, check=True)
    elapsed = time.perf_counter() - start
    readback = restored.read_bytes()
    assert digest(readback) == expected
    restored.unlink()
    return {"path": str(path), "bytes": len(frame), "sha256": digest(frame),
            "restored_sha256": digest(readback), "fresh_decode_wall_seconds": elapsed,
            "decoder_stdout": proc.stdout.strip()}


def run():
    started = time.perf_counter()
    plan = json.loads((HERE / "plan.json").read_text())
    OUT.mkdir(parents=True, exist_ok=True)
    assert not list(OUT.glob("*.rxp")), "Preserve previous runs; no overwrite"
    entries, target_values = [], set()
    for entry in plan["inputs"]:
        data = pathlib.Path(entry["path"]).read_bytes()
        assert len(data) == entry["bytes"] and digest(data) == entry["sha256"]
        offsets = [0, ((len(data) // 2) // 4096) * 4096, len(data) - 4096]
        entries.append((entry, offsets))
        for offset in offsets:
            window = data[offset:offset + 4096]
            target_values.update(int.from_bytes(window[i:i + 32], "big") for i in range(0, 4096, 32))
    tables, setup = MATH.build_tables(256, target_values)
    results = {"plan_sha256": digest((HERE / "plan.json").read_bytes()),
               "script_sha256": digest(pathlib.Path(__file__).read_bytes()),
               "math_evaluator_sha256": digest((HERE.parent / "representation-feasibility/evaluate.py").read_bytes()),
               "python": sys.version, "zlib_runtime": zlib.ZLIB_RUNTIME_VERSION,
               "scope": "Existing compressed assets; fixed windows; one-patch wrappers; not full-domain qualification",
               "math_setup": setup, "assets": []}
    for entry, offsets in entries:
        asset_start = time.perf_counter()
        data = pathlib.Path(entry["path"]).read_bytes()
        assert digest(data) == entry["sha256"]
        print("starting " + entry["cell"], flush=True)
        whole = []
        best_control_frame = whole_frame(data, 0, data)
        best_control = {"scope": "whole", "method": "raw", "complete_bytes": len(best_control_frame)}
        for codec in (1, 2):
            t = time.perf_counter()
            encoded = compress(data, codec)
            frame = whole_frame(data, codec, encoded)
            assert decode_frame(frame) == data
            item = {"scope": "whole", "method": CODECS[codec], "encoded_payload_bytes": len(encoded),
                    "complete_bytes": len(frame), "encode_and_inprocess_verify_seconds": time.perf_counter() - t}
            whole.append(item)
            if len(frame) < len(best_control_frame):
                best_control_frame, best_control = frame, item
        windows, best_theory = [], None
        for label, offset in zip(("start", "middle", "tail"), offsets):
            window = data[offset:offset + 4096]
            candidates, block_counts = [], {}
            best_by_method = {}

            def examine(transformed, method, params, label_id):
                nonlocal best_theory, best_control, best_control_frame
                for codec in (1, 2):
                    encoded = compress(transformed, codec)
                    assert inverse(decompress(encoded, codec), method, params) == window
                    candidate = {"id": label_id + "/" + CODECS[codec], "offset": offset,
                        "window_bytes": len(window), "method": method, "codec": codec,
                        "params": params, "transformed_bytes": len(transformed),
                        "encoded": encoded, "encoded_bytes": len(encoded),
                        "complete_bytes": len(data) - len(window) + len(encoded) + 33 + len(params)}
                    candidates.append(public_candidate(candidate))
                    previous = best_by_method.get(method)
                    if previous is None or candidate["complete_bytes"] < previous["complete_bytes"]:
                        best_by_method[method] = candidate
                    if method and (best_theory is None or candidate["complete_bytes"] < best_theory["complete_bytes"]):
                        best_theory = candidate
                    if not method and candidate["complete_bytes"] < len(best_control_frame):
                        best_control_frame = patch_frame(data, candidate)
                        best_control = public_candidate(candidate)

            examine(window, 0, b"", "identity")
            for method in (2, 3, 4):
                examine(projection(window, method), method, b"", METHODS[method])
            mathematical, block_counts = math_transform(window, tables)
            examine(mathematical, 5, b"", "math_description")
            seeds = [(0, bytes([s]), "literal" + str(s)) for s in range(8)]
            seeds.append((1, hashlib.sha256(window).digest(), "stored_window_sha256"))
            for kind, seed, seedname in seeds:
                for gen_offset in (0, 1, 16, 256):
                    for operation in (0, 1, 2, 4):
                        params = gen_params(kind, seed, gen_offset, operation)
                        transformed = gen_transform(window, params)
                        examine(transformed, 1, params, f"gen/{seedname}/offset{gen_offset}/operation{operation}")
            windows.append({"label": label, "offset": offset, "bytes": len(window),
                "sha256": digest(window), "math_selected_families": block_counts,
                "candidate_count": len(candidates), "candidates": candidates,
                "best_by_method": {METHODS[k]: public_candidate(v) for k, v in best_by_method.items()}})
        control_certificate = verify_fresh(best_control_frame, entry["cell"] + "-control", entry["sha256"])
        theory_certificate = verify_fresh(patch_frame(data, best_theory), entry["cell"] + "-theory", entry["sha256"])
        result = {"source": entry, "whole_second_pass_controls": whole, "windows": windows,
            "best_control": best_control, "best_theory": public_candidate(best_theory),
            "control_certificate": control_certificate, "theory_certificate": theory_certificate,
            "theory_saving_vs_unchanged_bytes": len(data) - best_theory["complete_bytes"],
            "theory_saving_vs_best_wrapped_control_bytes": len(best_control_frame) - best_theory["complete_bytes"],
            "asset_total_wall_seconds": time.perf_counter() - asset_start}
        results["assets"].append(result)
        (HERE / "results.json").write_text(json.dumps(results, separators=(",", ":")) + "\n")
        print(json.dumps({"completed": entry["cell"], "input_bytes": len(data),
            "control_bytes": len(best_control_frame), "theory_bytes": best_theory["complete_bytes"],
            "theory_method": METHODS[best_theory["method"]], "seconds": result["asset_total_wall_seconds"]}), flush=True)
    results["elapsed_seconds"] = time.perf_counter() - started
    results["all_candidate_windows_roundtrip"] = True
    results["independent_full_frame_decodes"] = 6
    results["retained_wrapper_bytes"] = sum(f.stat().st_size for f in OUT.glob("*.rxp"))
    results["evaluated_candidate_windows"] = sum(w["candidate_count"] for a in results["assets"] for w in a["windows"])
    (HERE / "results.json").write_text(json.dumps(results, separators=(",", ":")) + "\n")
    print(json.dumps({"finished": True, "seconds": results["elapsed_seconds"],
        "candidate_windows": results["evaluated_candidate_windows"]}), flush=True)


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "decode":
        value = decode_frame(pathlib.Path(sys.argv[2]).read_bytes())
        pathlib.Path(sys.argv[3]).write_bytes(value)
        print(json.dumps({"bytes": len(value), "sha256": digest(value)}))
    else:
        run()
