"""Immutable, verified-artifact cache for bounded Hutter experiments.

The cache stores references and hashes, never a second uncontrolled artifact
copy.  A missing key is a normal :class:`CacheMiss`; a bad index, receipt, or
changed referenced artifact is :class:`CacheCorruption` and must not be reused.

Preprocessing callers must provide an explicit verification declaration.  The
cache verifies the supplied artifact and restored bytes, but does *not* execute
an external decoder itself.  Therefore a caller declaration is recorded as
``caller_attested`` unless it identifies a bounded-run receipt that was itself
independently archive-only decoded.
"""
from __future__ import annotations

import hashlib
import fcntl
import json
import os
import tempfile
from pathlib import Path
from typing import Any


class CacheError(RuntimeError):
    """Base class for cache failures."""


class CacheMiss(CacheError):
    """The requested key has never been inserted."""


class CacheCorruption(CacheError):
    """A stored record is malformed, conflicting, or its artifact changed."""


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _hash_map(value: Any, label: str) -> dict[str, str]:
    if not isinstance(value, dict) or not value:
        raise CacheCorruption(f"{label} must be a nonempty source/dependency hash map")
    result: dict[str, str] = {}
    for name, digest in value.items():
        if not isinstance(name, str) or not name or not isinstance(digest, str) or len(digest) != 64:
            raise CacheCorruption(f"{label} contains an invalid hash entry")
        try:
            int(digest, 16)
        except ValueError as error:
            raise CacheCorruption(f"{label} contains a non-hex digest") from error
        result[name] = digest
    return result


