"""Complete-archive candidate contract shared by runtime adapters."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass(frozen=True)
class Candidate:
    id: str
    family: str
    encode: Callable[[bytes], bytes]
    memory_bytes: int
    decode_memory_bytes: int
    timeout_seconds: int = 43200
    threads: int = 1
    parameters: dict = field(default_factory=dict)
    encode_with_report: Callable[[bytes], tuple[bytes, object]] | None = None

    def description(self) -> dict:
        return {
            "id": self.id, "family": self.family,
            "memory_bytes": self.memory_bytes,
            "decode_memory_bytes": self.decode_memory_bytes,
            "timeout_seconds": self.timeout_seconds, "threads": self.threads,
            "parameters": self.parameters,
        }
