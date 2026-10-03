#!/usr/bin/env python3
"""Create private Rust dependency attribution evidence from an existing Cargo cache.

No crates are downloaded. The output is evidence for release review, not a
legal conclusion or a public release artifact.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tomllib


NOTICE_PREFIXES = ("license", "copying", "notice", "copyright")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def notice_files(crate: Path) -> list[Path]:
    return sorted(
        (path for path in crate.iterdir() if path.is_file() and path.name.lower().startswith(NOTICE_PREFIXES)),
        key=lambda path: path.name.lower(),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--registry-src", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    lock = args.lock.resolve()
    registry = args.registry_src.resolve()
    output = args.output.resolve()
    if not lock.is_file() or not registry.is_dir():
        raise SystemExit("--lock must be a file and --registry-src must be an existing directory")
    if output.exists():
        raise SystemExit(f"refusing to overwrite existing output: {output}")
    packages = tomllib.loads(lock.read_text())["package"]
    records: list[dict[str, object]] = []
    missing: list[str] = []
    for package in sorted(packages, key=lambda item: (item["name"], item["version"])):
        source = package.get("source", "")
        if not source.startswith("registry+"):
            continue
        name, version = package["name"], package["version"]
        crate = registry / f"{name}-{version}"
        if not crate.is_dir():
            raise SystemExit(f"missing cached crate source: {crate}")
        manifest = tomllib.loads((crate / "Cargo.toml").read_text()).get("package", {})
        files = notice_files(crate)
        copied: list[dict[str, str]] = []
        destination = output / "LICENSES" / f"{name}-{version}"
        for notice in files:
            destination.mkdir(parents=True, exist_ok=True)
            target = destination / notice.name
            shutil.copyfile(notice, target)
            copied.append({"name": notice.name, "sha256": sha256(notice)})
        if not files:
            missing.append(f"- `{name}` {version}: Cargo metadata declares `{manifest.get('license', '') or manifest.get('license-file', '') or 'no licence field'}`; no top-level local licence/notice file was found in this cache entry.")
        records.append(
            {
                "name": name,
                "version": version,
                "registry_source": source,
                "cargo_lock_checksum": package.get("checksum"),
                "declared_license": manifest.get("license"),
                "declared_license_file": manifest.get("license-file"),
                "copied_notice_files": copied,
            }
        )
    output.mkdir(parents=True, exist_ok=True)
    (output / "cargo-lock-licences.json").write_text(json.dumps({"schema": "cix-rust-notice-evidence-v1", "packages": records}, indent=2) + "\n")
    (output / "MISSING_LOCAL_NOTICE_FILES.md").write_text(
        "# Cached crate entries without a top-level notice file\n\n"
        "This is a review queue, not a conclusion that a notice is absent upstream.\n\n"
        + ("\n".join(missing) if missing else "None.\n")
        + "\n"
    )
    print(f"wrote {len(records)} registry crate records to {output}")


if __name__ == "__main__":
    main()
