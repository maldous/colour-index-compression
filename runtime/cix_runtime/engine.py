"""Measured complete-archive selection with isolated, bounded candidate work."""
from __future__ import annotations

import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import resource
import signal
import struct
import tempfile
import time
import traceback

from .model import Candidate

RAW_MAGIC = b"CIXR1"
RAW_HEADER = struct.Struct("<5sQ32s")
MAX_INPUT = 128 << 20
DEFAULT_MEMORY = 11_000_000_000
NATIVE_MEMORY = 8_000_000_000
TEMPORARY_ADMISSION_BYTES = 4_000_000_000


def raw_encode(data: bytes) -> bytes:
    return RAW_HEADER.pack(RAW_MAGIC, len(data), hashlib.sha256(data).digest()) + data


def _native(data: bytes, profile: str, threads: int, memory: int) -> bytes:
    from .backends import native_encode
    return native_encode(data, profile=profile, threads=threads, memory_bytes=memory)


def catalog(data: bytes, profile: str, threads: int, memory: int) -> tuple[list[Candidate], list[dict]]:
    from . import backends, heterogeneous, specialized
    n = len(data)
    candidates = [Candidate("raw", "raw", raw_encode, 3*n + (32 << 20), 3*n + (32 << 20))]
    native_memory = min(NATIVE_MEMORY, max(64 << 20, memory - 12*n - (256 << 20)))
    candidates.append(Candidate(
        "native-" + profile, "native",
        lambda b: _native(b, profile, threads, native_memory),
        native_memory + 12*n + (128 << 20), native_memory + 6*n,
        threads=threads, parameters={"profile": profile, "backend_memory_bytes": native_memory}))
    diagnostics: list[dict] = []
    if profile == "best":
        for version, options, model_memory in (
            ("v216", "-8", 4_500_000_000),
            ("v215", "-8", 4_500_000_000),
            ("v215", "-9L", 5_000_000_000),
        ):
            ident = f"paq-{version}-{options[1:]}"
            candidates.append(Candidate(
                ident, "generic-paq",
                lambda b, v=version, o=options: backends.encode_paq(b, v, o),
                model_memory + 8*n, model_memory + 6*n,
                parameters={"version": version, "options": options, "simd": "AVX2"}))
    if profile in {"default", "best"}:
        extra, notes = specialized.catalog(data)
        diagnostics.extend(notes)
        for item in extra:
            if profile == "default" and "paq" in str(item.parameters.get("backend", "")).lower():
                diagnostics.append({"id": item.id, "family": item.family,
                                    "status": "profile-omitted",
                                    "reason": "DEFAULT omits PAQ-backed specialist trials"})
            else:
                candidates.append(item)
        extra, notes = heterogeneous.catalog(data, profile=profile)
        candidates.extend(extra)
        diagnostics.extend(notes)
    else:
        diagnostics.append({"family": "specialized", "status": "profile-omitted",
                            "reason": "FAST uses the native low-latency profile and raw fallback"})
    identifiers = [item.id for item in candidates]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("duplicate candidate identifiers")
    return candidates, diagnostics


