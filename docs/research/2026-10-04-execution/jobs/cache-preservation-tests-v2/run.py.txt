"""Lease-gated preservation of the reproducible shared Cargo debug cache.

This job is intentionally destructive only after it has created and reopened a
bounded deterministic archive. It never selects source, installed providers,
prefixes, receipts, archives, or release-LTO output.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import stat
import subprocess
import tarfile

# run.py is docs/research/2026-10-04-execution/jobs/<job>/run.py.
ROOT = Path(__file__).resolve().parents[5]
EXPECTED_ROOT = Path("/home/user/src/colour-index-compression")
WORK = ROOT / "benchmark-work/native-rc-check-v1"
TARGET = WORK / "target/debug"
PRESERVED = WORK / "preserved-debug-cache-v1"
ARCHIVE = PRESERVED / "target-debug.tar.gz"
MANIFEST = PRESERVED / "target-debug.manifest.json"
MANIFEST_MIRROR = Path(__file__).with_name("manifest.json")
RECEIPT = Path(__file__).with_name("receipt.json")
LIMIT = 4_000_000_000
BUILD_HEADROOM = 700 * 1024 * 1024
# The cap is an admission limit. Deletion is allowed only after the verified
# archive's actual retained-work footprint proves the required post-delete room.
ARCHIVE_CAP = 50 * 1024 * 1024
HEADROOM_METADATA_MARGIN = 1024 * 1024


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def allocated(path: Path) -> int:
    return path.stat().st_blocks * 512


def work_bytes() -> int:
    completed = subprocess.run(["du", "-sx", "-B1", str(WORK)], check=True,
                               text=True, capture_output=True).stdout.split()[0]
    return int(completed)


def tree_bytes(path: Path) -> int:
    completed = subprocess.run(["du", "-sx", "-B1", str(path)], check=True,
                               text=True, capture_output=True).stdout.split()[0]
    return int(completed)


def relative(path: Path) -> str:
    return path.relative_to(TARGET).as_posix()


def safe_relative_target(path: Path, target: str) -> None:
    if not target or Path(target).is_absolute():
        raise RuntimeError("absolute or empty symlink target is forbidden: " + relative(path))
    resolved = (path.parent / target).resolve(strict=False)
    try:
        resolved.relative_to(TARGET)
    except ValueError as error:
        raise RuntimeError("symlink escapes selected cache: " + relative(path)) from error


def assert_no_active_writer() -> None:
    lsof = shutil.which("lsof")
    if not lsof:
        raise RuntimeError("lsof is required to reject active target/debug writers")
    result = subprocess.run([lsof, "+D", str(TARGET)], text=True, capture_output=True)
    if result.returncode not in (0, 1):
        raise RuntimeError("cannot inspect active target/debug users: " + result.stderr.strip())
    if result.returncode == 0 and result.stdout.strip():
        raise RuntimeError("active target/debug user prevents preservation: " + result.stdout.splitlines()[0])


def collect_manifest() -> tuple[dict, dict[tuple[int, int], str]]:
    if not TARGET.is_dir() or TARGET.is_symlink() or TARGET.resolve() != TARGET:
        raise RuntimeError("selected cache must be the exact non-symlink target/debug directory")
    entries, selected_inodes, selected_occurrences = [], {}, {}
    for path in sorted(TARGET.rglob("*"), key=lambda item: item.as_posix()):
        entry = {"path": relative(path), "mode": stat.S_IMODE(path.lstat().st_mode)}
        if path.is_symlink():
            link = os.readlink(path)
            safe_relative_target(path, link)
            entry.update({"type": "symlink", "target": link})
        elif path.is_file():
            detail = path.stat()
            inode = (detail.st_dev, detail.st_ino)
            entry.update({"type": "file", "logical_bytes": detail.st_size,
                          "allocated_bytes": detail.st_blocks * 512,
                          "sha256": sha256(path), "device": detail.st_dev,
                          "inode": detail.st_ino, "link_count": detail.st_nlink})
            selected_inodes.setdefault(inode, entry["path"])
            selected_occurrences[inode] = selected_occurrences.get(inode, 0) + 1
        elif path.is_dir():
            entry.update({"type": "directory"})
        else:
            raise RuntimeError("unsupported selected cache entry: " + str(path))
        entries.append(entry)
    if not entries:
        raise RuntimeError("selected cache is unexpectedly empty")
    # Link count must be fully accounted for inside TARGET. A separate WORK
    # walk names any matching inode outside TARGET, so it cannot be masked by
    # comparing a whole-work count with st_nlink.
    outside = {inode: [] for inode in selected_inodes}
    for path in WORK.rglob("*"):
        if path.is_symlink() or not path.is_file():
            continue
        detail = path.stat()
        inode = (detail.st_dev, detail.st_ino)
        if inode in outside and not path.is_relative_to(TARGET):
            outside[inode].append(str(path))
    for entry in entries:
        if entry["type"] == "file":
            inode = (entry["device"], entry["inode"])
            if outside[inode]:
                raise RuntimeError("selected inode is linked elsewhere in work: " + entry["path"])
            if selected_occurrences[inode] != entry["link_count"]:
                raise RuntimeError("selected inode has an external hardlink: " + entry["path"])
    manifest = {"schema": "cix.preserved-debug-cache.v1", "selected_root": str(TARGET),
                "entries": entries, "selected_allocated_bytes": tree_bytes(TARGET),
                "archive_cap_bytes": ARCHIVE_CAP}
    return manifest, selected_inodes


def tar_info(name: str, entry: dict) -> tarfile.TarInfo:
    item = tarfile.TarInfo(name)
    item.mode = entry["mode"]
    item.uid = item.gid = 0
    item.uname = item.gname = ""
    item.mtime = 0
    return item


def write_archive(manifest: dict, links: dict[tuple[int, int], str]) -> None:
    old_limit = resource.getrlimit(resource.RLIMIT_FSIZE)
    if old_limit[1] != resource.RLIM_INFINITY and ARCHIVE_CAP > old_limit[1]:
        raise RuntimeError("archive cap exceeds the process file-size hard limit")
    temporary = ARCHIVE.with_suffix(".tar.gz.partial")
    if temporary.exists() or ARCHIVE.exists() or MANIFEST.exists():
        raise RuntimeError("preservation destination already exists")
    payload = (json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n").encode()
    try:
        resource.setrlimit(resource.RLIMIT_FSIZE, (ARCHIVE_CAP, old_limit[1]))
        MANIFEST.write_bytes(payload)
        with temporary.open("xb") as stream, gzip.GzipFile(filename="", mode="wb", fileobj=stream, mtime=0) as zipped:
            with tarfile.open(fileobj=zipped, mode="w", format=tarfile.GNU_FORMAT) as archive:
                info = tarfile.TarInfo("target-debug.manifest.json")
                info.size = len(payload); info.mode = 0o644; info.uid = info.gid = 0; info.mtime = 0
                archive.addfile(info, __import__("io").BytesIO(payload))
                for entry in manifest["entries"]:
                    path = TARGET / entry["path"]
                    info = tar_info("target/debug/" + entry["path"], entry)
                    if entry["type"] == "directory":
                        info.type = tarfile.DIRTYPE
                        archive.addfile(info)
                    elif entry["type"] == "symlink":
                        info.type = tarfile.SYMTYPE; info.linkname = entry["target"]
                        archive.addfile(info)
                    else:
                        inode = (entry["device"], entry["inode"])
                        first = links[inode]
                        if entry["path"] != first:
                            info.type = tarfile.LNKTYPE; info.linkname = "target/debug/" + first
                            archive.addfile(info)
                        else:
                            info.size = entry["logical_bytes"]
                            with path.open("rb") as body:
                                archive.addfile(info, body)
        if temporary.stat().st_size > ARCHIVE_CAP:
            raise RuntimeError("archive exceeds declared cap")
        os.replace(temporary, ARCHIVE)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    finally:
        resource.setrlimit(resource.RLIMIT_FSIZE, old_limit)


def verify_archive(manifest: dict) -> str:
    expected = ["target-debug.manifest.json"] + ["target/debug/" + row["path"] for row in manifest["entries"]]
    with tarfile.open(ARCHIVE, "r:gz") as archive:
        members = archive.getmembers()
        if [member.name for member in members] != expected:
            raise RuntimeError("archive member set or order differs from manifest")
        embedded = archive.extractfile(members[0])
        if embedded is None or embedded.read() != MANIFEST.read_bytes():
            raise RuntimeError("archive manifest differs from preserved manifest")
        for entry, member in zip(manifest["entries"], members[1:]):
            if stat.S_IMODE(member.mode) != entry["mode"]:
                raise RuntimeError("archive mode differs: " + entry["path"])
            if entry["type"] == "directory" and not member.isdir():
                raise RuntimeError("archive directory differs: " + entry["path"])
            if entry["type"] == "symlink" and (not member.issym() or member.linkname != entry["target"]):
                raise RuntimeError("archive symlink differs: " + entry["path"])
            if entry["type"] == "file":
                if member.islnk():
                    if member.linkname != "target/debug/" + next(row["path"] for row in manifest["entries"]
                                                               if row.get("device") == entry["device"] and row.get("inode") == entry["inode"]):
                        raise RuntimeError("archive hardlink differs: " + entry["path"])
                elif not member.isfile():
                    raise RuntimeError("archive regular file differs: " + entry["path"])
                body = archive.extractfile(member)
                if body is None or hashlib.sha256(body.read()).hexdigest() != entry["sha256"]:
                    raise RuntimeError("archive digest differs: " + entry["path"])
    return sha256(ARCHIVE)


def unchanged(manifest: dict) -> bool:
    current, _ = collect_manifest()
    return current == manifest


def write_receipt(value: dict) -> None:
    RECEIPT.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def main() -> None:
    receipt = {"status": "started", "selected_root": str(TARGET), "removed": False}
    write_failure_receipt = not RECEIPT.exists()
    try:
        if os.environ.get("CIX_RELEASE_LEASE") != "1":
            raise RuntimeError("root scheduler lease required")
        if ROOT != EXPECTED_ROOT or WORK.parent != ROOT / "benchmark-work" or TARGET != WORK / "target/debug":
            raise RuntimeError("unexpected repository or selected cache root")
        if PRESERVED.exists() or MANIFEST_MIRROR.exists() or RECEIPT.exists():
            raise RuntimeError("refuse to overwrite retained preservation evidence")
        if work_bytes() + ARCHIVE_CAP > LIMIT:
            raise RuntimeError("archive cap cannot be admitted within the shared temporary limit")
        assert_no_active_writer()
        manifest, links = collect_manifest()
        MANIFEST_MIRROR.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        receipt["manifest_mirror"] = str(MANIFEST_MIRROR)
        before = work_bytes()
        PRESERVED.mkdir(mode=0o700)
        write_archive(manifest, links)
        archive_sha = verify_archive(manifest)
        retained_with_preservation = work_bytes()
        expected_after_delete = retained_with_preservation - manifest["selected_allocated_bytes"]
        expected_headroom = LIMIT - expected_after_delete
        if expected_headroom < BUILD_HEADROOM + HEADROOM_METADATA_MARGIN:
            raise RuntimeError("verified archive and manifest leave insufficient post-delete build headroom")
        assert_no_active_writer()
        if not unchanged(manifest):
            raise RuntimeError("selected cache changed after archive verification")
        shutil.rmtree(TARGET)
        if TARGET.exists():
            raise RuntimeError("selected cache removal was incomplete")
        receipt["removed"] = True
        after = work_bytes()
        headroom = LIMIT - after
        receipt.update({"status": "pass", "archive": str(ARCHIVE), "manifest": str(MANIFEST),
                        "archive_sha256": archive_sha, "archive_bytes": ARCHIVE.stat().st_size,
                        "selected_allocated_bytes": manifest["selected_allocated_bytes"],
                        "retained_work_before_bytes": before,
                        "retained_work_with_preservation_bytes": retained_with_preservation,
                        "expected_headroom_before_delete_bytes": expected_headroom,
                        "retained_work_after_bytes": after, "headroom_after_bytes": headroom,
                        "required_build_headroom_bytes": BUILD_HEADROOM,
                        "headroom_metadata_margin_bytes": HEADROOM_METADATA_MARGIN,
                        "preserved": "source, receipts, installed providers/prefixes, archives, stage, source export, and release-LTO output untouched"})
        if headroom < BUILD_HEADROOM + HEADROOM_METADATA_MARGIN:
            raise RuntimeError("post-prune headroom is below the required build reservation and metadata margin")
    except Exception as error:
        receipt.update({"status": "failed", "error": str(error)})
        raise
    finally:
        # A prior receipt is immutable evidence. Every fresh attempt, including
        # failures before archive creation or deletion, leaves one failure receipt.
        if write_failure_receipt:
            write_receipt(receipt)


if __name__ == "__main__":
    main()
