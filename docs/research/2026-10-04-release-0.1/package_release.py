#!/usr/bin/env python3
"""Private, opt-in CIX 0.1 artifact packager.

The script deliberately defaults to a plan. Pass --execute only after a
qualified final binary directory and a clean source export have been selected.
It never installs a package on the host.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import stat
import subprocess
import tarfile
import tempfile
import time
from typing import Iterable


COMMANDS = ("cix", "uncix", "cixcat")
LEGAL_FILES = ("README.md", "LICENSE", "THIRD_PARTY_NOTICES.txt")
MANPAGES = ("man/cix.1", "man/uncix.1", "man/cixcat.1")
TEMPORARY_CAP_BYTES = 4_000_000_000
SOURCE_ARCHIVE_CAP_BYTES = 1_000_000
EXCLUDED_PARTS = {
    ".git",
    ".private",
    ".github",
    "benchmark-work",
    "benchmarks",
    "dist",
    "docs/research",
    "examples",
    "figures",
    "raw",
    "results",
    "stage",
    "target",
}
EXCLUDED_SUFFIXES = (".bin", ".cix", ".restored", ".tmp")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--binary-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--work-dir",
        type=Path,
        help="existing scheduler-owned directory for all temporary package work; required with --execute",
    )
    parser.add_argument("--version", default="0.1.0")
    parser.add_argument(
        "--targets",
        default="source,binary-tar,dsc,deb,rpm",
        help="comma-separated: source,binary-tar,dsc,deb,rpm",
    )
    parser.add_argument(
        "--source-date-epoch",
        type=int,
        default=int(os.environ.get("SOURCE_DATE_EPOCH", "0")) or int(time.time()),
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="create artifacts; omitted by default so the invocation is a plan",
    )
    return parser.parse_args()


def checked_directory(path: Path, label: str) -> Path:
    resolved = path.resolve()
    if not resolved.is_dir():
        raise SystemExit(f"{label} is not a directory: {resolved}")
    return resolved


def checked_binary_directory(path: Path) -> Path:
    resolved = checked_directory(path, "binary directory")
    missing = [name for name in COMMANDS if not (resolved / name).is_file()]
    if missing:
        raise SystemExit(f"binary directory is missing: {', '.join(missing)}")
    return resolved


def selected_targets(value: str) -> set[str]:
    selected = {item.strip() for item in value.split(",") if item.strip()}
    valid = {"source", "binary-tar", "dsc", "deb", "rpm"}
    unknown = selected - valid
    if unknown or not selected:
        raise SystemExit(f"invalid targets: {', '.join(sorted(unknown)) or value}")
    if "dsc" in selected or "deb" in selected or "rpm" in selected:
        selected.add("source")
    return selected


def excluded(relative: Path, extra_exclusions: set[str] | None = None) -> bool:
    text = relative.as_posix()
    excluded_parts = EXCLUDED_PARTS | (extra_exclusions or set())
    if any(text == part or text.startswith(f"{part}/") for part in excluded_parts):
        return True
    return relative.suffix in EXCLUDED_SUFFIXES


def source_members(source_dir: Path, extra_exclusions: set[str] | None = None) -> list[Path]:
    members: list[Path] = []
    for path in source_dir.rglob("*"):
        relative = path.relative_to(source_dir)
        if excluded(relative, extra_exclusions):
            continue
        if path.is_symlink():
            raise SystemExit(f"source export must not contain symlinks: {relative}")
        if path.is_file():
            members.append(path)
    return sorted(members, key=lambda item: item.relative_to(source_dir).as_posix())


def normalized_info(path: Path, archive_name: str, epoch: int) -> tarfile.TarInfo:
    source_stat = path.stat()
    info = tarfile.TarInfo(archive_name)
    info.size = source_stat.st_size
    info.mode = stat.S_IMODE(source_stat.st_mode)
    info.mtime = epoch
    info.uid = 0
    info.gid = 0
    info.uname = "root"
    info.gname = "root"
    return info


def write_tar_gz(destination: Path, entries: Iterable[tuple[Path, str]], epoch: int) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=epoch) as compressed:
            with tarfile.open(mode="w", fileobj=compressed, format=tarfile.PAX_FORMAT) as archive:
                for source, name in entries:
                    info = normalized_info(source, name, epoch)
                    with source.open("rb") as handle:
                        archive.addfile(info, handle)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tree_size(path: Path) -> int:
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def ensure_temporary_budget(path: Path) -> None:
    size = tree_size(path)
    if size > TEMPORARY_CAP_BYTES:
        raise SystemExit(f"temporary package work exceeds 4 GB: {path} ({size} bytes)")


def run(command: list[str], *, cwd: Path | None = None) -> str:
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=os.environ.copy(),
        )
    except subprocess.CalledProcessError as error:
        rendered = " ".join(command)
        details = error.stderr.strip() or error.stdout.strip() or "no diagnostic output"
        raise SystemExit(f"command failed ({error.returncode}): {rendered}\n{details}") from error
    return result.stdout


def source_tarball(
    source_dir: Path,
    output_dir: Path,
    version: str,
    epoch: int,
    *,
    destination: Path | None = None,
    extra_exclusions: set[str] | None = None,
) -> Path:
    prefix = f"cix-{version}"
    archive_path = destination or output_dir / f"{prefix}.tar.gz"
    entries = [
        (path, f"{prefix}/{path.relative_to(source_dir).as_posix()}")
        for path in source_members(source_dir, extra_exclusions)
    ]
    write_tar_gz(archive_path, entries, epoch)
    if archive_path.stat().st_size > SOURCE_ARCHIVE_CAP_BYTES:
        raise SystemExit(f"source archive exceeds 1 MB limit: {archive_path}")
    return archive_path


def binary_manifest(binary_dir: Path) -> dict[str, object]:
    dependencies: dict[str, str] = {}
    if platform.system() == "Linux" and shutil.which("ldd"):
        for name in COMMANDS:
            dependencies[name] = run(["ldd", str(binary_dir / name)]).strip()
    return {
        "schema": "cix-binary-artifact-v1",
        "platform": platform.platform(),
        "dynamic_dependency_policy": "system libraries; inspect per-binary ldd output",
        "dynamic_dependencies": dependencies,
        "binaries": {
            name: {"sha256": sha256(binary_dir / name), "bytes": (binary_dir / name).stat().st_size}
            for name in COMMANDS
        },
    }


def binary_tarball(
    source_dir: Path,
    binary_dir: Path,
    output_dir: Path,
    version: str,
    epoch: int,
) -> Path:
    prefix = f"cix-{version}-{platform.system().lower()}-{platform.machine().lower()}"
    manifest_path = output_dir / ".binary-artifact.json"
    manifest_path.write_text(json.dumps(binary_manifest(binary_dir), indent=2) + "\n")
    try:
        entries = [(binary_dir / name, f"{prefix}/bin/{name}") for name in COMMANDS]
        entries.extend((source_dir / name, f"{prefix}/{name}") for name in LEGAL_FILES)
        entries.extend((source_dir / name, f"{prefix}/{name}") for name in MANPAGES)
        entries.append((manifest_path, f"{prefix}/artifact.json"))
        destination = output_dir / f"{prefix}.tar.gz"
        write_tar_gz(destination, entries, epoch)
        return destination
    finally:
        manifest_path.unlink(missing_ok=True)


def debian_dependencies(binary_dir: Path, project: Path) -> str:
    tool = shutil.which("dpkg-shlibdeps")
    if tool is None:
        raise SystemExit("dpkg-shlibdeps is required to derive Debian runtime dependencies")
    fields: set[str] = set()
    for name in COMMANDS:
        output = run([tool, "-O", "-e", str(binary_dir / name)], cwd=project)
        for line in output.splitlines():
            if line.startswith("shlibs:Depends="):
                fields.update(part.strip() for part in line.partition("=")[2].split(",") if part.strip())
    return ", ".join(sorted(fields))


def debian_shlibdeps_control(version: str) -> str:
    return "\n".join(
        [
            "Source: cix",
            "Section: utils",
            "Priority: optional",
            "Maintainer: maldous <matthew.aldous@gmail.com>",
            "Standards-Version: 4.7.0",
            "",
            "Package: cix",
            "Architecture: any",
            "Description: lossless command-line compressor",
            " CIX creates and restores lossless, self-describing CIX archives.",
            "",
        ]
    )


def build_deb(
    source_dir: Path,
    binary_dir: Path,
    output_dir: Path,
    version: str,
    work_dir: Path,
) -> Path:
    tool = shutil.which("dpkg-deb")
    architecture_tool = shutil.which("dpkg")
    if tool is None or architecture_tool is None:
        raise SystemExit("dpkg-deb and dpkg are required for a Debian package")
    architecture = run([architecture_tool, "--print-architecture"]).strip()
    with tempfile.TemporaryDirectory(prefix="cix-deb-", dir=work_dir) as temporary:
        project = Path(temporary) / "project"
        stage = project / "stage"
        control = stage / "DEBIAN"
        binary_path = stage / "usr/bin"
        man_path = stage / "usr/share/man/man1"
        doc_path = stage / "usr/share/doc/cix"
        (project / "debian").mkdir(parents=True)
        (project / "debian/control").write_text(debian_shlibdeps_control(version))
        control.mkdir(parents=True)
        binary_path.mkdir(parents=True)
        man_path.mkdir(parents=True)
        doc_path.mkdir(parents=True)
        for name in COMMANDS:
            shutil.copy2(binary_dir / name, binary_path / name)
        dependencies = debian_dependencies(binary_path, project)
        if not dependencies:
            raise SystemExit("dpkg-shlibdeps did not report runtime dependencies")
        for name in MANPAGES:
            shutil.copy2(source_dir / name, man_path / Path(name).name)
        for name in LEGAL_FILES:
            shutil.copy2(source_dir / name, doc_path / name)
        (control / "control").write_text(
            "\n".join(
                [
                    "Package: cix",
                    f"Version: {version}-1",
                    "Section: utils",
                    "Priority: optional",
                    f"Architecture: {architecture}",
                    "Maintainer: maldous <matthew.aldous@gmail.com>",
                    f"Depends: {dependencies}",
                    "Description: lossless command-line compressor",
                    " CIX creates and restores lossless, self-describing CIX archives.",
                    "",
                ]
            )
        )
        ensure_temporary_budget(Path(temporary))
        destination = output_dir / f"cix_{version}-1_{architecture}.deb"
        run([tool, "--root-owner-group", "--build", str(stage), str(destination)])
    return destination


def build_dsc(
    source_dir: Path,
    output_dir: Path,
    version: str,
    epoch: int,
    work_dir: Path,
) -> list[Path]:
    tool = shutil.which("dpkg-source")
    if tool is None:
        raise SystemExit("dpkg-source is required for a Debian source package")
    with tempfile.TemporaryDirectory(prefix="cix-dsc-", dir=work_dir) as temporary:
        parent = Path(temporary)
        # Debian's upstream orig archive must not already contain a competing
        # packaging/debian tree. The generated source tree adds it at debian/.
        orig = source_tarball(
            source_dir,
            parent,
            version,
            epoch,
            destination=parent / f"cix_{version}.orig.tar.gz",
            extra_exclusions={"packaging/debian"},
        )
        unpacked = parent / f"cix-{version}"
        for member in source_members(source_dir, {"packaging/debian"}):
            destination = unpacked / member.relative_to(source_dir)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(member, destination)
        shutil.copytree(source_dir / "packaging/debian", unpacked / "debian")
        ensure_temporary_budget(parent)
        run([tool, "-b", "."], cwd=unpacked)
        artifacts = [orig, *sorted(parent.glob(f"cix_{version}-1.*"))]
        copied: list[Path] = []
        for artifact in artifacts:
            if not artifact.is_file():
                continue
            destination = output_dir / artifact.name
            shutil.copy2(artifact, destination)
            copied.append(destination)
        if not any(artifact.suffix == ".dsc" for artifact in copied):
            raise SystemExit("dpkg-source completed without a .dsc file")
        return copied


def build_binary_rpm(
    source_dir: Path,
    binary_dir: Path,
    output_dir: Path,
    version: str,
    work_dir: Path,
) -> list[Path]:
    tool = shutil.which("rpmbuild")
    if tool is None:
        raise SystemExit("rpmbuild is required for an RPM build")
    with tempfile.TemporaryDirectory(prefix="cix-rpm-", dir=work_dir) as temporary:
        topdir = Path(temporary) / "rpmbuild"
        for directory in ("BUILD", "BUILDROOT", "RPMS", "SOURCES", "SPECS", "SRPMS"):
            (topdir / directory).mkdir(parents=True)
        staged = topdir / "SOURCES/cix-binary"
        staged.mkdir()
        for name in COMMANDS:
            shutil.copy2(binary_dir / name, staged / name)
        for name in LEGAL_FILES:
            shutil.copy2(source_dir / name, staged / name)
        for name in MANPAGES:
            shutil.copy2(source_dir / name, staged / Path(name).name)
        spec = topdir / "SPECS/cix-binary.spec"
        spec.write_text(
            "\n".join(
                [
                    "Name:           cix",
                    f"Version:        {version}",
                    "Release:        1%{?dist}",
                    "Summary:        Lossless command-line compressor",
                    "License:        MIT AND Apache-2.0",
                    "%global __strip /bin/true",
                    "%global debug_package %{nil}",
                    "AutoReqProv:    yes",
                    "",
                    "%description",
                    "CIX creates and restores lossless, self-describing CIX archives.",
                    "",
                    "%prep",
                    ":",
                    "",
                    "%build",
                    ":",
                    "",
                    "%install",
                    "install -Dpm 0755 %{_sourcedir}/cix-binary/cix %{buildroot}%{_bindir}/cix",
                    "install -Dpm 0755 %{_sourcedir}/cix-binary/uncix %{buildroot}%{_bindir}/uncix",
                    "install -Dpm 0755 %{_sourcedir}/cix-binary/cixcat %{buildroot}%{_bindir}/cixcat",
                    "install -Dpm 0644 %{_sourcedir}/cix-binary/cix.1 %{buildroot}%{_mandir}/man1/cix.1",
                    "install -Dpm 0644 %{_sourcedir}/cix-binary/uncix.1 %{buildroot}%{_mandir}/man1/uncix.1",
                    "install -Dpm 0644 %{_sourcedir}/cix-binary/cixcat.1 %{buildroot}%{_mandir}/man1/cixcat.1",
                    "install -Dpm 0644 %{_sourcedir}/cix-binary/LICENSE %{buildroot}%{_defaultdocdir}/%{name}/LICENSE",
                    "install -Dpm 0644 %{_sourcedir}/cix-binary/THIRD_PARTY_NOTICES.txt %{buildroot}%{_defaultdocdir}/%{name}/THIRD_PARTY_NOTICES.txt",
                    "install -Dpm 0644 %{_sourcedir}/cix-binary/README.md %{buildroot}%{_defaultdocdir}/%{name}/README.md",
                    "",
                    "%files",
                    "%{_bindir}/cix",
                    "%{_bindir}/uncix",
                    "%{_bindir}/cixcat",
                    "%{_mandir}/man1/cix.1*",
                    "%{_mandir}/man1/uncix.1*",
                    "%{_mandir}/man1/cixcat.1*",
                    "%license %{_defaultdocdir}/%{name}/LICENSE",
                    "%doc %{_defaultdocdir}/%{name}/THIRD_PARTY_NOTICES.txt",
                    "%doc %{_defaultdocdir}/%{name}/README.md",
                    "",
                ]
            )
        )
        ensure_temporary_budget(Path(temporary))
        run([tool, "-bb", "--define", f"_topdir {topdir}", str(spec)])
        artifacts = sorted((topdir / "RPMS").rglob("*.rpm"))
        if not artifacts:
            raise SystemExit("rpmbuild completed without a binary RPM")
        copied: list[Path] = []
        rpm_query = shutil.which("rpm")
        dependency_lines: list[str] = []
        for artifact in artifacts:
            destination = output_dir / artifact.name
            shutil.copy2(artifact, destination)
            copied.append(destination)
            with tempfile.TemporaryDirectory(prefix="cix-rpm-verify-", dir=work_dir) as extracted:
                rpm2cpio = shutil.which("rpm2cpio")
                cpio = shutil.which("cpio")
                if rpm2cpio is None or cpio is None:
                    raise SystemExit("rpm2cpio and cpio are required to verify binary RPM payload hashes")
                extraction = subprocess.run(
                    [rpm2cpio, str(artifact)],
                    check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=os.environ.copy()
                )
                subprocess.run(
                    [cpio, "-idm", "--quiet"], cwd=extracted, input=extraction.stdout,
                    check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=os.environ.copy()
                )
                for name in COMMANDS:
                    packaged = Path(extracted) / "usr/bin" / name
                    if not packaged.is_file() or sha256(packaged) != sha256(binary_dir / name):
                        raise SystemExit(f"RPM payload changed selected binary: {name}")
                ensure_temporary_budget(Path(extracted))
            if rpm_query:
                dependency_lines.append(f"{artifact.name}:")
                dependency_lines.extend(run([rpm_query, "-qpR", str(artifact)]).splitlines())
        receipt = output_dir / "RPM-BUILD-HOST.txt"
        receipt.write_text(
            "This binary RPM stages and payload-verifies the selected cix, uncix, and cixcat files; it does not run Cargo.\n"
            "Automatic RPM dependencies were generated on the invoking build host. They are not evidence "
            "of Fedora or RHEL runtime compatibility until this artifact is built and tested in that target environment.\n\n"
            + ("\n".join(dependency_lines) + "\n" if dependency_lines else "rpm -qpR unavailable on build host.\n")
        )
        copied.append(receipt)
        return copied


def plan(args: argparse.Namespace, targets: set[str]) -> None:
    print("CIX private packaging plan")
    print(f"  source: {args.source_dir.resolve()}")
    print(f"  binaries: {args.binary_dir.resolve()}")
    print(f"  output: {args.output_dir.resolve()}")
    print(f"  work: {args.work_dir.resolve() if args.work_dir else '(required with --execute)'}")
    print(f"  version: {args.version}")
    print(f"  targets: {', '.join(sorted(targets))}")
    print("  source tar: excludes private evidence/raw research and retains tests/")
    print("  binary tar: includes selected binaries, manuals, legal files, and dependency receipt")
    print("  dsc: generated from a temporary conventional debian/ layout")
    print("  deb: staged and built with dpkg-deb; never installed")
    print("  rpm: stages selected binaries with rpmbuild; target-runtime compatibility remains unqualified")


def main() -> None:
    args = parse_args()
    source_dir = checked_directory(args.source_dir, "source directory")
    binary_dir = checked_binary_directory(args.binary_dir)
    output_dir = args.output_dir.resolve()
    if output_dir.is_relative_to(source_dir):
        raise SystemExit("output directory must be outside the source directory")
    targets = selected_targets(args.targets)
    plan(args, targets)
    if not args.execute:
        return
    if args.work_dir is None:
        raise SystemExit("--work-dir is required with --execute")
    work_dir = checked_directory(args.work_dir, "work directory")
    if output_dir.is_relative_to(work_dir):
        raise SystemExit("output directory must be outside the temporary work directory")
    if shutil.disk_usage(work_dir).free < TEMPORARY_CAP_BYTES:
        raise SystemExit("work directory needs at least 4 GB free for the bounded temporary package budget")
    os.environ["TMPDIR"] = str(work_dir)
    tempfile.tempdir = str(work_dir)
    os.environ["SOURCE_DATE_EPOCH"] = str(args.source_date_epoch)
    output_dir.mkdir(parents=True, exist_ok=True)
    source_tar = source_tarball(source_dir, output_dir, args.version, args.source_date_epoch)
    artifacts: list[Path] = [source_tar]
    if "binary-tar" in targets:
        artifacts.append(binary_tarball(source_dir, binary_dir, output_dir, args.version, args.source_date_epoch))
    if "dsc" in targets:
        artifacts.extend(build_dsc(source_dir, output_dir, args.version, args.source_date_epoch, work_dir))
    if "deb" in targets:
        artifacts.append(build_deb(source_dir, binary_dir, output_dir, args.version, work_dir))
    if "rpm" in targets:
        artifacts.extend(build_binary_rpm(source_dir, binary_dir, output_dir, args.version, work_dir))
    receipt = {
        "schema": "cix-package-receipt-v1",
        "source": str(source_dir),
        "binary_dir": str(binary_dir),
        "temporary_budget_bytes": TEMPORARY_CAP_BYTES,
        "artifacts": [
            {"path": artifact.name, "sha256": sha256(artifact), "bytes": artifact.stat().st_size}
            for artifact in artifacts
            if artifact.is_file()
        ],
    }
    (output_dir / "package-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
