"""Byte-identical, bounded parallel encoding for :mod:`joint_bounded`.

Blocks in the joint frame are independently selectable when the encoder is
given the preceding 64 KiB of *source* data.  That makes the encoder a useful
local throughput tool without changing the on-wire frame or its decoder.  The
parent keeps framing and ordering serial; workers only construct individual
block payloads.

This module deliberately does not parallelise an adaptive stream inside a
block.  Consequently its output is exactly the output of ``joint_bounded``
under the same native accelerator setup, including strict candidate-order tie
handling.
"""
from __future__ import annotations

import concurrent.futures
import multiprocessing
import os
import zlib

from cix.multinomial import vencode
from benchmarks.joint_bounded import BLOCK_SIZE, MAGIC, MAX_BLOCK_SIZE, ORDERS


# CPU 8 is reserved by the current frozen Hutter baseline; CPU 9 is kept free
# beside it so a monitor or system work cannot steal the baseline's sibling.
RESERVED_CPUS = frozenset((8, 9))
HISTORY_BYTES = 65536


def _enable_legacy_accelerators():
    """Match ``competitive_codec._parallel_legacy`` in each worker."""
    from benchmarks.native_ppm import enable
    from benchmarks import mixer_rounded_bounded, rounded_mixer

    enable()
    # Kept in lockstep with competitive_codec's legacy setup.  The bounded
    # mixer currently constructs its own native encoder, but retaining this
    # assignment preserves the exact opt-in environment for future variants.
    mixer_rounded_bounded.encode_mixer = rounded_mixer.native_encoder()


def _worker_init():
    _enable_legacy_accelerators()


def _encode_block(block: bytes, history: bytes, cpu: int) -> bytes:
    """Construct one normal joint payload, retaining serial tie behaviour."""
    os.sched_setaffinity(0, {cpu})
    from cix.ppm import encode_ppm
    from benchmarks.mixer_rounded_bounded import encode as encode_mixer

    best = b"\x00" + block
    for order in ORDERS:
        candidate = b"\x01" + encode_ppm(
            block, max_order=order, prefix_history=history
        )
        if len(candidate) < len(best):
            best = candidate
    mixed = b"\x02" + encode_mixer(block)
    if len(mixed) < len(best):
        best = mixed
    return best


def _selected_cpus(cpus):
    allowed = set(os.sched_getaffinity(0))
    if cpus is None:
        selected = tuple(sorted(allowed - RESERVED_CPUS))
    else:
        if isinstance(cpus, (str, bytes)):
            raise ValueError("cpus must be an iterable of CPU numbers")
        selected = tuple(cpus)
        if any(not isinstance(cpu, int) for cpu in selected):
            raise ValueError("cpus must contain integer CPU numbers")
        if RESERVED_CPUS.intersection(selected):
            raise ValueError("requested CPUs include reserved baseline CPUs")
        if not set(selected).issubset(allowed):
            raise ValueError("requested CPUs are outside caller affinity")
    if not selected or len(selected) != len(set(selected)):
        raise ValueError("cpus must be a non-empty sequence of distinct CPUs")
    return selected


def _validate(block_size, jobs, cpus):
    if not isinstance(block_size, int) or not 1 <= block_size <= MAX_BLOCK_SIZE:
        raise ValueError("invalid block size")
    selected = _selected_cpus(cpus)
    if jobs is None:
        jobs = len(selected)
    if not isinstance(jobs, int) or jobs < 1:
        raise ValueError("jobs must be a positive integer")
    if jobs > len(selected):
        raise ValueError("jobs cannot exceed selected CPUs")
    return jobs, selected


def encode(data, *, block_size=BLOCK_SIZE, jobs=None, cpus=None):
    """Encode a ``joint_bounded`` frame using a bounded process work queue.

    At most ``jobs`` blocks are submitted at once.  Input is sliced before it
    enters a worker and each PPM task receives only its serial 64 KiB source
    history, so workers never need an oracle or results from predecessor
    blocks.  Returned payloads are framed in original block order.
    """
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise TypeError("data must be bytes-like")
    data = bytes(data)
    jobs, selected = _validate(block_size, jobs, cpus)
    result = bytearray(
        MAGIC + vencode(len(data)) + vencode(block_size) + zlib.crc32(data).to_bytes(4, "big")
    )
    count = (len(data) + block_size - 1) // block_size
    if not count:
        return bytes(result)

    context = multiprocessing.get_context("spawn")
    finished = {}
    running = {}
    next_submit = 0
    next_write = 0

    def submit(pool, index):
        offset = index * block_size
        block = data[offset:offset + block_size]
        history = data[max(0, offset - HISTORY_BYTES):offset]
        # Futures are bounded to ``jobs`` and CPU choice follows submission
        # order.  Recycling a worker does not change this per-task affinity.
        future = pool.submit(_encode_block, block, history, selected[index % jobs])
        running[future] = index

    with concurrent.futures.ProcessPoolExecutor(
        max_workers=jobs, mp_context=context, initializer=_worker_init
    ) as pool:
        while next_submit < count and len(running) < jobs:
            submit(pool, next_submit)
            next_submit += 1
        while running:
            done, _ = concurrent.futures.wait(
                running, return_when=concurrent.futures.FIRST_COMPLETED
            )
            for future in done:
                index = running.pop(future)
                finished[index] = future.result()
            while next_submit < count and len(running) < jobs:
                submit(pool, next_submit)
                next_submit += 1
            while next_write in finished:
                payload = finished.pop(next_write)
                result.extend(vencode(len(payload)))
                result.extend(payload)
                next_write += 1
    if next_write != count:
        raise RuntimeError("parallel block scheduler lost a result")
    return bytes(result)
