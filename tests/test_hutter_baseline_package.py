import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

import pytest

from benchmarks import hutter_baseline_package as package


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path: Path, body: bytes = b"x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)


def _fixture(tmp_path: Path) -> dict:
    runtime = tmp_path / "runtime"
    static_modules = ["cix", "cix.core", "benchmarks", "benchmarks.competitive_cli"]
    for name in ("cix/__init__.py", "cix/core.py", "benchmarks/__init__.py", "benchmarks/competitive_cli.py"):
        _write(runtime / name, ("# " + name + "\n").encode())
    for binary, source in package.DEFAULT_NATIVE:
        _write(runtime / binary, binary.encode())
        _write(runtime / source, source.encode())
    for version in ("215", "216"):
        root = runtime / "benchmark-work/references" / f"paq8px-v{version}"
        _write(root / f"paq8px-{version}/COPYING", b"license")
        _write(root / f"paq8px-{version}/src/paq.cpp", b"source")
        _write(root / "build-local/paq8px", b"binary")
    frozen_files = {path.relative_to(runtime).as_posix(): _hash(path) for path in runtime.rglob("*") if path.is_file()}
    freeze = tmp_path / "freeze.json"
    freeze.write_text(json.dumps({"source_commit": "frozen", "runtime_files": frozen_files}))
    imports = tmp_path / "imports.json"
    imports.write_text(json.dumps({"research_commit": "closure", "local_python_modules": static_modules,
                                   "non_stdlib_import_roots": sorted(package.NON_STDLIB_IMPORT_ROOTS)}))
    vendor = tmp_path / "vendor"
    _write(vendor / "brotli.py", b"# installed Brotli is a module, not a package\n")
    for package_dir in ("numpy", "imagecodecs", "pydivsufsort", "zstandard"):
        _write(vendor / package_dir / "__init__.py", package_dir.encode())
        _write(vendor / f"{package_dir}-1.0.dist-info/LICENSE", b"license")
    _write(vendor / "_brotli.cpython-test.so", b"extension")
    _write(vendor / "imagecodecs.libs/libexample.so", b"private")
    _write(vendor / "pydivsufsort.libs/libexample.so", b"private")
    return {"runtime": runtime, "freeze": freeze, "imports": imports, "vendor": vendor,
            "paq": [runtime / "benchmark-work/references/paq8px-v215", runtime / "benchmark-work/references/paq8px-v216"],
            "run": tmp_path / "run", "out": tmp_path / "out"}


def _complete_run(case: dict, monkeypatch, payload: bytes = b"archive") -> None:
    monkeypatch.setattr(package, "CANONICAL_BYTES", 9)
    monkeypatch.setattr(package, "CANONICAL_SHA256", "canonical")
    run = case["run"]
    run.mkdir()
    archive = run / "enwik9.cix"
    archive.write_bytes(payload)
    record = {"status": "VERIFIED_COMPLETE_ARCHIVE", "full_round_trip": True,
              "input_bytes": 9, "input_sha256": "canonical", "archive_bytes": len(payload),
              "archive_sha256": _hash(archive), "source_commit": "frozen", "policy": "p26"}
    (run / "status.json").write_text(json.dumps(record))
    (run / "complete.json").write_text(json.dumps(record))


def _build(case: dict, name: str = "program.zip") -> dict:
    return package.build_bundle(runtime=case["runtime"], freeze_manifest=case["freeze"],
                                static_imports=case["imports"], vendor_root=case["vendor"],
                                paq_roots=case["paq"], output=case["out"] / name)


def test_pending_result_has_null_totals_and_does_not_build(tmp_path):
    case = _fixture(tmp_path)
    result = package.package_report(runtime=case["runtime"], freeze_manifest=case["freeze"],
                                    static_imports=case["imports"], vendor_root=case["vendor"], paq_roots=case["paq"],
                                    run=case["run"], output=case["out"] / "program.zip", required_options=[], allow_pending=True)
    assert result["measurement_status"] == "PENDING_OR_UNVERIFIED_FULL_ENWIK9_ARCHIVE"
    assert result["hutter_accounting"]["total_bytes"] is None
    assert not (case["out"] / "program.zip").exists()


def test_deterministic_bundle_and_exact_split_formula(tmp_path, monkeypatch):
    case = _fixture(tmp_path)
    _complete_run(case, monkeypatch, b"real-archive")
    first = _build(case, "one.zip")
    second = _build(case, "two.zip")
    assert (case["out"] / "one.zip").read_bytes() == (case["out"] / "two.zip").read_bytes()
    result = package.package_report(runtime=case["runtime"], freeze_manifest=case["freeze"],
                                    static_imports=case["imports"], vendor_root=case["vendor"], paq_roots=case["paq"],
                                    run=case["run"], output=case["out"] / "three.zip", required_options=["é"], allow_pending=False)
    accounting = result["hutter_accounting"]
    assert accounting["required_option_bytes"] == len(b"encodedecode") + len("é".encode("utf-8"))
    assert accounting["total_bytes"] == 2 * accounting["program_zip"]["bytes"] + len(b"real-archive") + len(b"encodedecode") + 2
    assert all(not entry["path"].startswith("/") for entry in accounting["program_zip"]["files"])
    assert "cix-p26.sh" in {entry["path"] for entry in accounting["program_zip"]["files"]}
    paths = {entry["path"] for entry in accounting["program_zip"]["files"]}
    assert "vendor/site-packages/pydivsufsort.libs/libexample.so" in paths
    assert "vendor/site-packages/zstandard/__init__.py" in paths


