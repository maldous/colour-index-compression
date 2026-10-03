#!/usr/bin/env python3
"""Private validation of CIX source and binary release artifacts.

This script is intentionally not a public release tool. It writes all work,
logs, and evidence below a scheduler-owned work directory, never installs to
the host, and refuses to run unless --execute is supplied.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import time
from typing import Any


COMMANDS = ("cix", "uncix", "cixcat")
TEMPORARY_CAP_BYTES = 4_000_000_000


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packages-dir", type=Path, required=True)
    parser.add_argument("--reference-bin", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--cargo", type=Path, required=True, help="absolute stable Cargo executable")
    parser.add_argument("--jobs", type=int, default=2, help="Cargo build jobs, capped at 4")
    parser.add_argument("--timeout", type=int, default=1200, help="whole validation limit in seconds")
    parser.add_argument("--execute", action="store_true")
    return parser.parse_args()


def require_directory(path: Path, label: str) -> Path:
    resolved = path.resolve()
    if not resolved.is_dir():
        raise SystemExit(f"{label} is not a directory: {resolved}")
    return resolved


def require_file(path: Path, label: str) -> Path:
    resolved = path.resolve()
    if not resolved.is_file():
        raise SystemExit(f"{label} is not a file: {resolved}")
    return resolved


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tree_size(path: Path) -> int:
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def enforce_budget(path: Path) -> None:
    size = tree_size(path)
    if size > TEMPORARY_CAP_BYTES:
        raise RuntimeError(f"temporary validation work exceeds 4 GB: {size} bytes")


def find_one(directory: Path, pattern: str, label: str) -> Path:
    matches = sorted(directory.glob(pattern))
    if len(matches) != 1:
        raise RuntimeError(f"expected exactly one {label} ({pattern}); found {len(matches)}")
    return matches[0]


class Evidence:
    def __init__(self, root: Path, timeout: int) -> None:
        self.root = root
        self.deadline = time.monotonic() + timeout
        self.events: list[dict[str, Any]] = []

    def remaining(self) -> int:
        seconds = int(self.deadline - time.monotonic())
        if seconds <= 0:
            raise RuntimeError("whole validation timeout exceeded")
        return seconds

    def record(self, name: str, **fields: Any) -> None:
        self.events.append({"name": name, "at_unix": int(time.time()), **fields})

    def run(self, name: str, command: list[str], *, cwd: Path, env: dict[str, str]) -> str:
        started = time.monotonic()
        try:
            result = subprocess.run(
                command,
                cwd=cwd,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=self.remaining(),
                check=True,
            )
        except subprocess.CalledProcessError as error:
            self.record(
                name,
                command=command,
                cwd=str(cwd),
                exit_code=error.returncode,
                elapsed_seconds=round(time.monotonic() - started, 3),
                stdout=error.stdout,
                stderr=error.stderr,
            )
            raise RuntimeError(f"{name} failed: {error.stderr.strip() or error.stdout.strip()}") from error
        except subprocess.TimeoutExpired as error:
            self.record(
                name,
                command=command,
                cwd=str(cwd),
                timeout=True,
                elapsed_seconds=round(time.monotonic() - started, 3),
                stdout=error.stdout,
                stderr=error.stderr,
            )
            raise RuntimeError(f"{name} exceeded the whole validation timeout") from error
        self.record(
            name,
            command=command,
            cwd=str(cwd),
            exit_code=0,
            elapsed_seconds=round(time.monotonic() - started, 3),
            stdout=result.stdout,
            stderr=result.stderr,
        )
        return result.stdout


def extract_source(source_tar: Path, destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(source_tar, "r:gz") as archive:
        names = archive.getnames()
        roots = {name.split("/", 1)[0] for name in names if name and not name.startswith("/")}
        if roots != {"cix-0.1.0"}:
            raise RuntimeError(f"unexpected source archive root: {sorted(roots)}")
        for member in archive.getmembers():
            target = (destination / member.name).resolve()
            if not target.is_relative_to(destination.resolve()) or member.issym() or member.islnk():
                raise RuntimeError(f"unsafe path in source archive: {member.name}")
        archive.extractall(destination)
    return destination / "cix-0.1.0"


def command_hashes(bin_dir: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for name in COMMANDS:
        binary = require_file(bin_dir / name, f"{name} binary")
        hashes[name] = sha256(binary)
    return hashes


def tiny_roundtrip(evidence: Evidence, bin_dir: Path, work: Path, label: str, env: dict[str, str]) -> None:
    test_dir = work / f"roundtrip-{label}"
    test_dir.mkdir()
    source = test_dir / "input.bin"
    archive = test_dir / "input.cix"
    restored = test_dir / "restored.bin"
    source.write_bytes(b"CIX release validation\n" * 257)
    evidence.run(
        f"{label}-compress",
        [str(bin_dir / "cix"), "-f", "-o", str(archive), str(source)],
        cwd=test_dir,
        env=env,
    )
    evidence.run(
        f"{label}-test",
        [str(bin_dir / "uncix"), "-t", str(archive)],
        cwd=test_dir,
        env=env,
    )
    evidence.run(
        f"{label}-restore",
        [str(bin_dir / "uncix"), "-f", "-o", str(restored), str(archive)],
        cwd=test_dir,
        env=env,
    )
    if source.read_bytes() != restored.read_bytes():
        raise RuntimeError(f"{label} roundtrip bytes differ")
    streamed = evidence.run(
        f"{label}-cixcat",
        [str(bin_dir / "cixcat"), str(archive)],
        cwd=test_dir,
        env=env,
    ).encode()
    if streamed != source.read_bytes():
        raise RuntimeError(f"{label} cixcat bytes differ")


def validate_versions(evidence: Evidence, bin_dir: Path, label: str, env: dict[str, str]) -> None:
    for name in COMMANDS:
        evidence.run(f"{label}-{name}-version", [str(bin_dir / name), "--version"], cwd=bin_dir, env=env)


def extract_deb(evidence: Evidence, deb: Path, destination: Path, env: dict[str, str]) -> Path:
    tool = shutil.which("dpkg-deb")
    if tool is None:
        raise RuntimeError("dpkg-deb is required to inspect the Debian package")
    evidence.run("extract-deb", [tool, "-x", str(deb), str(destination)], cwd=destination.parent, env=env)
    return destination / "usr/bin"


def extract_rpm(evidence: Evidence, rpm: Path, destination: Path, env: dict[str, str]) -> Path:
    rpm2cpio = shutil.which("rpm2cpio")
    cpio = shutil.which("cpio")
    if rpm2cpio is None or cpio is None:
        raise RuntimeError("rpm2cpio and cpio are required to inspect the RPM package")
    started = time.monotonic()
    with subprocess.Popen([rpm2cpio, str(rpm)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env) as producer:
        with subprocess.Popen(
            [cpio, "-idm", "--quiet"], cwd=destination, stdin=producer.stdout,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env,
        ) as consumer:
            assert producer.stdout is not None
            producer.stdout.close()
            consumer_stdout, consumer_stderr = consumer.communicate(timeout=evidence.remaining())
        producer_stderr = producer.stderr.read().decode(errors="replace") if producer.stderr else ""
        producer_rc = producer.wait(timeout=evidence.remaining())
    evidence.record(
        "extract-rpm",
        command=[rpm2cpio, str(rpm), "|", cpio, "-idm", "--quiet"],
        cwd=str(destination),
        exit_code=0 if producer_rc == 0 and consumer.returncode == 0 else 1,
        elapsed_seconds=round(time.monotonic() - started, 3),
        stdout=consumer_stdout.decode(errors="replace"),
        stderr=producer_stderr + consumer_stderr.decode(errors="replace"),
    )
    if producer_rc != 0 or consumer.returncode != 0:
        raise RuntimeError("RPM extraction failed")
    return destination / "usr/bin"


def validate_hashes(label: str, bin_dir: Path, expected: dict[str, str], evidence: Evidence) -> None:
    actual = command_hashes(bin_dir)
    evidence.record(f"{label}-hashes", expected=expected, actual=actual)
    if actual != expected:
        raise RuntimeError(f"{label} command hashes differ from selected binaries")


def validate_dsc(evidence: Evidence, packages_dir: Path, destination: Path, env: dict[str, str]) -> None:
    dscs = sorted(packages_dir.glob("cix_0.1.0-1.dsc"))
    if not dscs:
        evidence.record("dsc-shape", skipped="no DSC artifact supplied")
        return
    tool = shutil.which("dpkg-source")
    if tool is None:
        raise RuntimeError("dpkg-source is required to inspect the DSC artifact")
    evidence.run("extract-dsc", [tool, "-x", str(dscs[0]), str(destination)], cwd=packages_dir, env=env)
    expected = (destination / "debian/control", destination / "debian/rules", destination / "Cargo.toml")
    missing = [str(path.relative_to(destination)) for path in expected if not path.is_file()]
    if missing:
        raise RuntimeError(f"DSC extraction has an unexpected shape; missing {', '.join(missing)}")
    evidence.record("dsc-shape", source_root=str(destination), expected_files=[str(path.relative_to(destination)) for path in expected])


def main() -> None:
    args = parse_args()
    packages_dir = require_directory(args.packages_dir, "packages directory")
    reference_bin = require_directory(args.reference_bin, "reference binary directory")
    work_parent = require_directory(args.work_dir, "work directory")
    cargo = require_file(args.cargo, "Cargo executable")
    if not args.execute:
        print("Private validation plan only. Pass --execute under the scheduler to run it.")
        return
    if not 1 <= args.jobs <= 4:
        raise SystemExit("--jobs must be between 1 and 4")
    if args.timeout <= 0:
        raise SystemExit("--timeout must be positive")
    if shutil.disk_usage(work_parent).free < TEMPORARY_CAP_BYTES:
        raise SystemExit("work directory needs at least 4 GB free")
    source_tar = find_one(packages_dir, "cix-0.1.0.tar.gz", "source tarball")
    deb = find_one(packages_dir, "cix_0.1.0-1_*.deb", "Debian package")
    rpm = find_one(packages_dir, "cix-0.1.0-1*.rpm", "RPM package")
    environment = os.environ.copy()
    environment.update(
        {
            "CARGO_NET_OFFLINE": "true",
            "CARGO_BUILD_JOBS": str(args.jobs),
            "TMPDIR": str(work_parent),
        }
    )
    evidence = Evidence(work_parent, args.timeout)
    status = "failed"
    error: str | None = None
    with tempfile.TemporaryDirectory(prefix="cix-third-party-", dir=work_parent) as temporary:
        root = Path(temporary)
        try:
            source_root = extract_source(source_tar, root / "source")
            enforce_budget(root)
            target_dir = root / "target"
            evidence.run(
                "source-build-release-lto",
                ["make", "PROFILE=release-lto", f"CARGO={cargo}", f"CARGO_TARGET_DIR={target_dir}", "build"],
                cwd=source_root,
                env=environment,
            )
            stage = root / "stage"
            evidence.run(
                "stage-install-only",
                [
                    "make", "PROFILE=release-lto", f"CARGO={cargo}", f"CARGO_TARGET_DIR={target_dir}",
                    "PREFIX=/usr", f"DESTDIR={stage}", "install-only",
                ],
                cwd=source_root,
                env=environment,
            )
            source_bin = stage / "usr/bin"
            validate_versions(evidence, source_bin, "source-stage", environment)
            tiny_roundtrip(evidence, source_bin, root, "source-stage", environment)
            evidence.run(
                "stage-uninstall",
                ["make", "PREFIX=/usr", f"DESTDIR={stage}", "uninstall"],
                cwd=source_root,
                env=environment,
            )
            remaining_files = [str(path.relative_to(stage)) for path in stage.rglob("*") if path.is_file()]
            evidence.record("stage-uninstall-empty", remaining_files=remaining_files)
            if remaining_files:
                raise RuntimeError("make uninstall left staged files")

            expected_hashes = command_hashes(reference_bin)
            deb_bin = extract_deb(evidence, deb, root / "deb", environment)
            validate_hashes("deb", deb_bin, expected_hashes, evidence)
            validate_versions(evidence, deb_bin, "deb", environment)
            tiny_roundtrip(evidence, deb_bin, root, "deb", environment)

            rpm_root = root / "rpm"
            rpm_root.mkdir()
            rpm_bin = extract_rpm(evidence, rpm, rpm_root, environment)
            validate_hashes("rpm", rpm_bin, expected_hashes, evidence)
            validate_versions(evidence, rpm_bin, "rpm", environment)
            tiny_roundtrip(evidence, rpm_bin, root, "rpm", environment)

            validate_dsc(evidence, packages_dir, root / "dsc", environment)
            enforce_budget(root)
            status = "passed"
        except Exception as caught:  # retain structured evidence before failing
            error = str(caught)
            evidence.record("failure", error=error)
        finally:
            receipt = {
                "schema": "cix-third-party-validation-v1",
                "status": status,
                "error": error,
                "source_tar": str(source_tar),
                "deb": str(deb),
                "rpm": str(rpm),
                "reference_bin": str(reference_bin),
                "cargo": str(cargo),
                "cargo_net_offline": True,
                "cargo_build_jobs": args.jobs,
                "temporary_budget_bytes": TEMPORARY_CAP_BYTES,
                "events": evidence.events,
            }
            (work_parent / "third-party-validation.json").write_text(json.dumps(receipt, indent=2) + "\n")
    if error:
        raise SystemExit(error)
    print(f"third-party validation passed; evidence: {work_parent / 'third-party-validation.json'}")


if __name__ == "__main__":
    main()
