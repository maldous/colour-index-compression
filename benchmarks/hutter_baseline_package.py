"""Build and account for the frozen p26 *baseline* program package.

This is deliberately a conservative accounting tool, not a Hutter submission
builder.  It only packages files selected from the frozen runtime manifest,
and it refuses to state a package total until the paired full enwik9 run has
completed and its actual archive hash is present on disk.  In particular, it
does not infer a program size from a source tarball or from a sum of modules.

The resulting ZIP is deterministic: entry ordering, timestamps and modes are
fixed.  It intentionally records that CPython itself is not bundled; the
current portfolio therefore remains a measured baseline rather than a claim of
offline self-contained Prize eligibility.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import tempfile
import zipfile
from typing import Any, Iterable


CANONICAL_BYTES = 1_000_000_000
CANONICAL_SHA256 = "159b85351e5f76e60cbe32e04c677847a9ecba3adc79addab6f4c6c7aa3744bc"
DEFAULT_NATIVE = (
    ("results/leaderboard/native_ppm.so", "benchmarks/native_ppm.cpp"),
    ("results/leaderboard/native_ppm_decode.so", "benchmarks/native_ppm_decode.cpp"),
    ("results/leaderboard/native_mixer_rounding.so", "benchmarks/native_mixer_rounding.cpp"),
    ("results/leaderboard/native_legacy_mixer.so", "benchmarks/native_legacy_mixer.cpp"),
)
VENDOR_NAMES = ("brotli", "numpy", "imagecodecs")
ZIP_TIME = (1980, 1, 1, 0, 0, 0)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_relative(value: str) -> PurePosixPath:
    result = PurePosixPath(value)
    if not value or result.is_absolute() or ".." in result.parts or "." in result.parts:
        raise ValueError(f"unsafe archive path: {value!r}")
    return result


def _file_tree(root: Path) -> list[Path]:
    """Return regular files below root, refusing symlinks and special files."""
    if root.is_symlink() or not root.is_dir():
        raise ValueError(f"required directory is absent or not a real directory: {root}")
    found: list[Path] = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"symlink is not permitted in package input: {path}")
        if path.is_file():
            found.append(path)
        elif not path.is_dir():
            raise ValueError(f"non-regular package input: {path}")
    return found


def _module_paths(runtime: Path, modules: Iterable[str]) -> list[Path]:
    """Resolve the frozen static local-module closure and parent packages."""
    files: set[Path] = set()
    for module in modules:
        if not isinstance(module, str) or not module or module.startswith("."):
            raise ValueError(f"invalid static module name: {module!r}")
        bits = module.split(".")
        target = runtime.joinpath(*bits)
        candidate = target.with_suffix(".py")
        if candidate.is_file():
            files.add(candidate)
        elif (target / "__init__.py").is_file():
            files.add(target / "__init__.py")
        else:
            raise ValueError(f"static closure module does not resolve in frozen runtime: {module}")
        for length in range(1, len(bits)):
            init = runtime.joinpath(*bits[:length], "__init__.py")
            if init.is_file():
                files.add(init)
    return sorted(files, key=lambda item: item.relative_to(runtime).as_posix())


def _vendor_paths(root: Path) -> list[Path]:
    """Select only the known static-import roots and their metadata/private libs."""
    if root.is_symlink() or not root.is_dir():
        raise ValueError(f"vendor root is absent or not a real directory: {root}")
    selected: list[Path] = []
    children = sorted(root.iterdir(), key=lambda item: item.name.lower())
    for child in children:
        lower = child.name.lower()
        matches = (
            child.name in VENDOR_NAMES
            or child.name == "brotli.py"
            or lower.startswith("_brotli") and child.suffix == ".so"
            or any(lower.startswith(name + "-") and lower.endswith(".dist-info") for name in VENDOR_NAMES)
            or any(lower in {name + ".libs", ".libs"} for name in VENDOR_NAMES)
        )
        if not matches:
            continue
        if child.is_symlink():
            raise ValueError(f"symlinked vendor artifact is forbidden: {child}")
        if child.is_file():
            selected.append(child)
        elif child.is_dir():
            selected.extend(_file_tree(child))
        else:
            raise ValueError(f"vendor selection is not a regular file/directory: {child}")
    required = {"brotli", "numpy", "imagecodecs"}
    missing = sorted(name for name in required if not ((root / name).is_dir() or (root / f"{name}.py").is_file()))
    if missing:
        raise ValueError(f"vendor root is missing required static dependencies: {', '.join(missing)}")
    if not any(path.name.startswith("_brotli") for path in selected):
        raise ValueError("vendor root is missing required _brotli extension")
    return selected


def _add_path(entries: dict[str, tuple[Path | None, bytes | None, str]], name: str,
              source: Path | None, payload: bytes | None, category: str) -> None:
    normalized = _safe_relative(name).as_posix()
    if normalized in entries:
        old = entries[normalized]
        if old[0] == source and old[1] == payload:
            return
        raise ValueError(f"duplicate package entry: {normalized}")
    if source is not None:
        if source.is_symlink() or not source.is_file():
            raise ValueError(f"package source is not a regular non-symlink file: {source}")
    entries[normalized] = (source, payload, category)


def _verify_frozen(path: Path, runtime: Path, frozen: dict[str, Any]) -> None:
    try:
        rel = path.relative_to(runtime).as_posix()
    except ValueError as exc:
        raise ValueError(f"runtime selection escapes frozen runtime: {path}") from exc
    expected = frozen.get("runtime_files", {}).get(rel)
    if not isinstance(expected, str):
        raise ValueError(f"selected runtime file is absent from freeze manifest: {rel}")
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"selected frozen runtime file is not a regular file: {rel}")
    actual = sha256(path)
    if actual != expected:
        raise ValueError(f"selected frozen runtime file changed: {rel}")


def _run_evidence(run: Path, frozen_source_commit: str | None) -> dict[str, Any] | None:
    """Return actual complete archive facts, or None only when --allow-pending."""
    status_path, complete_path = run / "status.json", run / "complete.json"
    if not status_path.is_file() or not complete_path.is_file():
        return None
    status = json.loads(status_path.read_text())
    complete = json.loads(complete_path.read_text())
    archive = run / "enwik9.cix"
    required = (
        status.get("status") == "VERIFIED_COMPLETE_ARCHIVE",
        status.get("full_round_trip") is True,
        status.get("input_bytes") == CANONICAL_BYTES,
        status.get("input_sha256") == CANONICAL_SHA256,
        complete.get("status") == "VERIFIED_COMPLETE_ARCHIVE",
        complete.get("full_round_trip") is True,
        complete.get("archive_sha256") == status.get("archive_sha256"),
        complete.get("archive_bytes") == status.get("archive_bytes"),
        status.get("source_commit") == frozen_source_commit,
        complete.get("source_commit") == frozen_source_commit,
        archive.is_file(),
    )
    if not all(required):
        raise ValueError("full baseline evidence is incomplete, inconsistent, or not verified")
    actual_bytes, actual_sha = archive.stat().st_size, sha256(archive)
    if actual_bytes != status["archive_bytes"] or actual_sha != status["archive_sha256"]:
        raise ValueError("actual archive does not match verified full-baseline receipts")
    return {"path": archive, "bytes": actual_bytes, "sha256": actual_sha,
            "source_commit": status.get("source_commit"), "codec_policy": status.get("policy")}


def _launcher() -> bytes:
    return (b"#!/bin/sh\nset -eu\nROOT=$(CDPATH= cd -- \"$(dirname -- \"$0\")\" && pwd)\n"
            b"exec env -i PATH=\"${PATH:-/usr/bin:/bin}\" PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 "
            b"CIX_ROOT=\"$ROOT\" python3 -S \"$ROOT/cix-p26-bootstrap.py\" \"$@\"\n")


def _bootstrap() -> bytes:
    return (b"# Generated fixed bootstrap for the measured CIX p26 baseline.\n"
            b"import os\nimport runpy\nimport sys\nimport sysconfig\n"
            b"from pathlib import Path\n"
            b"root = Path(os.environ['CIX_ROOT']).resolve()\n"
            b"os.chdir(root)\n"
            b"stdlib = [sysconfig.get_path('stdlib'), sysconfig.get_path('platstdlib'), sysconfig.get_config_var('DESTSHARED')]\n"
            b"sys.path[:] = [str(root), str(root / 'vendor' / 'site-packages')] + [p for p in stdlib if p]\n"
            b"sys.argv = ['benchmarks.competitive_cli', *sys.argv[1:]]\n"
            b"runpy.run_module('benchmarks.competitive_cli', run_name='__main__')\n")


def _requirements() -> bytes:
    return (b"This measured p26 baseline bundle does not include CPython.\n"
            b"It requires a compatible CPython 3.12 runtime and the bundled vendor tree.\n"
            b"The required positional runtime selectors are encode and decode.\n"
            b"It is not an offline self-contained or licensed Hutter Prize submission,\n"
            b"and this source ZIP is not asserted to be an accepted Prize program form.\n")


def build_bundle(*, runtime: Path, freeze_manifest: Path, static_imports: Path,
                 vendor_root: Path, paq_roots: list[Path], output: Path) -> dict[str, Any]:
    """Build one deterministic program ZIP and return its auditable inventory."""
    runtime, vendor_root = runtime.resolve(), vendor_root.resolve()
    frozen = json.loads(freeze_manifest.read_text())
    closure = json.loads(static_imports.read_text())
    if not isinstance(frozen.get("runtime_files"), dict):
        raise ValueError("freeze manifest has no runtime file hashes")
    modules = closure.get("local_python_modules")
    if not isinstance(modules, list) or not modules:
        raise ValueError("static import inventory has no local module closure")
    entries: dict[str, tuple[Path | None, bytes | None, str]] = {}
    for path in _module_paths(runtime, modules):
        _verify_frozen(path, runtime, frozen)
        _add_path(entries, path.relative_to(runtime).as_posix(), path, None, "frozen_local_module")
    for binary, source in DEFAULT_NATIVE:
        for rel in (binary, source):
            path = runtime / rel
            _verify_frozen(path, runtime, frozen)
            _add_path(entries, rel, path, None, "frozen_native")
    for root in _vendor_paths(vendor_root):
        _add_path(entries, "vendor/site-packages/" + root.relative_to(vendor_root).as_posix(), root, None, "vendor_dependency")
    if {root.name for root in paq_roots} != {"paq8px-v215", "paq8px-v216"}:
        raise ValueError("exactly the frozen paq8px-v215 and paq8px-v216 roots are required")
    for paq in sorted((root.resolve() for root in paq_roots), key=lambda item: item.name):
        if paq.parent != (runtime / "benchmark-work/references").resolve():
            raise ValueError(f"PAQ root is outside frozen runtime references: {paq}")
        source = paq / ("paq8px-215" if paq.name.endswith("215") else "paq8px-216")
        binary = paq / "build-local/paq8px"
        for path in _file_tree(source) + [binary]:
            _verify_frozen(path, runtime, frozen)
            # Preserve paths referenced by the unmodified portfolio instead of
            # relocating PAQ under a convenient but non-runnable namespace.
            rel = path.relative_to(runtime).as_posix()
            _add_path(entries, rel, path, None, "frozen_paq")
    _add_path(entries, "cix-p26.sh", None, _launcher(), "generated_launcher")
    _add_path(entries, "cix-p26-bootstrap.py", None, _bootstrap(), "generated_bootstrap")
    _add_path(entries, "RUNTIME-REQUIREMENTS.txt", None, _requirements(), "generated_requirement")
    if output.exists():
        raise FileExistsError(f"refusing to overwrite program bundle: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(prefix=output.name + ".", suffix=".tmp", dir=output.parent, delete=False) as handle:
        temp = Path(handle.name)
    try:
        with zipfile.ZipFile(temp, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9, strict_timestamps=True) as archive:
            for name in sorted(entries):
                source, payload, _category = entries[name]
                data = source.read_bytes() if source is not None else payload
                assert data is not None
                info = zipfile.ZipInfo(name, date_time=ZIP_TIME)
                info.compress_type = zipfile.ZIP_DEFLATED
                mode = 0o755 if name == "cix-p26.sh" else (stat.S_IMODE(source.stat().st_mode) if source is not None else 0o644)
                info.external_attr = mode << 16
                archive.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
        os.replace(temp, output)
    finally:
        temp.unlink(missing_ok=True)
    inventory = []
    for name in sorted(entries):
        source, payload, category = entries[name]
        data = source.read_bytes() if source is not None else payload
        assert data is not None
        inventory.append({"path": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "category": category})
    return {"path": str(output), "bytes": output.stat().st_size, "sha256": sha256(output),
            "file_count": len(inventory), "files": inventory,
            "frozen_source_commit": frozen.get("source_commit"),
            "static_closure_commit": closure.get("research_commit"),
            "runtime_requirement": "external compatible CPython 3.12; deliberately not bundled"}


def package_report(*, runtime: Path, freeze_manifest: Path, static_imports: Path, vendor_root: Path,
                   paq_roots: list[Path], run: Path, output: Path, required_options: list[str],
                   allow_pending: bool) -> dict[str, Any]:
    frozen = json.loads(freeze_manifest.read_text())
    evidence = _run_evidence(run, frozen.get("source_commit"))
    report: dict[str, Any] = {
        "schema_version": 1,
        "profile": "frozen-p26-current-cix-baseline-python-source-v1",
        "hutter_accounting": {"mode": "split_same_program",
            "formula": "2 * actual deterministic program ZIP + actual verified archive + exact UTF-8 required option bytes",
            "required_options": ["encode", "decode", *required_options],
            "required_option_bytes": sum(len(option.encode("utf-8")) for option in ["encode", "decode", *required_options]),
            "program_zip": None, "archive": None, "total_bytes": None},
        "eligibility_status": "BASELINE_ONLY_NOT_SELF_CONTAINED_OR_LICENSED",
        "eligibility_gaps": ["CPython interpreter is external and uncounted", "no public source release", "no repository OSI license", "no formal Prize submission review"],
    }
    if evidence is None:
        if not allow_pending:
            raise ValueError("full baseline is still pending; use --allow-pending only to emit null accounting")
        report["measurement_status"] = "PENDING_OR_UNVERIFIED_FULL_ENWIK9_ARCHIVE"
        return report
    report["measurement_status"] = "VERIFIED_COMPLETE_FULL_ENWIK9_ARCHIVE"
    bundle = build_bundle(runtime=runtime, freeze_manifest=freeze_manifest, static_imports=static_imports,
                          vendor_root=vendor_root, paq_roots=paq_roots, output=output)
    option_bytes = report["hutter_accounting"]["required_option_bytes"]
    total = 2 * bundle["bytes"] + evidence["bytes"] + option_bytes
    report["hutter_accounting"].update(program_zip=bundle, archive={k: (str(v) if k == "path" else v) for k, v in evidence.items()}, total_bytes=total)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--freeze-manifest", type=Path, required=True)
    parser.add_argument("--static-imports", type=Path, required=True)
    parser.add_argument("--vendor-root", type=Path, required=True, help="frozen Python site-packages root")
    parser.add_argument("--paq-root", type=Path, action="append", required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--program-zip", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--required-option", action="append", default=[])
    parser.add_argument("--allow-pending", action="store_true")
    args = parser.parse_args()
    report = package_report(runtime=args.runtime, freeze_manifest=args.freeze_manifest,
                            static_imports=args.static_imports, vendor_root=args.vendor_root,
                            paq_roots=args.paq_root, run=args.run, output=args.program_zip,
                            required_options=args.required_option, allow_pending=args.allow_pending)
    if args.report.exists():
        raise FileExistsError(f"refusing to overwrite report: {args.report}")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