def _input(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CacheCorruption("input identity must be an object")
    required = ("path", "offset", "length", "sha256")
    if any(key not in value for key in required):
        raise CacheCorruption("input identity is incomplete")
    if not isinstance(value["path"], str) or not isinstance(value["offset"], int):
        raise CacheCorruption("input path/offset is invalid")
    if not isinstance(value["length"], int) or value["length"] <= 0:
        raise CacheCorruption("input length is invalid")
    digest = value["sha256"]
    if not isinstance(digest, str) or len(digest) != 64:
        raise CacheCorruption("input SHA-256 is invalid")
    try:
        int(digest, 16)
    except ValueError as error:
        raise CacheCorruption("input SHA-256 is non-hex") from error
    return {key: value[key] for key in required}


def _control_identity(receipt: dict[str, Any]) -> dict[str, Any]:
    identity = receipt.get("identity")
    if not isinstance(identity, dict):
        raise CacheCorruption("receipt has no immutable identity")
    configuration = identity.get("configuration")
    if not isinstance(configuration, dict):
        raise CacheCorruption("receipt configuration is missing")
    # Preserve every configuration field (rather than a selected subset) in the
    # key.  This prevents an omitted newly introduced option from reusing a
    # control produced under different settings.
    return {
        "input": _input(identity.get("input")),
        "configuration": configuration,
        "build_sha256": _hash_map(identity.get("build_sha256"), "receipt build_sha256"),
        "core": identity.get("core"),
        "initial_state": identity.get("initial_state"),
        "manifest_sha256": identity.get("manifest_sha256"),
    }


def _control_record(receipt_path: Path) -> tuple[str, dict[str, Any]]:
    try:
        receipt = json.loads(receipt_path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        raise CacheCorruption("control receipt cannot be read") from error
    if receipt.get("status") != "VERIFIED_SCREENING":
        raise CacheCorruption("only VERIFIED_SCREENING controls are cacheable")
    identity = _control_identity(receipt)
    verification = receipt.get("verification")
    if not isinstance(verification, dict) or verification.get("matched") is not True:
        raise CacheCorruption("control receipt lacks successful verification")
    source = identity["input"]
    if verification.get("source_sha256") != source["sha256"] or verification.get("restored_sha256") != source["sha256"]:
        raise CacheCorruption("control receipt verification does not bind its exact input")
    if not isinstance(receipt.get("independent_decode"), str) or not receipt["independent_decode"].strip():
        raise CacheCorruption("control receipt lacks independent decode evidence")
    artifacts = receipt.get("artifacts")
    if not isinstance(artifacts, dict):
        raise CacheCorruption("control receipt lacks artifact references")
    archive, restored = Path(artifacts.get("archive", "")).resolve(), Path(artifacts.get("restored", "")).resolve()
    if not archive.is_file() or not restored.is_file():
        raise CacheCorruption("control artifact is missing")
    if not isinstance(receipt.get("archive_bytes"), int) or receipt["archive_bytes"] != archive.stat().st_size:
        raise CacheCorruption("control physical archive size changed or is incomplete")
    if receipt.get("archive_sha256") != _sha256(archive):
        raise CacheCorruption("control archive hash changed")
    if restored.stat().st_size != source["length"] or _sha256(restored) != source["sha256"]:
        raise CacheCorruption("control restored artifact no longer proves byte-exact input")
    record = {
        "kind": "control",
        "receipt": str(receipt_path.resolve()),
        "identity": identity,
        "archive": str(archive),
        "restored": str(restored),
        "archive_bytes": receipt["archive_bytes"],
        "archive_sha256": receipt["archive_sha256"],
        "restored_sha256": source["sha256"],
        "verification_level": "bounded_receipt_independent_archive_only",
    }
    key = hashlib.sha256(_canonical({"kind": "control", "identity": identity})).hexdigest()
    return key, record


def _preprocessing_identity(spec: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(spec, dict):
        raise CacheCorruption("preprocessing spec must be an object")
    kind = spec.get("kind")
    if not isinstance(kind, str) or not kind.strip():
        raise CacheCorruption("preprocessing kind is required")
    if kind == "prediction_trace":
        raise CacheCorruption("prediction_trace reuse is forbidden without a state-equivalence verifier")
    configuration = spec.get("configuration")
    if not isinstance(configuration, dict):
        raise CacheCorruption("preprocessing configuration is missing")
    return {
        # All declared parameters are retained, including future fields, so a
        # caller cannot accidentally omit an option from cache identity.
        "spec": spec,
        "input": _input(spec.get("input")),
        "source_hashes": _hash_map(spec.get("source_hashes"), "preprocessing source_hashes"),
        "configuration": configuration,
    }


def _preprocessing_record(spec: dict[str, Any], artifact_path: Path, restored_path: Path) -> tuple[str, dict[str, Any]]:
    identity = _preprocessing_identity(spec)
    artifact, restored = artifact_path.resolve(), restored_path.resolve()
    if not artifact.is_file() or not restored.is_file():
        raise CacheCorruption("preprocessing artifact or restored bytes are missing")
    source = identity["input"]
    verification = spec.get("verification")
    if not isinstance(verification, dict) or verification.get("matched") is not True:
        raise CacheCorruption("preprocessing requires caller verification.matched=true")
    if verification.get("source_sha256") != source["sha256"] or verification.get("restored_sha256") != source["sha256"]:
        raise CacheCorruption("preprocessing verification does not bind exact input")
    evidence = spec.get("independent_decode_evidence")
    if not isinstance(evidence, str) or not evidence.strip():
        raise CacheCorruption("preprocessing requires independent_decode_evidence")
    if restored.stat().st_size != source["length"] or _sha256(restored) != source["sha256"]:
        raise CacheCorruption("preprocessing restored bytes do not match exact input")
    verification_source = spec.get("verification_source", "caller_attested")
    if verification_source not in ("caller_attested", "bounded_receipt"):
        raise CacheCorruption("unknown preprocessing verification_source")
    if verification_source == "bounded_receipt":
        receipt = spec.get("verification_receipt")
        if not isinstance(receipt, str):
            raise CacheCorruption("bounded preprocessing declaration requires verification_receipt")
        # A different verified archive cannot certify this transform. Bind the
        # exact input and the exact independently decoded frame to the receipt.
        _, proof = _control_record(Path(receipt))
        if proof["identity"]["input"] != source or Path(proof["archive"]) != artifact:
            raise CacheCorruption("preprocessing receipt does not verify this exact input and artifact")
        if Path(proof["restored"]) != restored:
            raise CacheCorruption("preprocessing receipt has a different restored artifact")
        level = "bounded_receipt_independent_archive_only"
    else:
        level = "caller_attested_not_independently_reexecuted_by_cache"
    record = {
        "kind": "preprocessing",
        "identity": identity,
        "artifact": str(artifact),
        "artifact_bytes": artifact.stat().st_size,
        "artifact_sha256": _sha256(artifact),
        "restored": str(restored),
        "restored_sha256": source["sha256"],
        "independent_decode_evidence": evidence,
        "verification_level": level,
    }
    key = hashlib.sha256(_canonical({"kind": "preprocessing", "identity": identity})).hexdigest()
    return key, record


class Cache:
    """Content-addressed index of validated references under ``root``."""

    def __init__(self, root: Path | str):
        self.root = Path(root).resolve()
        self.index_path = self.root / "index.json"

    def _load(self) -> dict[str, Any]:
        if not self.index_path.exists():
            return {"schema": 1, "controls": {}, "preprocessing": {}}
        try:
            index = json.loads(self.index_path.read_text())
        except (OSError, json.JSONDecodeError) as error:
            raise CacheCorruption("cache index cannot be read") from error
        if not isinstance(index, dict) or index.get("schema") != 1:
            raise CacheCorruption("cache index schema is invalid")
        for key in ("controls", "preprocessing"):
            if not isinstance(index.get(key), dict):
                raise CacheCorruption("cache index is malformed")
        return index

    def _write(self, index: dict[str, Any]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        descriptor, filename = tempfile.mkstemp(prefix=".index-", dir=self.root)
        temporary = Path(filename)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(_canonical(index) + b"\n")
            stream.flush()
            os.fsync(stream.fileno())
        temporary.chmod(0o444)
        os.replace(temporary, self.index_path)
        self.index_path.chmod(0o444)

    def _put(self, bucket: str, key: str, record: dict[str, Any]) -> str:
        self.root.mkdir(parents=True, exist_ok=True)
        with (self.root / ".index.lock").open("a+") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            index = self._load()
            existing = index[bucket].get(key)
            if existing is not None:
                if _canonical(existing) != _canonical(record):
                    raise CacheCorruption("same immutable key has conflicting artifact evidence")
                return key
            index[bucket][key] = record
            self._write(index)
        return key

    def put_control(self, receipt_path: Path | str) -> str:
        key, record = _control_record(Path(receipt_path))
        return self._put("controls", key, record)

    def get_control(self, key: str) -> dict[str, Any]:
        record = self._load()["controls"].get(key)
        if record is None:
            raise CacheMiss(f"control cache miss: {key}")
        actual_key, actual = _control_record(Path(record.get("receipt", "")))
        if actual_key != key or _canonical(actual) != _canonical(record):
            raise CacheCorruption("cached control no longer matches its immutable receipt/artifacts")
        return actual

    def put_preprocessing(self, spec: dict[str, Any], artifact_path: Path | str, restored_path: Path | str) -> str:
        key, record = _preprocessing_record(spec, Path(artifact_path), Path(restored_path))
        return self._put("preprocessing", key, record)

    def get_preprocessing(self, key: str) -> dict[str, Any]:
        record = self._load()["preprocessing"].get(key)
        if record is None:
            raise CacheMiss(f"preprocessing cache miss: {key}")
        spec = record.get("identity", {}).get("spec") if isinstance(record, dict) else None
        actual_key, actual = _preprocessing_record(spec, Path(record.get("artifact", "")), Path(record.get("restored", "")))
        if actual_key != key or _canonical(actual) != _canonical(record):
            raise CacheCorruption("cached preprocessing no longer matches its immutable artifacts")
        return actual
