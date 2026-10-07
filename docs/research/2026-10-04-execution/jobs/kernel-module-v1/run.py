"""Leased build receipt for the experimental cix_squashfs external module."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

assert os.environ.get("CIX_RELEASE_LEASE") == "1"
root = Path(__file__).resolve().parents[5]
work = root / "benchmark-work/native-rc-check-v1"
job = Path(__file__).resolve().parent
overlay = root / "rust/cix-native/adapters/squashfs/kernel"
source = work / "kernel-source-v4"
source_receipt = root / "docs/research/2026-10-04-execution/jobs/kernel-source-v4/receipt.json"
headers = Path("/lib/modules/6.8.0-142-generic/build")
stage = work / "kernel-module-v1/stage"

if stage.exists():
    raise SystemExit(f"refusing non-fresh stage: {stage}")
if not (headers / "include/config/kernel.release").is_file():
    raise SystemExit("matching configured kernel headers are unavailable")

tracked = [
    overlay / "Kconfig", overlay / "Makefile", overlay / "README.md",
    *sorted((overlay / "include").glob("*")),
    *sorted((overlay / "scripts").glob("*.sh")),
    overlay / "cix_profile_portable.c", overlay / "cix_squashfs_decompressor.c",
    overlay / "cix_squashfs_fs_register.c",
    root / "rust/cix-native/adapters/squashfs/profile/src/cix_squashfs_profile.c",
    root / "rust/cix-native/adapters/squashfs/profile/include/cix_squashfs_profile.h",
]
hashes = {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
          for path in tracked if path.is_file()}
hashes["kernel-release"] = (headers / "include/config/kernel.release").read_text().strip()
hashes["kernel-source-receipt"] = hashlib.sha256(source_receipt.read_bytes()).hexdigest()
(job / "input-hashes.json").write_text(json.dumps(hashes, indent=2, sort_keys=True) + "\n")

environment = dict(os.environ)
environment.update({
    "CIX_LINUX_SRC": str(source),
    "CIX_KERNEL_BUILD": str(headers),
    "CIX_SQUASHFS_SOURCE_RECEIPT": str(source_receipt),
    "CIX_SQUASHFS_STAGE": str(stage),
    "CIX_EXPECTED_KERNEL_RELEASE": "6.8.0-142-generic",
})
prepare = subprocess.run([str(overlay / "scripts/build-overlay.sh")], env=environment,
                         text=True, capture_output=True)
build = None
if prepare.returncode == 0:
    build = subprocess.run(["make", "-C", str(headers), f"M={stage}",
                            "CONFIG_CIX_SQUASHFS=m", "modules", "-j4"],
                           env=environment, text=True, capture_output=True)
(job / "build-overlay.stdout.log").write_text(prepare.stdout)
(job / "build-overlay.stderr.log").write_text(prepare.stderr)
if build is not None:
    (job / "module-build.stdout.log").write_text(build.stdout)
    (job / "module-build.stderr.log").write_text(build.stderr)
module = stage / "cix_squashfs.ko"
receipt = {
    "prepare_returncode": prepare.returncode,
    "build_returncode": None if build is None else build.returncode,
    "stage": str(stage),
    "kernel_release": hashes["kernel-release"],
    "module": str(module),
    "module_sha256": hashlib.sha256(module.read_bytes()).hexdigest() if module.is_file() else None,
    "source_receipt": str(source_receipt),
    "input_hashes": str(job / "input-hashes.json"),
}
(job / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
raise SystemExit(prepare.returncode if build is None else build.returncode)
