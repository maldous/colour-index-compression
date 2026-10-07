"""Prepare, but do not build, a PyInstaller one-file p26 package plan.

This is a post-baseline preparation tool.  It writes a hash-bound PyInstaller
specification and an entrypoint which keeps user input/output paths absolute
before changing into the frozen runtime.  The generated plan is intentionally
not a completeness or Prize-eligibility claim: a real build, clean-host tests,
physical executable count, source release, and licensing review remain required.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from benchmarks import hutter_baseline_package as baseline


PYINSTALLER_VERSION = "6.22.3"
PACKAGE_NAME = "cix-p26-enwik9"


def digest(path: Path) -> str:
    return baseline.sha256(path)


def _add(entries: dict[str, Path], target: str, source: Path) -> None:
    baseline._safe_relative(target)
    old = entries.get(target)
    if old is not None and old != source:
        raise ValueError(f"two selected files map to package path {target}")
    entries[target] = source


def selected_files(*, runtime: Path, freeze_manifest: Path, static_imports: Path,
                   vendor_root: Path, paq_roots: list[Path]) -> dict[str, Path]:
    """Return the exact data-file mapping for the frozen current p26 closure."""
    runtime = runtime.resolve()
    frozen = json.loads(freeze_manifest.read_text())
    closure = json.loads(static_imports.read_text())
    modules, roots = closure.get("local_python_modules"), closure.get("non_stdlib_import_roots")
    if not isinstance(modules, list) or not isinstance(roots, list):
        raise ValueError("static import inventory is incomplete")
    entries: dict[str, Path] = {}
    for source in baseline._module_paths(runtime, modules):
        baseline._verify_frozen(source, runtime, frozen)
        _add(entries, "runtime/" + source.relative_to(runtime).as_posix(), source)
    for binary, source_rel in baseline.DEFAULT_NATIVE:
        for rel in (binary, source_rel):
            source = runtime / rel
            baseline._verify_frozen(source, runtime, frozen)
            _add(entries, "runtime/" + rel, source)
    for source in baseline._vendor_paths(vendor_root.resolve(), roots):
        _add(entries, "runtime/vendor/site-packages/" + source.relative_to(vendor_root.resolve()).as_posix(), source)
    expected_paq = {"paq8px-v215", "paq8px-v216"}
    if {path.name for path in paq_roots} != expected_paq:
        raise ValueError("exactly frozen PAQ v215 and v216 roots are required")
    references = (runtime / "benchmark-work/references").resolve()
    for root in paq_roots:
        root = root.resolve()
        if root.parent != references:
            raise ValueError(f"PAQ root lies outside frozen references: {root}")
        source_root = root / ("paq8px-215" if root.name.endswith("215") else "paq8px-216")
        binary = root / "build-local/paq8px"
        for source in [*baseline._file_tree(source_root), binary]:
            baseline._verify_frozen(source, runtime, frozen)
            _add(entries, "runtime/" + source.relative_to(runtime).as_posix(), source)
    return dict(sorted(entries.items()))


def entrypoint_source() -> str:
    """Entrypoint text for PyInstaller. Paths become absolute before chdir()."""
    return '''import argparse
import os
from pathlib import Path
import runpy
import sys

def absolute_existing(value):
    return Path(value).expanduser().resolve(strict=True)

def absolute_output(value):
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    return path.parent.resolve(strict=True) / path.name

def setup_runtime():
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    runtime, vendor = root / "runtime", root / "runtime/vendor/site-packages"
    # Do not consult caller-provided package locations after boot.
    os.environ.pop("PYTHONPATH", None)
    os.environ["PYTHONNOUSERSITE"] = "1"
    os.environ.update(OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1", NUMEXPR_NUM_THREADS="1")
    sys.path.insert(0, str(vendor))
    sys.path.insert(0, str(runtime))
    for version in ("v215", "v216"):
        paq = runtime / "benchmark-work/references" / f"paq8px-{version}" / "build-local/paq8px"
        paq.chmod(paq.stat().st_mode | 0o111)
    os.chdir(runtime)

def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("-h", "--help", action="store_true")
    parser.add_argument("operation", choices=("encode", "decode"), nargs="?")
    parser.add_argument("source", nargs="?")
    parser.add_argument("destination", nargs="?")
    args = parser.parse_args()
    if args.help:
        if any((args.operation, args.source, args.destination)):
            parser.error("--help takes no operation or paths")
        setup_runtime()
        sys.argv = ["benchmarks.competitive_cli", "--help"]
        runpy.run_module("benchmarks.competitive_cli", run_name="__main__")
        return
    if not all((args.operation, args.source, args.destination)):
        parser.error("operation, source and destination are required")
    source, destination = absolute_existing(args.source), absolute_output(args.destination)
    setup_runtime()
    sys.argv = ["benchmarks.competitive_cli", args.operation, str(source), str(destination)]
    runpy.run_module("benchmarks.competitive_cli", run_name="__main__")

if __name__ == "__main__":
    main()
'''


def _is_elf(path: Path) -> bool:
    with path.open("rb") as source:
        return source.read(4) == b"\x7fELF"


def payload_maps(selected: dict[str, Path]) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Classify every selected ELF explicitly for PyInstaller dependency analysis."""
    datas, binaries = [], []
    for target, source in selected.items():
        row = (str(source), str(Path(target).parent))
        (binaries if _is_elf(source) else datas).append(row)
    return datas, binaries


