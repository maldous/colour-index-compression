"""Immutable content-addressed evidence registry; it never opens a corpus."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path


KINDS = {"inputs", "classifications", "exposures"}
EXPOSURE_KINDS = {"hash_only", "development", "profile", "holdout_test", "historical_full_read"}


def canonical(value: object) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise ValueError("record must be JSON serializable") from error


def digest(value: object) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def hash64(value: str, name: str) -> None:
    if not isinstance(value, str) or len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise ValueError(f"{name} must be a lowercase 64-character SHA-256 hex digest")


class Registry:
    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        for kind in KINDS:
            (self.root / kind).mkdir(parents=True, exist_ok=True)

    def _path(self, kind: str, record_id: str) -> Path:
        if kind not in KINDS:
            raise ValueError("unknown record kind")
        hash64(record_id, "record id")
        return self.root / kind / f"{record_id}.json"

    def _read(self, kind: str, record_id: str) -> dict:
        path = self._path(kind, record_id)
        try:
            value = json.loads(path.read_text())
        except FileNotFoundError:
            raise KeyError(record_id) from None
        except json.JSONDecodeError as error:
            raise ValueError(f"corrupt {kind} record: {record_id}") from error
        if not isinstance(value, dict) or digest(value) != record_id:
            raise ValueError(f"corrupt {kind} record: {record_id}")
        return value

    def _write(self, kind: str, value: dict) -> str:
        record_id = digest(value)
        path = self._path(kind, record_id)
        payload = canonical(value) + b"\n"
        try:
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
        except FileExistsError:
            # Existing content must be a valid identical immutable record; a
            # filename collision with corrupt or altered bytes is never repaired.
            if self._read(kind, record_id) != value:
                raise ValueError(f"immutable {kind} record mismatch: {record_id}")
            return record_id
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                directory = os.open(path.parent, os.O_RDONLY)
                try: os.fsync(directory)
                finally: os.close(directory)
            except OSError:
                pass
        except BaseException:
            # Do not remove a possibly observed immutable path after an I/O
            # failure. Its digest validation will surface the corruption.
            raise
        return record_id

    def register_input(self, dataset_sha256: str, offset: int, length: int, range_sha256: str) -> str:
        hash64(dataset_sha256, "dataset_sha256"); hash64(range_sha256, "range_sha256")
        if not isinstance(offset, int) or offset < 0:
            raise ValueError("offset must be a nonnegative integer")
        if not isinstance(length, int) or length <= 0:
            raise ValueError("length must be a positive integer")
        # Deliberately no filesystem path: byte identity is separate from any
        # location where the corpus happened to be materialized.
        return self._write("inputs", {"dataset_sha256": dataset_sha256, "offset": offset,
                                      "length": length, "range_sha256": range_sha256})

    def record_classification(self, input_id: str, classification_dict: dict, provenance: object) -> str:
        self._read("inputs", input_id)
        if not isinstance(classification_dict, dict):
            raise ValueError("classification_dict must be an object")
        return self._write("classifications", {"input_id": input_id, "classification": classification_dict,
                                                "provenance": provenance})

    def record_exposure(self, input_id: str, event_dict: dict) -> str:
        self._read("inputs", input_id)
        if not isinstance(event_dict, dict) or event_dict.get("kind") not in EXPOSURE_KINDS:
            raise ValueError("exposure kind must be explicit and supported")
        for key in ("evidence_refs", "userdirective_refs"):
            refs = event_dict.get(key)
            if not isinstance(refs, list) or not refs or not all(isinstance(ref, str) and ref for ref in refs):
                raise ValueError(f"exposure {key} must be a nonempty string list")
        # An event describes observed evidence only. In particular, it never
        # classifies unobserved ranges as held out or otherwise.
        return self._write("exposures", {"input_id": input_id, "event": event_dict})

    def get_input(self, record_id: str) -> dict:
        return self._read("inputs", record_id)

    def records(self, kind: str) -> list[dict]:
        if kind not in KINDS:
            raise ValueError("unknown record kind")
        values = []
        for path in sorted((self.root / kind).glob("*.json")):
            values.append(self._read(kind, path.stem))
        return values
