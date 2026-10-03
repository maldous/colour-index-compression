#!/usr/bin/env python3
"""Assemble the private, review-ready Rust third-party notice document."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


LINUX_RUNTIME = {
    "bitflags", "block-buffer", "cfg-if", "cpufeatures", "crc32fast", "crypto-common",
    "ctrlc", "digest", "flate2", "generic-array", "libc", "libz-sys", "nix",
    "num-bigint", "num-integer", "num-traits", "sha2", "typenum",
}
BUILD_ONLY = {"autocfg", "cc", "cfg_aliases", "find-msvc-tools", "pkg-config", "shlex", "vcpkg", "version_check"}
APPLE_ONLY = {"block2", "dispatch2", "objc2", "objc2-encode"}
WINDOWS_ONLY = {"windows-link", "windows-sys"}
APPLE_UPSTREAM = {"block2": "block2-0.6.2", "dispatch2": "dispatch2-0.3.1", "objc2": "objc2-0.6.4", "objc2-encode": "objc2-encode-4.1.0"}


def scope(name: str) -> str:
    if name in LINUX_RUNTIME:
        return "Linux runtime"
    if name in BUILD_ONLY:
        return "build-only"
    if name in APPLE_ONLY:
        return "Apple target-only"
    if name in WINDOWS_ONLY:
        return "Windows target-only"
    raise ValueError(f"unclassified crate: {name}")


def fenced(text: str) -> str:
    return "```text\n" + text.rstrip() + "\n```\n"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--upstream", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f"refusing to overwrite: {args.output}")
    evidence = args.evidence.resolve()
    upstream = args.upstream.resolve()
    records = json.loads((evidence / "cargo-lock-licences.json").read_text())["packages"]
    names = {record["name"] for record in records}
    expected = LINUX_RUNTIME | BUILD_ONLY | APPLE_ONLY | WINDOWS_ONLY
    if names != expected:
        raise SystemExit(f"scope map mismatch: lock-only={sorted(names - expected)}, map-only={sorted(expected - names)}")
    lines = [
        "# Rust third-party notices — CIX 0.1.0",
        "",
        "This notice records the registry crates resolved by the Cargo.lock shipped with this CIX source distribution. It preserves the reproduced licence and notice texts used for this release. The declared licence expressions are package metadata, not an independent legal interpretation.",
        "",
        "`Linux runtime` means Cargo resolved the crate for the x86_64-unknown-linux-gnu final CLI dependency graph; `build-only` means it was used while building; target-only entries remain in the lock for the listed platform. System libraries are not Rust crates and remain covered by their distribution packages and existing CIX native notices.",
        "",
        "## Locked component inventory",
        "",
        "| Crate | Version | Cargo.lock checksum | Registry source | Cargo-declared licence | Build scope |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for record in records:
        source = str(record["registry_source"]).replace("registry+", "")
        lines.append(f"| `{record['name']}` | `{record['version']}` | `{record['cargo_lock_checksum']}` | `{source}` | `{record['declared_license']}` | {scope(record['name'])} |")
    lines += [
        "",
        "## Retained cached crate notices",
        "",
        "The following are verbatim top-level licence/notice files reproduced from registry crate sources matching the names, versions, and Cargo.lock checksums in the inventory. Each reproduced file has its SHA-256 beside its name.",
        "",
    ]
    for record in records:
        crate = f"{record['name']}-{record['version']}"
        files = record["copied_notice_files"]
        if not files:
            continue
        lines += [f"### `{crate}`", ""]
        for entry in files:
            notice = evidence / "LICENSES" / crate / entry["name"]
            lines += [f"#### `{entry['name']}` — SHA-256 `{entry['sha256']}`", "", fenced(notice.read_text(errors="replace"))]
    lines += [
        "## Apple-target crate provenance retained from upstream",
        "",
        "The four Apple target-only crate archives do not carry a top-level licence/notice file. Their package metadata names the repository `https://github.com/madsmtm/objc2`; the tag-pinned upstream `LICENSE.md` text is reproduced below with its source URL and SHA-256. The upstream text notes Apple SDK derivation and its associated licensing caveat.",
        "",
    ]
    for name, tag in APPLE_UPSTREAM.items():
        record = next(item for item in records if item["name"] == name)
        file = upstream / f"{tag}-LICENSE.md"
        source_url = f"https://raw.githubusercontent.com/madsmtm/objc2/{tag}/LICENSE.md"
        lines += [f"### `{name}` {record['version']} — `{record['declared_license']}`", "", f"Source: {source_url}", "", f"SHA-256: `{sha256(file)}`", "", fenced(file.read_text())]
    lines += [
        "## Canonical terms retained for the Apple dispatch alternative",
        "",
        "`dispatch2` declares `Zlib OR Apache-2.0 OR MIT`. The tag-pinned upstream policy above identifies that choice. The official zlib 1.3.1 source licence text is retained here for the Zlib alternative; Apache-2.0 and MIT terms are also present verbatim in the cached crate notices above. This does not select a licence on behalf of a downstream distributor.",
        "",
        fenced((upstream / "zlib-v1.3.1-LICENSE").read_text()),
        "## Verification information",
        "",
        "- The inventory records each registry package's Cargo.lock checksum.",
        "- Every reproduced cached licence or notice file has a SHA-256 in its heading.",
        "- Every reproduced Apple upstream policy file has its tag-pinned URL and SHA-256 immediately before its text.",
        "- The scope classification was derived from `cargo tree --offline --target x86_64-unknown-linux-gnu --edges normal,build`; target-only membership comes from Cargo.lock platform conditional dependencies.",
    ]
    args.output.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
