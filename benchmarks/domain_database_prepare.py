"""Byte-preserving preparation helpers for frozen database-domain fixtures."""
from __future__ import annotations


def first_nonblank_records(data: bytes, count: int) -> bytes:
    """Return the first ``count`` complete nonblank physical records unchanged.

    The helper selects lines only; it does not parse CSV fields or normalize
    whitespace, delimiters, encodings, or record terminators.
    """
    if count <= 0:
        raise ValueError("record count must be positive")
    selected = [line for line in data.splitlines(keepends=True) if line.strip()][:count]
    if len(selected) != count:
        raise ValueError("source has fewer nonblank complete records than requested")
    return b"".join(selected)
