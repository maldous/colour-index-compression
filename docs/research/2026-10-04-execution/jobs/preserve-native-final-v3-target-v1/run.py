"""Archive a completed v3 target before reclaiming it for the Sonar reservation.

This job is intentionally destructive only after it has created and reopened a
bounded deterministic archive. It never selects source, installed providers,
prefixes, receipts, archives, or release-LTO output.
"""
from __future__ import annotations

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
V3_WORK = WORK / "native-final-source-v3"
TARGET = V3_WORK / "target"
PRESERVED = V3_WORK / "preserved-target-v1"
ARCHIVE = PRESERVED / "target.tar.xz"
MANIFEST = PRESERVED / "target.manifest.json"
MANIFEST_MIRROR = Path(__file__).with_name("manifest.json")
RECEIPT = Path(__file__).with_name("receipt.json")
LIMIT = 4_000_000_000
SONAR_RESERVATION = 620_756_992
ARCHIVE_CAP = 90_000_000
MANIFEST_CAP = 4_000_000
HEADROOM_METADATA_MARGIN = 1024 * 1024
V3_JOB_RECEIPT = ROOT / "docs/research/2026-10-04-execution/jobs/native-final-source-v3/receipt.json"
V3_WORK_RECEIPT = V3_WORK / "receipt.json"
V3_RAW_RESULT = V3_JOB_RECEIPT.parent / "raw/result.json"
ALIAS_RECEIPT = ROOT / "docs/research/2026-10-04-execution/jobs/native-alias-filter-v1/receipt.json"
ALIAS_STDOUT = ALIAS_RECEIPT.with_name("stdout.log")
ALIAS_TEST = "cli::policy_tests::program_name_normalization_is_platform_specific"
RETAINED_BINARIES = {
    "release-lto/cix": "734653d644ddfed39638caa42f4d91b5bb29eb9ff0a3e2ce45aaecd664d37eca",
    "release-lto/cixcat": "4104d82878912303f2fe8e103b469ee09572fc2cef5c24be03ed319d3a4758c2",
    "release-lto/uncix": "dfa3e665f3ad1c3de39d551249ebca663235b7f3b0dbaee68e85c1a13f2823c5",
}
RETAINED_BINARY_BYTES = 12_839_336


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
        raise RuntimeError("lsof is required to reject active target writers")
    result = subprocess.run([lsof, "+D", str(TARGET)], text=True, capture_output=True)
    if result.returncode not in (0, 1):
        raise RuntimeError("cannot inspect active target users: " + result.stderr.strip())
    if result.returncode == 0 and result.stdout.strip():
        raise RuntimeError("active target user prevents preservation: " + result.stdout.splitlines()[0])


def identity(path: Path) -> dict[str, object]:
    return {"path": str(path), "sha256": sha256(path), "bytes": path.stat().st_size}


def terminal_quality_gates() -> dict[str, object]:
    required = ("copy-retained-lto-cache", "clippy", "release-lto-binaries",
                "test-cli-program-aliases", "test-cli_smoke",
                "test-full_engine_constraints", "test-zpaq_backend")
    evidence: dict[str, object] = {}
    for label, path, terminal in (("v3_job_receipt", V3_JOB_RECEIPT, True),
                                  ("v3_work_phase_receipt", V3_WORK_RECEIPT, False)):
        if not path.is_file():
            raise RuntimeError(label + " is absent")
        value = json.loads(path.read_text(encoding="utf-8"))
        phases = value.get("phases")
        if value.get("schema") != "cix-native-final-source-v3":
            raise RuntimeError(label + " has an unexpected v3 receipt schema")
        if terminal and value.get("status") != "pass":
            raise RuntimeError(label + " is not a terminal v3 pass")
        if not terminal and value.get("status") != "running":
            raise RuntimeError(label + " is not the expected in-work completed-phase receipt")
        if not isinstance(phases, dict) or any(phases.get(name, {}).get("returncode") != 0 for name in required):
            raise RuntimeError(label + " lacks a successful required phase")
        if terminal:
            receipt_binaries = value.get("release_lto_binaries")
            if not isinstance(receipt_binaries, dict) or any(
                receipt_binaries.get(Path(path).name, {}).get("sha256") != expected
                for path, expected in RETAINED_BINARIES.items()
            ):
                raise RuntimeError("v3 receipt does not bind the expected optimized binaries")
        evidence[label] = identity(path)
    if not V3_RAW_RESULT.is_file():
        raise RuntimeError("v3 outer raw result is absent")
    raw = json.loads(V3_RAW_RESULT.read_text(encoding="utf-8"))
    if raw.get("exit_code") != 0 or raw.get("child_status", {}).get("child_exit_code") != 0:
        raise RuntimeError("v3 outer raw result is not a terminal successful execution")
    evidence["v3_outer_raw_result"] = identity(V3_RAW_RESULT)
    if not ALIAS_RECEIPT.is_file() or not ALIAS_STDOUT.is_file():
        raise RuntimeError("alias-test receipt or stdout proof is absent")
    alias = json.loads(ALIAS_RECEIPT.read_text(encoding="utf-8"))
    stdout = ALIAS_STDOUT.read_text(encoding="utf-8")
    if alias.get("status") != "pass" or alias.get("exit_code") != 0 or alias.get("test") != ALIAS_TEST:
        raise RuntimeError("alias-test receipt is not an exact passing test")
    if "running 1 test" not in stdout or "test " + ALIAS_TEST + " ... ok" not in stdout or "1 passed; 0 failed" not in stdout:
        raise RuntimeError("alias-test stdout does not prove one exact passing test")
    evidence["alias_receipt"] = identity(ALIAS_RECEIPT)
    evidence["alias_stdout"] = identity(ALIAS_STDOUT)
    return evidence


