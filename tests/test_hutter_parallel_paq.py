import os

import pytest

from benchmarks import hutter_parallel_paq as codec


def _cpus(count=2):
    candidates = [cpu for cpu in sorted(os.sched_getaffinity(0)) if cpu not in (8, 9)]
    if len(candidates) < count:
        pytest.skip("fewer than two non-reserved CPUs are available")
    return tuple(candidates[:count])


def test_actual_paq_chunks_round_trip_and_are_self_contained(tmp_path):
    # Keep this deliberately small; it invokes the pinned actual v216 binary,
    # but exercises multiple independent container chunks and the full decoder.
    source = tmp_path / "source.bin"
    source.write_bytes((b"parallel PAQ stream test\n" * 300) + bytes(range(251)))
    archive = tmp_path / "parallel.cixparq"
    report = codec.encode(source, archive, chunk_bytes=2048, workers=2, cpus=_cpus(), options="-8",
                          temporary=tmp_path / "work", verify=True)
    assert report["round_trip"] is True
    assert report["chunks"] >= 2
    assert report["output_bytes"] == archive.stat().st_size
    assert archive.read_bytes().startswith(codec.MAGIC)
    restored = tmp_path / "restored.bin"
    decoded = codec.decode(archive, restored, temporary=tmp_path / "decode")
    assert decoded["output_sha256"] == report["source_sha256"]
    assert restored.read_bytes() == source.read_bytes()


def test_rejects_reserved_cpu_and_bad_framing(tmp_path):
    with pytest.raises(ValueError, match="reserved"):
        codec.parse_cpus("8")
    source = tmp_path / "bad.cixparq"
    source.write_bytes(codec.MAGIC + b"short")
    with pytest.raises(ValueError, match="truncated"):
        codec.decode(source, tmp_path / "out.bin", temporary=tmp_path / "decode")
