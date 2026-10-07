#!/usr/bin/env python3
"""Run a bounded local engineering export/build/install exercise, never a release."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from export_source import materialise
from validate_source_allowlist import ENGINEERING_PROFILE

REQUIRED_PROVIDER_KEYS = (
    "CIX_RUNTIME_PAQ_V215_BRIDGE", "CIX_RUNTIME_PAQ_V216_BRIDGE",
    "CIX_RUNTIME_PAQ_JOINT_DISCOUNT_BRIDGE", "CIX_RUNTIME_PAQ_STORE_STATE_BRIDGE",
    "CIX_RUNTIME_JXL_BRIDGE", "CIX_RUNTIME_SPATIAL_BRIDGE",
    "CIX_RUNTIME_JXL_LIBRARY", "CIX_RUNTIME_JXL_THREADS_LIBRARY",
    "CIX_RUNTIME_JXL_CMS_LIBRARY", "CIX_RUNTIME_BROTLIDEC_LIBRARY",
    "CIX_RUNTIME_BROTLIENC_LIBRARY", "CIX_RUNTIME_BROTLICOMMON_LIBRARY",
    "CIX_RUNTIME_CHARLS_LIBRARY", "CIX_RUNTIME_OPENJPEG_LIBRARY",
)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def require_absolute_file(value: str, label: str) -> Path:
    path = Path(value)
    if not path.is_absolute() or not path.is_file() or path.is_symlink():
        raise ValueError(f"{label} must be an existing, non-symlink absolute file")
    return path


def read_provider_closure(path: Path) -> tuple[Path, dict[str, Path], dict[str, str], list[dict[str, str]]]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("schema") != "cix-engineering-provider-closure-v1":
        raise ValueError("unsupported engineering provider closure schema")
    if document.get("status") != "engineering_inputs_selected":
        raise ValueError("provider closure status must be engineering_inputs_selected")
    target = document.get("target", {})
    if target.get("os") != "linux" or target.get("linkage") != "ELF shared objects":
        raise ValueError("engineering runtime staging currently accepts selected Linux ELF providers only")
    readelf = require_absolute_file(document.get("readelf", ""), "readelf")
    selected: dict[str, Path] = {}
    hashes: dict[str, str] = {}
    providers = document.get("providers", {})
    for key in REQUIRED_PROVIDER_KEYS:
        item = providers.get(key)
        if not isinstance(item, dict):
            raise ValueError(f"provider closure missing {key}")
        selected[key] = require_absolute_file(str(item.get("path", "")), key)
        expected = item.get("sha256")
        if not isinstance(expected, str) or len(expected) != 64:
            raise ValueError(f"provider closure has no SHA-256 for {key}")
        actual = digest(selected[key])
        if actual != expected:
            raise ValueError(f"provider hash mismatch for {key}: {actual}")
        hashes[key] = actual
    dependencies = document.get("source_dependencies")
    if not isinstance(dependencies, list) or not dependencies:
        raise ValueError("provider closure must declare source/package dependencies")
    required_fields = {"component", "identity", "license_expression", "notice_reference", "provisioning"}
    for item in dependencies:
        if not isinstance(item, dict) or not required_fields.issubset(item):
            raise ValueError("each source dependency needs identity, licence, notice, and provisioning fields")
        if any("fill " in str(item[field]).lower() for field in required_fields):
            raise ValueError("provider source dependency still has an unfilled field")
    return readelf, selected, hashes, dependencies



def stage_provider_notices(closure: Path, notice_manifest: Path, exported: Path) -> dict[str, object]:
    """Verify selected provider identities and stage only declared notice texts."""
    closure_document = json.loads(closure.read_text(encoding="utf-8"))
    notices = json.loads(notice_manifest.read_text(encoding="utf-8"))
    if notices.get("schema") != "cix-selected-runtime-provider-notices-v1":
        raise ValueError("unsupported provider notice manifest schema")
    closure_providers = closure_document.get("providers")
    notice_providers = notices.get("providers")
    notice_files = notices.get("notice_files")
    unresolved = notices.get("unresolved")
    if not isinstance(closure_providers, dict) or not isinstance(notice_providers, dict):
        raise ValueError("provider notice manifest and closure require provider maps")
    if set(closure_providers) != set(notice_providers):
        raise ValueError("provider notice manifest must cover exactly the selected closure providers")
    if not isinstance(notice_files, dict) or not isinstance(unresolved, list):
        raise ValueError("provider notice manifest lacks notice files or unresolved list")
    for key, provider in closure_providers.items():
        expected = provider.get("sha256") if isinstance(provider, dict) else None
        observed = notice_providers[key].get("sha256") if isinstance(notice_providers[key], dict) else None
        if not isinstance(expected, str) or observed != expected:
            raise ValueError(f"provider notice identity mismatch: {key}")
    output = exported / "third_party" / "provider-notices"
    licenses = output / "licenses"
    licenses.mkdir(parents=True, exist_ok=False)
    copied: dict[str, str] = {}
    for relative, expected in sorted(notice_files.items()):
        candidate = notice_manifest.parent / relative
        if (not isinstance(relative, str) or not isinstance(expected, str) or
                Path(relative).is_absolute() or ".." in Path(relative).parts):
            raise ValueError("unsafe provider notice entry")
        source = require_absolute_file(str(candidate.resolve()), f"provider notice {relative}")
        if digest(source) != expected:
            raise ValueError(f"provider notice hash mismatch: {relative}")
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied[relative] = digest(target)
        if copied[relative] != expected:
            raise ValueError(f"staged provider notice hash mismatch: {relative}")
    exported_providers = json.loads(json.dumps(notice_providers))
    for provider in exported_providers.values():
        if isinstance(provider, dict):
            provider.pop("source_receipt", None)
    identity = {"schema": notices["schema"], "scope": notices.get("scope"),
                "providers": exported_providers, "notice_files": copied,
                "unresolved": unresolved,
                "export_note": "Private evidence locations are excluded; provider hashes, notice hashes, and unresolved items are retained."}
    rendered = json.dumps(identity, indent=2, sort_keys=True) + "\n"
    private_markers = ("/home/user/", "benchmark-work/", "docs/research/", "colour-index-compression/")
    if any(marker in rendered for marker in private_markers):
        raise ValueError("staged provider notice identity contains a private evidence marker")
    (output / "PROVIDER-NOTICES.json").write_text(rendered, encoding="utf-8")
    return identity

def run(argv: list[str], cwd: Path, env: dict[str, str], commands: list[list[str]]) -> None:
    commands.append(argv)
    subprocess.run(argv, cwd=cwd, env=env, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--provider-closure", type=Path, required=True)
    parser.add_argument("--work-directory", type=Path, required=True,
                        help="new bounded work directory")
    parser.add_argument("--cargo", default="cargo")
    parser.add_argument("--cmake", default="cmake")
    parser.add_argument("--make", default="make")
    parser.add_argument("--jobs", type=int, default=2)
    args = parser.parse_args()
    if not 1 <= args.jobs <= 4:
        raise ValueError("jobs must be within the shared one-to-four-core policy")
    work = args.work_directory.resolve()
    if work.exists():
        raise ValueError(f"work directory already exists: {work}")
    readelf, providers, provider_hashes, dependencies = read_provider_closure(
        args.provider_closure.resolve()
    )
    work.mkdir(parents=True)
    commands: list[list[str]] = []
    try:
        source_output = work / "source-output"
        exported = materialise(args.source_root, args.manifest, source_output, ENGINEERING_PROFILE)
        environment = os.environ.copy()
        environment.update({
            "CARGO_NET_OFFLINE": "true",
            "CARGO_BUILD_JOBS": str(args.jobs),
            "CARGO_TARGET_DIR": str(work / "target"),
        })
        paq_sources = args.source_root.resolve() / "packaging" / "export" / "stage_provider_sources.py"
        notice_manifest = args.source_root.resolve() / "packaging" / "notices" / "provider-notices.json"
        provider_notice_identity = stage_provider_notices(args.provider_closure.resolve(), notice_manifest, exported)
        gpl_text = json.loads(args.provider_closure.read_text(encoding="utf-8"))["gpl2_text"]["path"]
        receipt_root = args.source_root.resolve().parents[1]
        run(["python3", str(paq_sources), "--closure", str(args.provider_closure.resolve()),
             "--receipt-root", str(receipt_root), "--export-root", str(exported),
             "--gpl2-text", gpl_text], exported, environment, commands)
        run([args.cargo, "generate-lockfile", "--offline"], exported, environment, commands)
        run([args.cargo, "metadata", "--locked", "--offline", "--format-version", "1"], exported, environment, commands)
        stage = work / "stage"
        run([args.make, "PROFILE=release-lto", f"CARGO={args.cargo}",
             f"CARGO_TARGET_DIR={work / 'target'}", "PREFIX=/usr", f"DESTDIR={stage}", "install"],
            exported, environment, commands)
        runtime_build = work / "runtime-build"
        runtime_command = [
            args.cmake, "-S", "rust/cix-native/packaging/runtime", "-B", str(runtime_build),
            "-DCMAKE_INSTALL_PREFIX=/usr", "-DCIX_RUNTIME_CAPABILITY=full-engine",
            f"-DCIX_RUNTIME_READELF={readelf}",
            f"-DCIX_RUNTIME_CIX_EXECUTABLE={work / 'target' / 'release-lto' / 'cix'}",
        ] + [f"-D{key}={providers[key]}" for key in REQUIRED_PROVIDER_KEYS]
        run(runtime_command, exported, environment, commands)
        runtime_env = environment.copy()
        runtime_env["DESTDIR"] = str(stage)
        run([args.cmake, "--install", str(runtime_build)], exported, runtime_env, commands)
        installed_bin = stage / "usr" / "bin"
        installed_lib = stage / "usr" / "lib" / "cix"
        expected_names = {
            "CIX_RUNTIME_PAQ_V215_BRIDGE": "libcix_paq_v215_bridge.so",
            "CIX_RUNTIME_PAQ_V216_BRIDGE": "libcix_paq_v216_bridge.so",
            "CIX_RUNTIME_PAQ_JOINT_DISCOUNT_BRIDGE": "libcix_paq_joint_discount_bridge.so",
            "CIX_RUNTIME_PAQ_STORE_STATE_BRIDGE": "libcix_paq_store_state_bridge.so",
            "CIX_RUNTIME_JXL_BRIDGE": "libcix_jxl_bridge.so",
            "CIX_RUNTIME_SPATIAL_BRIDGE": "libcix_spatial_bridge.so",
            "CIX_RUNTIME_JXL_LIBRARY": "libjxl.so.0.12.0",
            "CIX_RUNTIME_JXL_THREADS_LIBRARY": "libjxl_threads.so.0.12.0",
            "CIX_RUNTIME_JXL_CMS_LIBRARY": "libjxl_cms.so.0.12.0",
            "CIX_RUNTIME_BROTLIDEC_LIBRARY": "libbrotlidec.so.1.2.0",
            "CIX_RUNTIME_BROTLIENC_LIBRARY": "libbrotlienc.so.1.2.0",
            "CIX_RUNTIME_BROTLICOMMON_LIBRARY": "libbrotlicommon.so.1.2.0",
            "CIX_RUNTIME_CHARLS_LIBRARY": "libcharls.so.2.4.2",
            "CIX_RUNTIME_OPENJPEG_LIBRARY": "libopenjp2.so.2.5.0",
        }
        for name in ("cix", "uncix", "cixcat"):
            if not (installed_bin / name).exists():
                raise ValueError(f"missing installed command: {name}")
        if not (installed_bin / "uncix").is_symlink() or not (installed_bin / "cixcat").is_symlink():
            raise ValueError("installed aliases are not symlinks")
        installed_hashes = {"cix": digest(installed_bin / "cix")}
        if installed_hashes["cix"] != digest(work / "target" / "release-lto" / "cix"):
            raise ValueError("runtime installer changed the selected CIX executable")
        for key, name in expected_names.items():
            path = installed_lib / name
            if not path.is_file():
                raise ValueError(f"missing installed provider bridge: {name}")
            installed_hashes[name] = digest(path)
            if installed_hashes[name] != provider_hashes[key]:
                raise ValueError(f"installed provider hash mismatch: {name}")
        run([str(installed_bin / "cix"), "--version"], exported, environment, commands)
        run([str(installed_bin / "uncix"), "--version"], exported, environment, commands)
        run([str(installed_bin / "cixcat"), "--version"], exported, environment, commands)
        receipt = {
            "schema": "cix-engineering-export-receipt-v1",
            "status": "engineering_validation_not_release",
            "release_acceptance": False,
            "source_profile": ENGINEERING_PROFILE,
            "workspace_lock_sha256": digest(exported / "Cargo.lock"),
            "provider_hashes": provider_hashes,
            "installed_hashes": installed_hashes,
            "source_dependencies": dependencies,
            "provider_notice_identity": provider_notice_identity,
            "commands": commands,
            "non_claims": [
                "This receipt does not create or accept final-dependency-closure.json.",
                "This exercise does not qualify provider loading, archive compatibility, package-manager artifacts, non-Linux targets, or a release.",
                "Provider source/license declarations are inputs to later RC45 review, not a legal determination."
            ]
        }
        (work / "engineering-export-receipt.json").write_text(
            json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except Exception:
        (work / "FAILED").write_text("engineering export job failed; inspect scheduler output\n", encoding="utf-8")
        raise


if __name__ == "__main__":
    main()