def _save(path: Path, value: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")
    os.replace(temporary, path)


def _diagnostics(path: Path) -> object | None:
    """Return bounded backend diagnostics without trusting scratch-file shape."""
    if not path.is_file():
        return None
    text = path.read_bytes()[:64 * 1024].decode(errors="replace")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def _worker(item: Candidate, data: bytes, archive: str, receipt: str,
            diagnostics: str) -> None:
    os.setsid()
    before = time.perf_counter()
    row = item.description()
    diagnostic_path = Path(diagnostics)
    try:
        # This bounds a single output file before a backend can fill temporary
        # storage. Aggregate temporary/RAM/CPU enforcement belongs to the caller.
        file_limit = max(64 << 20, 16*len(data) + (32 << 20))
        resource.setrlimit(resource.RLIMIT_FSIZE, (file_limit, file_limit))
        # Bound virtual allocation as well as the outer cgroup's resident total.
        # Existing shared mappings are charged separately from new model state.
        baseline_vms = int(Path("/proc/self/statm").read_text().split()[0]) * os.sysconf("SC_PAGE_SIZE")
        address_limit = baseline_vms + item.memory_bytes
        resource.setrlimit(resource.RLIMIT_AS, (address_limit, address_limit))
        # Each candidate receives a private diagnostics target.  The backend may
        # leave it absent; an inherited caller setting must never collide with a
        # concurrent candidate's report.
        os.environ["CIX_CANDIDATE_DIAGNOSTICS"] = str(diagnostic_path)
        if item.encode_with_report is not None:
            output, details = item.encode_with_report(data)
            row["model_details"] = details
        else:
            output = item.encode(data)
        if not isinstance(output, bytes):
            raise TypeError("candidate did not return a complete byte archive")
        Path(archive).write_bytes(output)
        row.update(status="completed", archive_bytes=len(output),
                   archive_sha256=hashlib.sha256(output).hexdigest())
    except Exception as error:
        row.update(status="failed", error_type=type(error).__name__, error=str(error),
                   traceback=traceback.format_exc(limit=8))
    own = resource.getrusage(resource.RUSAGE_SELF)
    descendants = resource.getrusage(resource.RUSAGE_CHILDREN)
    row.update(wall_seconds=time.perf_counter()-before,
               cpu_seconds=own.ru_utime + own.ru_stime + descendants.ru_utime + descendants.ru_stime,
               worker_peak_rss_kib=own.ru_maxrss, descendant_peak_rss_kib=descendants.ru_maxrss,
               rss_scope="separate process maxima; aggregate peak is measured by the outer cgroup")
    details = _diagnostics(diagnostic_path)
    if details is not None:
        row["backend_diagnostics"] = details
    _save(Path(receipt), row)


def _kill_group(process: multiprocessing.Process) -> None:
    if process.pid is None:
        return
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        if process.is_alive():
            process.kill()
    process.join(timeout=5)


def _temporary_estimate(item: Candidate, input_bytes: int) -> int:
    """Conservative per-trial scratch estimate used for concurrent admission.

    Candidate output remains subject to the worker's stricter file-size limit.
    This reservation models the ordinary source/archive/restore scratch set and
    is deliberately separate from the declared model-memory admission.
    """
    declared = item.parameters.get("temporary_bytes")
    if isinstance(declared, int) and declared >= 0:
        return declared
    return max(64 << 20, 3 * input_bytes + (64 << 20))


def _admitted(item: Candidate, *, memory_bytes: int, threads: int) -> tuple[bool, str | None]:
    if max(item.memory_bytes, item.decode_memory_bytes) > memory_bytes:
        return False, "encoder/decoder memory admission"
    if item.threads > threads:
        return False, "CPU admission"
    return True, None


def _selection_report(data: bytes, profile: str, memory_bytes: int, threads: int,
                      diagnostics: list[dict]) -> dict:
    return {"schema": "cix-runtime-selection-v1", "profile": profile,
            "input_bytes": len(data), "input_sha256": hashlib.sha256(data).hexdigest(),
            "memory_admission_bytes": memory_bytes, "threads": threads,
            "selection": "smallest complete archive; original ordered priority on ties",
            "recognition": diagnostics, "trials": [], "status": "running",
            "strategy": {
                "kind": "canonical-first-fit-resource-admission-v1",
                "raw": "dispatched alone before parallel work",
                "constraints": {
                    "declared_peak_memory_bytes": memory_bytes,
                    "threads": threads,
                    "estimated_temporary_bytes": TEMPORARY_ADMISSION_BYTES,
                    "outer_aggregate_cgroup": "required for resident-memory and aggregate-temp enforcement",
                },
            }}


def _prepare_trials(candidates: list[Candidate], input_bytes: int, memory_bytes: int,
                    threads: int) -> tuple[list[dict], list[tuple[int, Candidate, dict, int]]]:
    rows: list[dict] = []
    pending: list[tuple[int, Candidate, dict, int]] = []
    for priority, item in enumerate(candidates):
        row = dict(item.description(), priority=priority)
        rows.append(row)
        eligible, reason = _admitted(item, memory_bytes=memory_bytes, threads=threads)
        if not eligible:
            row.update(status="budget-omitted", reason=reason)
            continue
        temporary_bytes = _temporary_estimate(item, input_bytes)
        if temporary_bytes > TEMPORARY_ADMISSION_BYTES:
            row.update(status="budget-omitted", reason="temporary-storage admission")
            continue
        pending.append((priority, item, row, temporary_bytes))
    raw = [entry for entry in pending if entry[1].family == "raw"]
    if len(raw) > 1:
        raise ValueError("duplicate raw candidate family")
    return rows, raw + [entry for entry in pending if entry[1].family != "raw"]


def _write_progress(report: dict, rows: list[dict], running: dict[int, dict],
                    maximum_inflight: int, progress_path: Path | None) -> None:
    report["trials"] = rows
    report["active_candidates"] = [
        {"id": state["item"].id, "priority": priority,
         "elapsed_seconds": time.perf_counter() - state["started"]}
        for priority, state in sorted(running.items())
    ]
    report["strategy"]["maximum_inflight"] = maximum_inflight
    if progress_path:
        _save(progress_path, report)


def _collect_trial(priority: int, state: dict, completed_archives: dict[int, Path],
                   *, timed_out: bool = False) -> None:
    process = state["process"]
    row = state["row"]
    try:
        if timed_out:
            _kill_group(process)
            row.update(status="budget-omitted", reason="candidate time allowance expired",
                       wall_seconds=time.perf_counter() - state["started"])
        else:
            process.join()
            if process.exitcode == 0 and state["receipt"].is_file():
                row.update(json.loads(state["receipt"].read_text()))
            else:
                row.update(status="failed", reason="candidate process failed or produced no receipt",
                           exit_code=process.exitcode)
    finally:
        _kill_group(process)
    if row.get("status") == "completed":
        frame = state["archive"].read_bytes()
        if (len(frame) != row["archive_bytes"]
                or hashlib.sha256(frame).hexdigest() != row["archive_sha256"]):
            raise RuntimeError("candidate receipt/archive mismatch")
        completed_archives[priority] = state["archive"]


def _next_ready(queue: list[tuple[int, Candidate, dict, int]], running: dict[int, dict],
                memory_bytes: int, threads: int) -> int | None:
    if any(state["item"].family == "raw" for state in running.values()):
        return None
    used_memory = sum(state["memory"] for state in running.values())
    used_threads = sum(state["threads"] for state in running.values())
    used_temporary = sum(state["temporary"] for state in running.values())
    for index, (_, item, _, temporary_bytes) in enumerate(queue):
        fits = (item.family != "raw" or not running) and (
            used_memory + item.memory_bytes <= memory_bytes
            and used_threads + item.threads <= threads
            and used_temporary + temporary_bytes <= TEMPORARY_ADMISSION_BYTES)
        if fits:
            return index
    return None


def _start_trial(context: multiprocessing.context.BaseContext, work: Path, data: bytes,
                 entry: tuple[int, Candidate, dict, int]) -> tuple[int, dict]:
    priority, item, row, temporary_bytes = entry
    directory = work / f"candidate-{priority:04d}"
    directory.mkdir()
    archive = directory / "archive.cix"
    receipt = directory / "receipt.json"
    diagnostics_path = directory / "backend-diagnostics.json"
    process = context.Process(
        target=_worker,
        args=(item, data, str(archive), str(receipt), str(diagnostics_path)),
    )
    return priority, {"item": item, "row": row, "process": process,
                      "archive": archive, "receipt": receipt,
                      "memory": item.memory_bytes, "threads": item.threads,
                      "temporary": temporary_bytes}


def _run_trials(data: bytes, work: Path, queue: list[tuple[int, Candidate, dict, int]],
                rows: list[dict], report: dict, memory_bytes: int, threads: int,
                progress_path: Path | None) -> dict[int, Path]:
    running: dict[int, dict] = {}
    try:
        return _drive_trials(data, work, queue, rows, report, memory_bytes,
                             threads, progress_path, running)
    finally:
        for state in running.values():
            _kill_group(state["process"])


def _drive_trials(data: bytes, work: Path, queue: list[tuple[int, Candidate, dict, int]],
                  rows: list[dict], report: dict, memory_bytes: int, threads: int,
                  progress_path: Path | None, running: dict[int, dict]) -> dict[int, Path]:
    context = multiprocessing.get_context("fork")
    completed_archives: dict[int, Path] = {}
    maximum_inflight = 0
    while queue or running:
        selected_index = _next_ready(queue, running, memory_bytes, threads)
        if selected_index is not None:
            priority, state = _start_trial(context, work, data, queue.pop(selected_index))
            state["started"] = time.perf_counter()
            state["process"].start()
            running[priority] = state
            maximum_inflight = max(maximum_inflight, len(running))
            _write_progress(report, rows, running, maximum_inflight, progress_path)
            continue
        finished = _finished_trials(running)
        if finished:
            for priority, timed_out in finished:
                _collect_trial(priority, running.pop(priority), completed_archives, timed_out=timed_out)
            _write_progress(report, rows, running, maximum_inflight, progress_path)
            continue
        _write_progress(report, rows, running, maximum_inflight, progress_path)
        _wait_for_trial(running, bool(queue))
    return completed_archives


def _finished_trials(running: dict[int, dict]) -> list[tuple[int, bool]]:
    now = time.perf_counter()
    return [
        (priority, now - state["started"] > state["item"].timeout_seconds)
        for priority, state in running.items()
        if now - state["started"] > state["item"].timeout_seconds or not state["process"].is_alive()
    ]


def _wait_for_trial(running: dict[int, dict], has_pending: bool) -> None:
    if not running:
        if has_pending:
            raise RuntimeError("resource-admitted candidate cannot be dispatched")
        return
    remaining = min(
        state["item"].timeout_seconds - (time.perf_counter() - state["started"])
        for state in running.values()
    )
    next(iter(running.values()))["process"].join(timeout=min(1.0, max(0.01, remaining)))


def _select_archive(rows: list[dict], completed_archives: dict[int, Path]) -> tuple[bytes, str]:
    incumbent: bytes | None = None
    selected = ""
    for priority, row in enumerate(rows):
        archive = completed_archives.get(priority)
        if archive is None:
            continue
        frame = archive.read_bytes()
        if incumbent is None or len(frame) < len(incumbent):
            incumbent, selected = frame, row["id"]
    if incumbent is None:
        raise RuntimeError("no complete archive candidate succeeded")
    return incumbent, selected


def encode(data: bytes, *, profile: str = "best", memory_bytes: int = DEFAULT_MEMORY,
           threads: int = 4, progress_path: Path | None = None,
           candidates: list[Candidate] | None = None) -> tuple[bytes, dict]:
    if len(data) > MAX_INPUT or memory_bytes < (64 << 20) or not 1 <= threads <= 4:
        raise ValueError("whole-input search exceeds declared runtime admission")
    if profile not in {"fast", "default", "best"}:
        raise ValueError("unsupported profile")
    started = time.perf_counter()
    if candidates is None:
        candidates, diagnostics = catalog(data, profile, threads, memory_bytes)
    else:
        diagnostics = []
    report = _selection_report(data, profile, memory_bytes, threads, diagnostics)
    with tempfile.TemporaryDirectory(prefix="cix-search-") as temporary:
        rows, queue = _prepare_trials(candidates, len(data), memory_bytes, threads)
        completed_archives = _run_trials(
            data, Path(temporary), queue, rows, report, memory_bytes, threads, progress_path,
        )
        incumbent, selected = _select_archive(rows, completed_archives)
        report["selected"] = selected
        report["trials"] = rows
    report.update(status="completed", archive_bytes=len(incumbent),
                  archive_sha256=hashlib.sha256(incumbent).hexdigest(),
                  full_search_wall_seconds=time.perf_counter()-started)
    report.pop("active_candidates", None)
    for row in report["trials"]:
        row["selected"] = row["id"] == report["selected"]
    if progress_path:
        _save(progress_path, report)
    return incumbent, report


def decode(frame: bytes, *, max_output_bytes: int = MAX_INPUT,
           memory_bytes: int = DEFAULT_MEMORY) -> bytes:
    from . import backends, heterogeneous, specialized
    prefix = frame[:5]
    if prefix == RAW_MAGIC:
        if len(frame) < RAW_HEADER.size:
            raise ValueError("truncated raw header")
        _, n, digest = RAW_HEADER.unpack_from(frame)
        if n > max_output_bytes or n + RAW_HEADER.size != len(frame) or 2*n > memory_bytes:
            raise ValueError("raw length or memory admission mismatch")
        output = frame[RAW_HEADER.size:]
        if hashlib.sha256(output).digest() != digest:
            raise ValueError("raw integrity mismatch")
        return output
    if prefix == backends.CIXP:
        return backends.decode_paq(frame, max_output_bytes, memory_bytes)
    if heterogeneous.recognizes_magic(prefix):
        return heterogeneous.decode(frame, max_output_bytes, memory_bytes)
    if specialized.recognizes_magic(prefix):
        return specialized.decode(frame, max_output_bytes, memory_bytes)
    if prefix in {b"CIXG1", b"CIXG2", b"CIXM5", b"CIXM6", b"CIXF1", b"CIXB1", b"CIXZ1"}:
        return backends.native_decode(frame, max_output_bytes, memory_bytes)
    raise ValueError("unsupported CIX archive identifier")