def spec_source(entrypoint: Path, selected: dict[str, Path], hiddenimports: list[str], pathex: list[Path], output_name: str = PACKAGE_NAME) -> str:
    """Generate current-PyInstaller one-file spec with explicit ELF analysis."""
    datas, binaries = payload_maps(selected)
    return f'''# Generated; run only with the recorded PyInstaller wheel and Python 3.12.
# This uses one-file mode: no collection directory is emitted.
a = Analysis([{str(entrypoint)!r}], pathex={[str(path) for path in pathex]!r}, binaries={binaries!r}, datas={datas!r}, hiddenimports={hiddenimports!r}, hookspath=[], runtime_hooks=[], excludes=[], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name={output_name!r}, console=True, strip=False, upx=False)
'''


def prepare(*, runtime: Path, freeze_manifest: Path, static_imports: Path, vendor_root: Path,
            paq_roots: list[Path], run: Path, output: Path) -> dict[str, Any]:
    """Write a post-run build plan. Does not invoke PyInstaller or copy payloads."""
    frozen = json.loads(freeze_manifest.read_text())
    evidence = baseline._run_evidence(run, frozen.get("source_commit"))
    if evidence is None:
        raise ValueError("full baseline remains pending; no executable plan is bound to an unverified archive")
    if output.exists():
        raise FileExistsError(f"refusing to overwrite preparation directory: {output}")
    selected = selected_files(runtime=runtime, freeze_manifest=freeze_manifest, static_imports=static_imports,
                              vendor_root=vendor_root, paq_roots=paq_roots)
    output.mkdir(parents=True)
    entrypoint, spec = output / "cix_p26_entrypoint.py", output / "cix_p26.spec"
    entrypoint.write_text(entrypoint_source())
    closure = json.loads(static_imports.read_text())
    hiddenimports = [*closure["local_python_modules"], *closure["non_stdlib_import_roots"]]
    spec.write_text(spec_source(entrypoint, selected, hiddenimports, [runtime.resolve(), vendor_root.resolve()]))
    datas, binaries = payload_maps(selected)
    inventory = [{"target": target, "source_sha256": digest(source), "source_bytes": source.stat().st_size}
                 for target, source in selected.items()]
    plan = {
        "schema_version": 1,
        "status": "PREPARED_NOT_BUILT",
        "target": "Linux x86-64 PyInstaller one-file executable, exact frozen p26 closure",
        "pyinstaller": {"version": PYINSTALLER_VERSION, "acquisition": "download wheel after baseline, record exact filename and SHA-256, install offline with --require-hashes"},
        "freeze": {"source_commit": frozen.get("source_commit"), "codec_commit": frozen.get("codec_commit")},
        "verified_archive": {key: (str(value) if key == "path" else value) for key, value in evidence.items()},
        "entrypoint": {"path": entrypoint.name, "sha256": digest(entrypoint)},
        "spec": {"path": spec.name, "sha256": digest(spec)},
        "selected_files": inventory,
        "payload_classification": {"data_targets": [target for target, _ in datas],
                                   "binary_targets": [target for target, _ in binaries],
                                   "note": "PyInstaller may add, relocate, or rewrite ELF dependencies; inspect and hash actual output before counting."},
        "required_runtime_selectors": ["encode", "decode"],
        "physical_executable_bytes": None,
        "package_total_bytes": None,
        "eligibility_gaps": ["PyInstaller build and clean-host execution unmeasured", "Linux system ABI dependency policy unresolved", "CIX public source release absent", "CIX root OSI license absent", "third-party license/package review incomplete", "Prize reviewer approval absent"],
    }
    (output / "plan.json").write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n")
    return plan


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--freeze-manifest", type=Path, required=True)
    parser.add_argument("--static-imports", type=Path, required=True)
    parser.add_argument("--vendor-root", type=Path, required=True)
    parser.add_argument("--paq-root", type=Path, action="append", required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    prepare(runtime=args.runtime, freeze_manifest=args.freeze_manifest, static_imports=args.static_imports,
            vendor_root=args.vendor_root, paq_roots=args.paq_root, run=args.run, output=args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
