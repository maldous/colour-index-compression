import os
import random

import pytest

from benchmarks import competitive_codec as codec
from benchmarks.competitive_parallel_cli import memory_bound, parse_cpus
from tests.test_competitive_codec import legacy_raw


def _cpus():
    available=sorted(os.sched_getaffinity(0))
    if len(available)<2:
        pytest.skip('parallel equivalence requires two permitted CPUs')
    return tuple(available[:2])


def _identity(record):
    return [(row['name'],row['size'],row.get('cache_used')) for row in record['trials']]


def test_parallel_portfolio_preserves_serial_selection_and_tie_order():
    data=random.Random(481).randbytes(4096)
    serial,serial_record=codec.encode(data,legacy_cache=legacy_raw(data))
    parallel,parallel_record=codec.encode_parallel(data,workers=2,cpus=_cpus(),legacy_cache=legacy_raw(data))
    assert parallel==serial
    assert parallel_record['selected']==serial_record['selected']
    assert _identity(parallel_record)==_identity(serial_record)
    assert codec.decode(parallel)==data


def test_parallel_portfolio_runs_uncached_legacy_candidate_in_worker():
    data=(b'parallel candidate block ' * 300)
    serial,serial_record=codec.encode(data)
    parallel,parallel_record=codec.encode_parallel(data,workers=2,cpus=_cpus())
    assert parallel==serial
    assert parallel_record['selected']==serial_record['selected']
    assert _identity(parallel_record)==_identity(serial_record)
    assert codec.decode(parallel)==data


def test_parallel_bounds_reject_invalid_or_oversubscribed_cpu_choices():
    allowed=sorted(os.sched_getaffinity(0))
    with pytest.raises(ValueError):
        codec.encode_parallel(b'x',workers=len(allowed)+1,cpus=tuple(allowed))
    with pytest.raises(ValueError):
        codec.encode_parallel(b'x',workers=1,cpus=(max(allowed)+1000,))


def test_parallel_cli_cpu_and_memory_guards_are_explicit():
    assert parse_cpus('16-18,20')==(16,17,18,20)
    with pytest.raises(Exception):
        parse_cpus('16-18,18')
    assert memory_bound(100,2,10000,1000,0)==2200
    with pytest.raises(ValueError):
        memory_bound(100,8,1000,1000,0)