def test_changed_or_omitted_closure_or_native_artifact_fails_closed(tmp_path):
    case = _fixture(tmp_path)
    (case["runtime"] / "cix/core.py").write_text("changed")
    with pytest.raises(ValueError, match="changed"):
        _build(case)
    case = _fixture(tmp_path / "other")
    (case["runtime"] / "cix/core.py").unlink()
    with pytest.raises(ValueError, match="does not resolve"):
        _build(case)
    case = _fixture(tmp_path / "another")
    (case["runtime"] / "results/leaderboard/native_ppm.so").unlink()
    with pytest.raises(ValueError, match="not a regular"):
        _build(case)


def test_mismatched_verified_archive_receipt_fails_closed(tmp_path, monkeypatch):
    case = _fixture(tmp_path)
    _complete_run(case, monkeypatch)
    status = json.loads((case["run"] / "status.json").read_text())
    status["archive_sha256"] = "0" * 64
    (case["run"] / "status.json").write_text(json.dumps(status))
    with pytest.raises(ValueError, match="incomplete, inconsistent"):
        package.package_report(runtime=case["runtime"], freeze_manifest=case["freeze"],
                               static_imports=case["imports"], vendor_root=case["vendor"], paq_roots=case["paq"],
                               run=case["run"], output=case["out"] / "program.zip", required_options=[], allow_pending=False)


def test_changed_physical_archive_or_source_commit_mismatch_fails_closed(tmp_path, monkeypatch):
    case = _fixture(tmp_path)
    _complete_run(case, monkeypatch)
    (case["run"] / "enwik9.cix").write_bytes(b"changed after receipt")
    with pytest.raises(ValueError, match="does not match"):
        package.package_report(runtime=case["runtime"], freeze_manifest=case["freeze"],
                               static_imports=case["imports"], vendor_root=case["vendor"], paq_roots=case["paq"],
                               run=case["run"], output=case["out"] / "program.zip", required_options=[], allow_pending=False)
    (case["run"] / "enwik9.cix").write_bytes(b"archive")
    record = json.loads((case["run"] / "status.json").read_text())
    record["source_commit"] = "different"
    (case["run"] / "status.json").write_text(json.dumps(record))
    with pytest.raises(ValueError, match="incomplete, inconsistent"):
        package.package_report(runtime=case["runtime"], freeze_manifest=case["freeze"],
                               static_imports=case["imports"], vendor_root=case["vendor"], paq_roots=case["paq"],
                               run=case["run"], output=case["out"] / "other.zip", required_options=[], allow_pending=False)


def test_symlink_input_is_rejected(tmp_path):
    case = _fixture(tmp_path)
    target = case["runtime"] / "cix/core.py"
    target.unlink()
    target.symlink_to(case["runtime"] / "cix/__init__.py")
    with pytest.raises(ValueError, match="regular"):
        _build(case)


def test_unresolved_nonstdlib_import_root_fails_closed(tmp_path):
    case = _fixture(tmp_path)
    imports = json.loads(case["imports"].read_text())
    imports["non_stdlib_import_roots"].append("unreviewed_extension")
    case["imports"].write_text(json.dumps(imports))
    with pytest.raises(ValueError, match="unresolved roots"):
        _build(case)


def test_extracted_launcher_chdirs_and_executes_relative_native_fixture(tmp_path):
    case = _fixture(tmp_path)
    cli = case["runtime"] / "benchmarks/competitive_cli.py"
    cli.write_text("import subprocess\nsubprocess.run(['results/leaderboard/native_ppm.so'], check=True)\nprint('portable-ok')\n")
    native = case["runtime"] / "results/leaderboard/native_ppm.so"
    native.write_text("#!/bin/sh\nprintf native-ok\n")
    native.chmod(0o755)
    frozen = json.loads(case["freeze"].read_text())
    for path in (cli, native):
        frozen["runtime_files"][path.relative_to(case["runtime"]).as_posix()] = _hash(path)
    case["freeze"].write_text(json.dumps(frozen))
    built = _build(case)
    unpacked = tmp_path / "unpacked"
    with zipfile.ZipFile(built["path"]) as source:
        for info in source.infolist():
            target = unpacked / info.filename
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read(info))
            os.chmod(target, info.external_attr >> 16)
    result = subprocess.run([str(unpacked / "cix-p26.sh")], cwd=tmp_path, text=True, capture_output=True, check=True,
                            env={"PATH": os.environ["PATH"], "PYTHONPATH": "/must/not/leak"})
    assert "native-ok" in result.stdout
    assert "portable-ok" in result.stdout
