import os
import random

import pytest

from benchmarks import joint_bounded
from benchmarks.joint_parallel_encode import _CpuLeases, encode
from benchmarks.native_ppm import enable


def _cpus(count=2):
    available = sorted(set(os.sched_getaffinity(0)) - {8, 9})
    preferred = [cpu for cpu in available if 16 <= cpu <= 31]
    selected = preferred or available
    if len(selected) < count:
        pytest.skip("fewer than two non-reserved CPUs are available")
    return tuple(selected[:count])


@pytest.mark.parametrize(
    "data,block_size",
    [
        (b"", 128),
        (b"abc" * 180, 128),
        (random.Random(177).randbytes(2051), 257),
        (bytes(range(251)) * 17, 511),
    ],
)
def test_parallel_frame_is_serial_identical_and_round_trips(data, block_size):
    # This is the same native setup used by competitive_codec's legacy path.
    enable()
    serial = joint_bounded.encode(data, block_size=block_size)
    parallel = encode(data, block_size=block_size, jobs=2, cpus=_cpus())
    assert parallel == serial
    assert joint_bounded.decode(parallel) == data


def test_parallel_preserves_previous_64k_source_history_at_boundary():
    # The second block needs source bytes before its own start.  Its repeated
    # tail makes accidentally dropping that history observable in the frame.
    block_size = 65536
    prefix = (b"previous-block-history/" * 4096)[:block_size]
    data = prefix + prefix[-4096:] * 18 + b"end"
    enable()
    serial = joint_bounded.encode(data, block_size=block_size)
    parallel = encode(data, block_size=block_size, jobs=2, cpus=_cpus())
    assert parallel == serial
    assert joint_bounded.decode(parallel) == data


def test_parallel_rejects_reserved_or_out_of_affinity_cpus():
    with pytest.raises(ValueError, match="reserved"):
        encode(b"x", block_size=16, jobs=1, cpus=(8,))
    with pytest.raises(ValueError, match="outside caller affinity"):
        encode(b"x", block_size=16, jobs=1, cpus=(999999,))


def test_skewed_completion_reuses_only_the_completed_tasks_cpu_lease():
    # Simulate block 0 on CPU 16 still running while block 1 on CPU 17 wins
    # the race.  A third block must wait for and reuse 17, never overlap 16.
    leases = _CpuLeases((16, 17))
    assert leases.claim() == 16
    assert leases.claim() == 17
    assert leases.claim() is None
    leases.release(17)
    assert leases.claim() == 17
    with pytest.raises(RuntimeError, match="not leased"):
        leases.release(99)