def collect_manifest() -> tuple[dict, dict[tuple[int, int], str]]:
    if not TARGET.is_dir() or TARGET.is_symlink() or TARGET.resolve() != TARGET:
        raise RuntimeError("selected cache must be the exact non-symlink v3 target directory")
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
    manifest = {"schema": "cix.preserved-native-final-v3-target.v1", "selected_root": str(TARGET),
                "entries": entries, "selected_allocated_bytes": tree_bytes(TARGET),
                "archive_cap_bytes": ARCHIVE_CAP, "manifest_cap_bytes": MANIFEST_CAP,
                "separately_retained_binaries": sorted(RETAINED_BINARIES)}
    return manifest, selected_inodes


def tar_info(name: str, entry: dict) -> tarfile.TarInfo:
    item = tarfile.TarInfo(name)
    item.mode = entry["mode"]
    item.uid = item.gid = 0
    item.uname = item.gname = ""
    item.mtime = 0
    return item


def archived_entries(manifest: dict) -> list[dict]:
    return list(manifest["entries"])


def encoded_manifest(manifest: dict) -> bytes:
    payload = (json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n").encode()
    if len(payload) > MANIFEST_CAP:
        raise RuntimeError("full target manifest exceeds its declared cap")
    return payload


def write_archive(manifest: dict, links: dict[tuple[int, int], str]) -> None:
    old_limit = resource.getrlimit(resource.RLIMIT_FSIZE)
    if old_limit[1] != resource.RLIM_INFINITY and ARCHIVE_CAP > old_limit[1]:
        raise RuntimeError("archive cap exceeds the process file-size hard limit")
    temporary = ARCHIVE.with_name(ARCHIVE.name + ".partial")
    if temporary.exists() or ARCHIVE.exists() or MANIFEST.exists():
        raise RuntimeError("preservation destination already exists")
    payload = encoded_manifest(manifest)
    try:
        resource.setrlimit(resource.RLIMIT_FSIZE, (ARCHIVE_CAP, old_limit[1]))
        MANIFEST.write_bytes(payload)
        with tarfile.open(temporary, mode="w:xz", format=tarfile.GNU_FORMAT, preset=9) as archive:
                info = tarfile.TarInfo("target.manifest.json")
                info.size = len(payload); info.mode = 0o644; info.uid = info.gid = 0; info.mtime = 0
                archive.addfile(info, __import__("io").BytesIO(payload))
                for entry in archived_entries(manifest):
                    path = TARGET / entry["path"]
                    info = tar_info("target/" + entry["path"], entry)
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
                            info.type = tarfile.LNKTYPE; info.linkname = "target/" + first
                            archive.addfile(info)
                        else:
                            info.size = entry["logical_bytes"]
                            with path.open("rb") as body:
                                archive.addfile(info, body)
        if temporary.stat().st_size > ARCHIVE_CAP:
            raise RuntimeError("archive exceeds declared cap")
        os.replace(temporary, ARCHIVE)
    except Exception:
        # A partial XZ stream is retained as failure evidence. It cannot trigger
        # deletion because verification and the capacity gate occur afterward.
        raise
    finally:
        resource.setrlimit(resource.RLIMIT_FSIZE, old_limit)


def verify_archive(manifest: dict) -> str:
    expected = ["target.manifest.json"] + ["target/" + row["path"] for row in archived_entries(manifest)]
    with tarfile.open(ARCHIVE, "r:xz") as archive:
        members = archive.getmembers()
        if [member.name for member in members] != expected:
            raise RuntimeError("archive member set or order differs from manifest")
        embedded = archive.extractfile(members[0])
        if embedded is None or embedded.read() != MANIFEST.read_bytes():
            raise RuntimeError("archive manifest differs from preserved manifest")
        for entry, member in zip(archived_entries(manifest), members[1:]):
            if stat.S_IMODE(member.mode) != entry["mode"]:
                raise RuntimeError("archive mode differs: " + entry["path"])
            if entry["type"] == "directory" and not member.isdir():
                raise RuntimeError("archive directory differs: " + entry["path"])
            if entry["type"] == "symlink" and (not member.issym() or member.linkname != entry["target"]):
                raise RuntimeError("archive symlink differs: " + entry["path"])
            if entry["type"] == "file":
                if member.islnk():
                    if member.linkname != "target/" + next(row["path"] for row in archived_entries(manifest)
                                                               if row.get("device") == entry["device"] and row.get("inode") == entry["inode"]):
                        raise RuntimeError("archive hardlink differs: " + entry["path"])
                elif not member.isfile():
                    raise RuntimeError("archive regular file differs: " + entry["path"])
                body = archive.extractfile(member)
                if body is None or hashlib.sha256(body.read()).hexdigest() != entry["sha256"]:
                    raise RuntimeError("archive digest differs: " + entry["path"])
    return sha256(ARCHIVE)


def copy_and_verify_binaries(manifest: dict) -> dict[str, dict[str, object]]:
    entry_by_path = {entry["path"]: entry for entry in manifest["entries"]}
    preserved: dict[str, dict[str, object]] = {}
    for path, expected_sha in RETAINED_BINARIES.items():
        source = TARGET / path
        entry = entry_by_path.get(path)
        if entry is None or entry.get("type") != "file" or sha256(source) != expected_sha or entry.get("sha256") != expected_sha:
            raise RuntimeError("receipt-bound optimized binary is absent or changed: " + path)
        destination = PRESERVED / "binaries" / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        if sha256(destination) != expected_sha or stat.S_IMODE(destination.stat().st_mode) != entry["mode"]:
            raise RuntimeError("separate optimized binary preservation failed: " + path)
        preserved[path] = {"source_sha256": expected_sha, "bytes": source.stat().st_size,
                           "mode": entry["mode"], "preserved_path": str(destination),
                           "preserved_sha256": sha256(destination)}
    return preserved


def unchanged(manifest: dict) -> bool:
    current, _ = collect_manifest()
    return current == manifest


def write_receipt(value: dict) -> None:
    RECEIPT.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def main() -> None:
    receipt = {"status": "started", "selected_root": str(TARGET), "removed": False,
               "archive_candidate": str(ARCHIVE), "manifest_candidate": str(MANIFEST)}
    write_failure_receipt = not RECEIPT.exists()
    try:
        if os.environ.get("CIX_RELEASE_LEASE") != "1":
            raise RuntimeError("root scheduler lease required")
        if ROOT != EXPECTED_ROOT or WORK.parent != ROOT / "benchmark-work" or TARGET != V3_WORK / "target":
            raise RuntimeError("unexpected repository or selected cache root")
        if PRESERVED.exists() or MANIFEST_MIRROR.exists() or RECEIPT.exists():
            raise RuntimeError("refuse to overwrite retained preservation evidence")
        quality_gate_identities = terminal_quality_gates()
        if work_bytes() + ARCHIVE_CAP + RETAINED_BINARY_BYTES + MANIFEST_CAP + HEADROOM_METADATA_MARGIN >= LIMIT:
            raise RuntimeError("archive cap cannot be admitted within the shared temporary limit")
        assert_no_active_writer()
        manifest, links = collect_manifest()
        MANIFEST_MIRROR.write_bytes(encoded_manifest(manifest))
        receipt["manifest_mirror"] = str(MANIFEST_MIRROR)
        before = work_bytes()
        PRESERVED.mkdir(mode=0o700)
        binaries = copy_and_verify_binaries(manifest)
        write_archive(manifest, links)
        archive_sha = verify_archive(manifest)
        retained_with_preservation = work_bytes()
        expected_after_delete = retained_with_preservation - manifest["selected_allocated_bytes"]
        expected_headroom = LIMIT - expected_after_delete
        if expected_after_delete + SONAR_RESERVATION + HEADROOM_METADATA_MARGIN >= LIMIT:
            raise RuntimeError("verified XZ archive, manifest, and binaries leave insufficient Sonar capacity")
        assert_no_active_writer()
        if not unchanged(manifest):
            raise RuntimeError("selected cache changed after archive verification")
        for binary in binaries.values():
            if sha256(Path(binary["preserved_path"])) != binary["preserved_sha256"]:
                raise RuntimeError("separately preserved optimized binary changed before deletion")
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
                        "required_sonar_reservation_bytes": SONAR_RESERVATION,
                        "headroom_metadata_margin_bytes": HEADROOM_METADATA_MARGIN,
                        "quality_gate_identities": quality_gate_identities,
                        "separately_preserved_binaries": binaries,
                        "preserved": "v3 source, logs, receipts, test results, and three optimized binaries retained"})
        if after + SONAR_RESERVATION + HEADROOM_METADATA_MARGIN >= LIMIT:
            raise RuntimeError("post-prune retained work does not leave the required Sonar capacity")
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
