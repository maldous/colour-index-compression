"""CIXG1: bounded, byte-observable adaptive compression, with paid substreams.

The original research stream remains unchanged. No filename or format detector
is reachable here. Expensive trials execute in isolated, deadline-limited workers.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import multiprocessing as mp
import resource
import struct
import time
import zlib
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .multinomial import (decode_type_class_known_n, encode_type_class_known_n,
    _counts, multinomial_cardinality, _range_encode_type_sequence)

MAGIC = b"CIXG1"
HEADER = struct.Struct("<5sII")
FRAME = struct.Struct("<BII32s")
STREAM = struct.Struct("<BII")
END = 255
TILE = 1024                 # exact ranks have at most 8192 bits, never input-sized
MAX_BLOCK = 65536
ROUTES = {0: "raw", 1: "runs", 2: "composition", 3: "lz", 4: "predictor",
          5: "bwt", 6: "stride", 7: "phrases", 8: "ppm", 9: "mixture", 10: "deflate"}
CODERS = {0: "raw", 1: "runs", 2: "cix-exact-1024", 3: "deflate", 4: "adaptive-range",
          5: "same-count-range-1024"}


@dataclass(frozen=True)
class Effort:
    block_bytes: int
    sample_bytes: int
    candidate_limit: int
    search_seconds: float
    trial_seconds: float
    worker_memory_mib: int


# Fixed before held-out evaluation. Budgets are ceilings, not speed promises.
EFFORTS = {
    "fast": Effort(32768, 2048, 4, 0.75, 0.30, 256),
    "balanced": Effort(32768, 4096, 7, 3.0, 1.0, 384),
    "maximum": Effort(65536, 8192, 10, 12.0, 4.0, 512),
}


def _v(x: int) -> bytes:
    out = bytearray()
    while x >= 128:
        out.append((x & 127) | 128); x >>= 7
    out.append(x)
    return bytes(out)


def _readv(b: bytes, p: int) -> tuple[int, int]:
    value = 0
    for shift in range(0, 35, 7):
        if p >= len(b): raise ValueError("truncated integer")
        c = b[p]; p += 1; value |= (c & 127) << shift
        if c < 128: return value, p
    raise ValueError("oversized integer")


def _entropy(b: bytes) -> float:
    if not b: return 0.0
    n = len(b)
    return math.log2(n) - sum(c * math.log2(c) for c in Counter(b).values()) / n


def profile(data: bytes, cap: int) -> dict:
    # Spread probes across the block; adjacency never bridges probe boundaries.
    width = max(1, cap // 4)
    starts = sorted(set((0, len(data)//3, 2*len(data)//3, max(0, len(data)-width))))
    parts = [data[s:s+width] for s in starts]
    sample = b"".join(parts)
    run_equal = sum(sum(a == b for a, b in zip(p, p[1:])) for p in parts)
    seen = set(); repeats = 0; keys = 0
    for p in parts:
        for i in range(max(0, len(p)-3)):
            k = p[i:i+4]; repeats += k in seen; seen.add(k); keys += 1
    lags = {}
    for lag in (1, 2, 4, 8, 16, 32, 64):
        residual = b"".join(bytes(p[i] ^ p[i-lag] for i in range(lag, len(p))) for p in parts)
        lags[lag] = _entropy(residual)
    contexts = {}; hits = opportunities = 0
    for p in parts:
        for i in range(2, len(p)):
            k = p[i-2:i]
            if k in contexts: opportunities += 1; hits += contexts[k] == p[i]
            contexts[k] = p[i]
    return {"sample_bytes": len(sample), "entropy": _entropy(sample),
            "symbols": len(set(sample)), "run_fraction": run_equal / max(1, len(sample)-len(parts)),
            "repeat_fraction": repeats / max(1, keys), "lag_entropy": lags,
            "predictability": hits / max(1, opportunities),
            "regional_entropy_range": max(map(_entropy, parts)) - min(map(_entropy, parts))}


def _rle(data: bytes) -> bytes:
    out = bytearray(); i = 0
    while i < len(data):
        j = i + 1
        while j < len(data) and data[j] == data[i]: j += 1
        out.append(data[i]); out += _v(j-i); i = j
    return bytes(out)


def _unrle(blob: bytes, n: int) -> bytes:
    out = bytearray(); p = 0
    while p < len(blob):
        c = blob[p]; length, p = _readv(blob, p+1)
        if not length or len(out)+length > n: raise ValueError("invalid run")
        out.extend(bytes((c,))*length)
    if len(out) != n: raise ValueError("run length mismatch")
    return bytes(out)


def _cix(data: bytes) -> bytes:
    out = bytearray()
    for s in range(0, len(data), TILE):
        payload = encode_type_class_known_n(data[s:s+TILE])
        out += _v(len(payload)); out += payload
    return bytes(out)


def _uncix(blob: bytes, n: int) -> bytes:
    out = bytearray(); p = 0
    while len(out) < n:
        size, p = _readv(blob, p); end = p + size
        if end > len(blob): raise ValueError("truncated composition")
        piece, used = decode_type_class_known_n(blob[p:end], 0, min(TILE, n-len(out)))
        if used != size: raise ValueError("composition trailing bytes")
        out += piece; p = end
    if p != len(blob): raise ValueError("composition length mismatch")
    return bytes(out)


def _count_range(data: bytes) -> bytes:
    # Experimental matched-information control: identical paid alphabet and
    # counts; only the ordering encoder is replaced. Construction includes the
    # incumbent rank computation and is NOT a fair speed control for range.
    out = bytearray()
    for s in range(0, len(data), TILE):
        tile = data[s:s+TILE]; counts = _counts(tile)
        exact = encode_type_class_known_n(tile)
        width = (multinomial_cardinality(counts)-1).bit_length()
        sequence_bytes = (width+7)//8
        header = exact[:len(exact)-sequence_bytes-1]
        payload, bits = _range_encode_type_sequence(tile, counts)
        encoded = header+b"\x01"+_v(bits)+payload
        out += _v(len(encoded)); out += encoded
    return bytes(out)


def _deflate(data: bytes) -> bytes:
    obj = zlib.compressobj(6, zlib.DEFLATED, -15)
    return obj.compress(data) + obj.flush()


def _inflate(blob: bytes, n: int) -> bytes:
    obj = zlib.decompressobj(-15)
    out = obj.decompress(blob, n+1)
    if len(out) != n or not obj.eof or obj.unused_data or obj.unconsumed_tail:
        raise ValueError("deflate length/framing mismatch")
    return out


def streams(parts: list[bytes], backend: str) -> bytes:
    out = bytearray((len(parts),))
    for part in parts:
        candidates = [(0, part), (1, _rle(part))]
        if backend in ("cix", "hybrid"):
            # Count overhead makes dense high-entropy local composition unlikely.
            # This gate does NOT bypass repeat/transform routes at the input level.
            if _entropy(part[:8192]) < 7.5:
                candidates.append((2, _cix(part)))
        if backend in ("deflate", "hybrid"):
            candidates.append((3, _deflate(part)))
        if backend == "range":
            from .adaptive import encode_adaptive
            candidates.append((4, encode_adaptive(part, order=0)))
        if backend == "count-range": candidates.append((5, _count_range(part)))
        coder, payload = min(candidates, key=lambda c: len(c[1]))
        out += STREAM.pack(coder, len(part), len(payload)); out += payload
    return bytes(out)


def unstreams(blob: bytes, limit: int) -> list[bytes]:
    if not blob or not 1 <= blob[0] <= 8: raise ValueError("invalid substream count")
    out = []; p = 1; total = 0
    for _ in range(blob[0]):
        if p+STREAM.size > len(blob): raise ValueError("truncated substream descriptor")
        coder, n, size = STREAM.unpack_from(blob, p); p += STREAM.size
        total += n
        if total > limit or p+size > len(blob): raise ValueError("substream resource limit")
        b = blob[p:p+size]; p += size
        if coder == 0:
            if len(b) != n: raise ValueError("raw substream length mismatch")
            part = b
        elif coder == 1: part = _unrle(b, n)
        elif coder in (2,5): part = _uncix(b, n)
        elif coder == 3: part = _inflate(b, n)
        elif coder == 4:
            from .adaptive import decode_adaptive
            if len(b) < 3 or b[1:3] != bytes((0, 8)):
                raise ValueError("unbounded range model")
            part = decode_adaptive(b, source_length=n)
        else: raise ValueError("unknown substream coder")
        out.append(part)
    if p != len(blob): raise ValueError("trailing substream bytes")
    return out


def accounting(route: str, blob: bytes, n: int) -> dict:
    result = {"framing_bytes": FRAME.size, "structural_bytes": 0,
              "stream_descriptor_bytes": 0, "count_table_bytes": 0,
              "coded_payload_bytes": len(blob), "coders": []}
    if route not in ("composition","deflate","lz","predictor","bwt","stride","phrases"):
        return result
    offset = 4 if route == "bwt" else 1 if route == "stride" else 1+2*blob[0] if route == "phrases" else 0
    result["structural_bytes"] = offset
    result["stream_descriptor_bytes"] = 1
    result["coded_payload_bytes"] = 0
    p = offset+1
    for _ in range(blob[offset]):
        coder, count, size = STREAM.unpack_from(blob,p); p += STREAM.size
        result["coders"].append(CODERS[coder]); result["stream_descriptor_bytes"] += STREAM.size
        part = blob[p:p+size]; p += size; metadata = 0; tile_overhead = 0
        if coder in (2,5):
            q = 0; remaining = count
            while remaining:
                start = q; tile_size, q = _readv(part,q); tile_start = q
                m, r = _readv(part,q); local_n = min(TILE,remaining)
                if m < 256: r += ((math.comb(256,m)-1).bit_length()+7)//8
                if m > 1: r += ((math.comb(local_n-1,m-1)-1).bit_length()+7)//8
                metadata += r-tile_start
                mode = part[r]; r += 1
                tile_overhead += q-start+1
                if mode == 1:
                    bit_start = r; _, r = _readv(part,r)
                    tile_overhead += r-bit_start
                q += tile_size; remaining -= local_n
            result["count_table_bytes"] += metadata
            result["stream_descriptor_bytes"] += tile_overhead
        result["coded_payload_bytes"] += size-metadata-tile_overhead
    assert sum(result[k] for k in ("structural_bytes","stream_descriptor_bytes","count_table_bytes","coded_payload_bytes")) == len(blob)
    return result


def _residual(data: bytes, inverse: bool = False) -> bytes:
    # A causal three-expert mixture: previous byte, lag-four, and the most
    # recent successor of the previous two bytes. Scores decay every 256 bytes.
    values = bytearray(65536); valid = bytearray(65536)
    scores = [0, 0, 0]; out = bytearray()
    for i, value in enumerate(data):
        past = out if inverse else data
        context = past[i-2]*256+past[i-1] if i >= 2 else 0
        predictions = [past[i-1] if i else 0, past[i-4] if i >= 4 else 0,
                       values[context] if i >= 2 and valid[context] else 0]
        winner = max(range(3), key=lambda k: scores[k])
        actual = value ^ predictions[winner] if inverse else value
        out.append(actual if inverse else value ^ predictions[winner])
        for k, predicted in enumerate(predictions): scores[k] += predicted == actual
        if i >= 2: values[context] = actual; valid[context] = 1
        if (i+1) % 256 == 0: scores = [s//2 for s in scores]
    return bytes(out)


def _bwt(data: bytes) -> tuple[int, bytes]:
    # Bounded prefix-doubling suffix sort; unlike the legacy Python fallback,
    # never allocate all suffix strings (quadratic temporary storage).
    n = len(data)
    if not n: return 0, b""
    sa = list(range(n)); rank = list(data); width = 1
    while True:
        sa.sort(key=lambda i: (rank[i], rank[i+width] if i+width < n else -1))
        new = [0]*n; classes = 0; previous = None
        for i in sa:
            pair = (rank[i], rank[i+width] if i+width < n else -1)
            if previous is not None and pair != previous: classes += 1
            new[i] = classes; previous = pair
        rank = new
        if classes == n-1: break
        width *= 2
    primary = sa.index(0)+1
    return primary, bytes((data[-1],)) + bytes(data[i-1] for i in sa if i)


def _mtf_runs(data: bytes) -> list[bytes]:
    from .bwt import mtf_encode
    mtf = mtf_encode(data); tags = bytearray(); literals = bytearray(); lengths = bytearray(); i = 0
    while i < len(mtf):
        if mtf[i] == 0:
            j = i+1
            while j < len(mtf) and mtf[j] == 0: j += 1
            tags.append(1); lengths += _v(j-i); i = j
        else: tags.append(0); literals.append(mtf[i]); i += 1
    return [bytes(tags), bytes(literals), bytes(lengths)]


def _unmtf_runs(parts: list[bytes], n: int) -> bytes:
    from .bwt import mtf_decode
    if len(parts) != 3: raise ValueError("MTF substream count")
    tags, literals, lengths = parts; a = b = 0; out = bytearray()
    for tag in tags:
        if tag == 1:
            count, b = _readv(lengths, b)
            if not count or len(out)+count > n: raise ValueError("MTF run overflow")
            out.extend(b"\x00"*count)
        elif tag == 0 and a < len(literals): out.append(literals[a]); a += 1
        else: raise ValueError("MTF tag/literal mismatch")
        if len(out) > n: raise ValueError("MTF size overflow")
    if len(out) != n or a != len(literals) or b != len(lengths): raise ValueError("MTF lengths")
    return mtf_decode(bytes(out))


def _stride(data: bytes) -> tuple[int, bytes]:
    from .transforms import SPEC_BY_ID, apply_transform
    sample = data[:4096]
    # Numeric widths and endian options are general byte relationships, not
    # semantic data types. Pin this six-probe shortlist before validation.
    ids = (4, 6, 7, 9, 17, 18)
    chosen = min(ids, key=lambda i: _entropy(apply_transform(sample, SPEC_BY_ID[i])))
    return chosen, apply_transform(data, SPEC_BY_ID[chosen])


def _phrases(data: bytes) -> tuple[bytes, list[bytes]]:
    counts = Counter(data[i:i+2] for i in range(len(data)-1))
    dictionary = [k for k, c in counts.most_common(32) if c >= 8]
    lookup = {k: i for i, k in enumerate(dictionary)}
    tags = bytearray(); literals = bytearray(); indices = bytearray(); i = 0
    while i < len(data):
        key = data[i:i+2]
        if key in lookup: tags.append(1); indices.append(lookup[key]); i += 2
        else: tags.append(0); literals.append(data[i]); i += 1
    return bytes((len(dictionary),))+b"".join(dictionary), [bytes(tags), bytes(literals), bytes(indices)]


def route_encode(route: str, data: bytes, backend: str, history: bytes = b"") -> bytes:
    if route == "raw": return data
    if route == "runs": return _rle(data)
    if route == "composition": return streams([data], "cix")
    if route == "deflate": return streams([data], "deflate")
    if route == "predictor": return streams([_residual(data)], backend)
    if route == "stride":
        spec, transformed = _stride(data)
        from .transforms import SPEC_BY_ID
        width = SPEC_BY_ID[spec].width if SPEC_BY_ID[spec].shuffle else 1
        plane = len(transformed)//width
        parts = [transformed[k*plane:(k+1)*plane] for k in range(width-1)] + [transformed[(width-1)*plane:]]
        return bytes((spec,)) + streams(parts, backend)
    if route == "lz":
        from .lz import parse_lz
        parsed = parse_lz(data, prefix_history=history, window=65536, chain=8, max_match=65535)
        return streams([parsed.tags, parsed.literals, b"".join(_v(x) for x in parsed.lengths),
                        b"".join(_v(x) for x in parsed.distances)], backend)
    if route == "bwt":
        primary, transformed = _bwt(data)
        return struct.pack("<I", primary) + streams(_mtf_runs(transformed), backend)
    if route == "phrases":
        dictionary, parts = _phrases(data)
        return dictionary + streams(parts, backend)
    if route == "ppm":
        from .ppm import encode_ppm
        return encode_ppm(data, max_order=3, escape_method=0, update_exclusion=False,
                          secondary_escape=False)
    if route == "mixture":
        from .fixedmix import encode_fixed_mix
        return encode_fixed_mix(data)
    raise ValueError("unknown route")


def route_decode(route: str, blob: bytes, n: int, history: bytes = b"") -> bytes:
    if route == "raw":
        if len(blob) != n: raise ValueError("raw block size")
        return blob
    if route == "runs": return _unrle(blob, n)
    if route in ("composition", "deflate", "predictor"):
        parts = unstreams(blob, n)
        if len(parts) != 1 or len(parts[0]) != n: raise ValueError("single stream size")
        return _residual(parts[0], True) if route == "predictor" else parts[0]
    if route == "stride":
        from .transforms import SPEC_BY_ID, invert_transform
        if not blob or blob[0] not in (4, 6, 7, 9, 17, 18): raise ValueError("invalid stride")
        data = b"".join(unstreams(blob[1:], n))
        if len(data) != n: raise ValueError("stride size")
        return invert_transform(data, SPEC_BY_ID[blob[0]])
    if route == "bwt":
        from .bwt import bwt_inverse
        if len(blob) < 4: raise ValueError("truncated BWT primary")
        transformed = _unmtf_runs(unstreams(blob[4:], 4*n), n)
        return bwt_inverse(struct.unpack_from("<I", blob)[0], transformed)
    if route == "lz":
        parts = unstreams(blob, 4*n)
        if len(parts) != 4: raise ValueError("LZ stream count")
        tags, literals, lengths, distances = parts; a = b = c = 0; out = bytearray(history)
        for tag in tags:
            if tag == 0 and a < len(literals): out.append(literals[a]); a += 1
            elif tag == 1:
                length, b = _readv(lengths, b); distance, c = _readv(distances, c); length += 4
                if not 1 <= distance <= min(65536, len(out)) or len(out)-len(history)+length > n:
                    raise ValueError("invalid LZ match")
                for _ in range(length): out.append(out[-distance])
            else: raise ValueError("invalid LZ tag")
            if len(out)-len(history) > n: raise ValueError("LZ output overflow")
        if len(out)-len(history) != n or (a,b,c) != (len(literals),len(lengths),len(distances)):
            raise ValueError("LZ lengths")
        return bytes(out[len(history):])
    if route == "phrases":
        if not blob or blob[0] > 32: raise ValueError("phrase dictionary size")
        count = blob[0]; start = 1+2*count
        if start > len(blob): raise ValueError("truncated dictionary")
        dictionary = [blob[1+2*i:3+2*i] for i in range(count)]
        parts = unstreams(blob[start:], 2*n)
        if len(parts) != 3: raise ValueError("phrase streams")
        tags, literals, indices = parts; a = b = 0; out = bytearray()
        for tag in tags:
            if tag == 0 and a < len(literals): out.append(literals[a]); a += 1
            elif tag == 1 and b < len(indices) and indices[b] < count:
                out += dictionary[indices[b]]; b += 1
            else: raise ValueError("invalid phrase tag/index")
            if len(out) > n: raise ValueError("phrase output overflow")
        if len(out) != n or a != len(literals) or b != len(indices): raise ValueError("phrase lengths")
        return bytes(out)
    if route == "ppm":
        from .ppm import decode_ppm
        if len(blob) < 2 or blob[1] > 3: raise ValueError("unbounded PPM order")
        return decode_ppm(blob, source_length=n)
    if route == "mixture":
        from .fixedmix import decode_fixed_mix
        return decode_fixed_mix(blob, source_length=n)
    raise ValueError("unknown route")


def shortlist(features: dict, effort: str) -> list[str]:
    # High histogram entropy does not veto LZ, BWT, prediction or stride tests.
    routes = ["runs", "deflate"]
    priorities = []
    if features["repeat_fraction"] > 0.01: priorities.append("lz")
    if min(features["lag_entropy"].values()) < features["entropy"]-0.20: priorities.append("stride")
    if features["predictability"] > 0.1: priorities.append("predictor")
    if features["symbols"] < 96 or features["entropy"] < 5.5: priorities.append("composition")
    priorities += ["lz", "bwt", "stride", "predictor", "phrases", "composition", "ppm", "mixture"]
    for route in priorities:
        if route not in routes: routes.append(route)
    return routes[:EFFORTS[effort].candidate_limit]


def _trial_worker(conn, route, data, backend, history, memory):
    try:
        resource.setrlimit(resource.RLIMIT_AS, (memory*1048576, memory*1048576))
        start = time.perf_counter()
        payload = route_encode(route, data, backend, history)
        conn.send((payload, time.perf_counter()-start, resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, None))
    except Exception as exc:
        conn.send((None, 0, 0, f"{type(exc).__name__}: {exc}"))
    finally: conn.close()


def trial(route: str, data: bytes, backend: str, history: bytes, seconds: float, memory: int) -> tuple:
    ctx = mp.get_context("fork"); parent, child = ctx.Pipe(False)
    proc = ctx.Process(target=_trial_worker, args=(child, route, data, backend, history, memory))
    started = time.perf_counter(); proc.start(); child.close()
    result = (None, 0, 0, "TIME_BUDGET")
    try:
        if parent.poll(max(0.0, seconds-(time.perf_counter()-started))):
            try: result = parent.recv()
            except EOFError: result = (None, 0, 0, "WORKER_EXIT")
    finally:
        if proc.is_alive(): proc.terminate()
        proc.join(); parent.close()
    return (*result, time.perf_counter()-started)


def encode_file(source: Path, destination: Path, *, effort="balanced", backend="hybrid",
                disable=(), force=None, history_bytes=0, block_bytes=None, offline=False,
                trace_path: Path | None = None) -> dict:
    policy = EFFORTS[effort]; block_bytes = block_bytes or policy.block_bytes
    if not 1 <= block_bytes <= MAX_BLOCK or history_bytes not in (0,65536): raise ValueError("block/history limit")
    if backend not in ("cix", "deflate", "hybrid", "range", "count-range"): raise ValueError("backend")
    if force is not None and force not in ROUTES.values(): raise ValueError("force route")
    records = []; whole = hashlib.sha256(); history = b""; offset = 0
    route_usage = Counter(); block_count = 0; selection_total = 0.0; selected_compute = 0.0
    begin = time.perf_counter(); last_progress = begin
    if trace_path: trace_path.write_text("")
    with source.open("rb") as src, destination.open("wb") as dst:
        dst.write(HEADER.pack(MAGIC, block_bytes, history_bytes))
        while data := src.read(block_bytes):
            block_begin = time.perf_counter(); features = profile(data, policy.sample_bytes)
            profiling_seconds = time.perf_counter()-block_begin
            best_route = "raw"; best = data; trials = []
            routes = ([force] if force else [r for r in ROUTES.values() if r != "raw"] if offline
                      else shortlist(features, effort))
            for route in routes:
                if route in disable: continue
                remaining = policy.search_seconds-(time.perf_counter()-block_begin)
                if remaining <= 0:
                    trials.append({"route": route, "status": "SEARCH_BUDGET"}); continue
                blob, compute, rss, error, wall = trial(route, data, backend, history,
                    min(policy.trial_seconds, remaining), policy.worker_memory_mib)
                trials.append({"route": route, "bytes": None if blob is None else len(blob)+FRAME.size,
                               "payload_bytes": None if blob is None else len(blob), "compute_seconds": compute,
                               "wall_seconds": wall, "peak_rss_kib": rss, "status": error or "COMPLETE",
                               "accounting": None if blob is None else accounting(route,blob,len(data))})
                if blob is not None and (force is not None or len(blob) < len(best)):
                    best_route, best = route, blob
            if force and best_route != force: raise RuntimeError(f"forced route did not complete: {trials}")
            route_id = next(i for i,r in ROUTES.items() if r == best_route)
            digest = hashlib.sha256(data).digest(); whole.update(data)
            dst.write(FRAME.pack(route_id, len(data), len(best), digest)); dst.write(best)
            elapsed = time.perf_counter()-block_begin
            record = {"offset": offset, "source_bytes": len(data), "route": best_route,
                "complete_block_bytes": FRAME.size+len(best), "features": features,
                "accounting": accounting(best_route,best,len(data)),
                "profiling_seconds": profiling_seconds, "selection_seconds": elapsed,
                "selected_trial_compute_seconds": next((t["compute_seconds"] for t in trials if t["route"] == best_route), 0),
                "trials": trials}
            if len(records) < 32: records.append(record)
            if trace_path:
                with trace_path.open("a") as trace: trace.write(json.dumps(record)+"\n")
            route_usage[best_route] += len(data); block_count += 1
            selection_total += elapsed; selected_compute += record["selected_trial_compute_seconds"]
            offset += len(data)
            history = (history+data)[-history_bytes:] if history_bytes else b""
            now = time.perf_counter()
            if now-last_progress >= 30:
                print(json.dumps({"phase":"encode", "processed_bytes": offset,
                      "elapsed_seconds":now-begin,"output_bytes":dst.tell()}), flush=True)
                last_progress = now
        dst.write(FRAME.pack(END, 0, 0, whole.digest()))
    return {"format":"CIXG1", "effort":effort, "backend":backend,
            "history_bytes":history_bytes, "block_bytes":block_bytes, "disable":list(disable),
            "force":force, "offline":offline, "source_bytes":offset,
            "compressed_bytes":destination.stat().st_size, "source_sha256":whole.hexdigest(),
            "encode_seconds":time.perf_counter()-begin, "blocks":records,
            "block_count":block_count, "route_usage_source_bytes":dict(route_usage),
            "selection_total_seconds":selection_total,
            "search_and_launch_overhead_seconds":selection_total-selected_compute,
            "blocks_truncated":block_count>len(records),
            "all_block_trace":str(trace_path) if trace_path else None}


def decode_file(source: Path, destination: Path) -> dict:
    whole = hashlib.sha256(); history = b""; total = 0; start = time.perf_counter()
    with source.open("rb") as src, destination.open("wb") as dst:
        header = src.read(HEADER.size)
        if len(header) != HEADER.size: raise ValueError("truncated archive")
        magic, block_bytes, history_bytes = HEADER.unpack(header)
        if magic != MAGIC or not 1 <= block_bytes <= MAX_BLOCK or history_bytes not in (0,65536):
            raise ValueError("unsupported CIX header")
        while True:
            frame = src.read(FRAME.size)
            if len(frame) != FRAME.size: raise ValueError("missing archive terminator")
            route, n, size, digest = FRAME.unpack(frame)
            if route == END:
                if n or size or digest != whole.digest() or src.read(1): raise ValueError("archive checksum/trailing bytes")
                break
            if route not in ROUTES or not 1 <= n <= block_bytes or size > 8*n+4096:
                raise ValueError("invalid block descriptor")
            blob = src.read(size)
            if len(blob) != size: raise ValueError("truncated block payload")
            data = route_decode(ROUTES[route], blob, n, history)
            if len(data) != n or hashlib.sha256(data).digest() != digest: raise ValueError("block checksum mismatch")
            dst.write(data); whole.update(data); total += n
            history = (history+data)[-history_bytes:] if history_bytes else b""
    return {"decoded_bytes":total, "decoded_sha256":whole.hexdigest(), "decode_seconds":time.perf_counter()-start}


def main(argv=None):
    parser = argparse.ArgumentParser(description="CIX generic adaptive pipeline")
    parser.add_argument("operation", choices=("encode","decode"))
    parser.add_argument("source", type=Path); parser.add_argument("destination", type=Path)
    parser.add_argument("--effort", choices=EFFORTS, default="balanced")
    parser.add_argument("--backend", choices=("cix","deflate","hybrid","range","count-range"), default="hybrid")
    parser.add_argument("--force", choices=ROUTES.values())
    parser.add_argument("--disable", action="append", default=[], choices=ROUTES.values())
    parser.add_argument("--history", type=int, choices=(0,65536), default=0)
    parser.add_argument("--block", type=int); parser.add_argument("--offline", action="store_true")
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args(argv)
    if args.source.resolve() == args.destination.resolve(): parser.error("input and output must differ")
    report = (encode_file(args.source,args.destination,effort=args.effort,backend=args.backend,
               disable=args.disable,force=args.force,history_bytes=args.history,block_bytes=args.block,offline=args.offline,
               trace_path=args.receipt.with_suffix(".blocks.jsonl") if args.receipt else None)
              if args.operation == "encode" else decode_file(args.source,args.destination))
    if args.receipt: args.receipt.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k != "blocks"}), flush=True)


if __name__ == "__main__": main()
