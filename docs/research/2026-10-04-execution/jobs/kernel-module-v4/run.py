"""Leased build receipt for the public-manifest cix_squashfs external module."""
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
headers = Path("/lib/modules/6.8.0-142-generic/build")
stage = work / "kernel-module-v4/stage"
manifest = overlay / "upstream-linux-6.8.0-142.142-squashfs-manifest.json"
v3_inputs = json.loads((root / "docs/research/2026-10-04-execution/jobs/kernel-module-v3/input-hashes.json").read_text())

if stage.exists():
    raise SystemExit(f"refusing non-fresh stage: {stage}")
if not (headers / "include/config/kernel.release").is_file():
    raise SystemExit("matching configured kernel headers are unavailable")
if not manifest.is_file():
    raise SystemExit("bundled public source manifest is unavailable")

tracked = [
    overlay / "Kconfig", overlay / "Makefile", overlay / "README.md", manifest,
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
(job / "input-hashes.json").write_text(json.dumps(hashes, indent=2, sort_keys=True) + "\n")

profile_paths = [
    "rust/cix-native/adapters/squashfs/kernel/cix_profile_portable.c",
    "rust/cix-native/adapters/squashfs/kernel/cix_squashfs_decompressor.c",
    "rust/cix-native/adapters/squashfs/kernel/cix_squashfs_fs_register.c",
    "rust/cix-native/adapters/squashfs/kernel/Makefile",
    "rust/cix-native/adapters/squashfs/profile/src/cix_squashfs_profile.c",
    "rust/cix-native/adapters/squashfs/profile/include/cix_squashfs_profile.h",
]
profile_identity = {
    path: {"v3": v3_inputs.get(path), "v4": hashes.get(path),
           "unchanged": v3_inputs.get(path) == hashes.get(path)}
    for path in profile_paths
}
if not all(item["unchanged"] for item in profile_identity.values()):
    raise SystemExit("runtime source identity differs from VM-qualified module-v3")

# Deliberately omit CIX_SQUASHFS_SOURCE_RECEIPT: build-overlay must take its
# bundled public-manifest default.  This job performs no insmod/modprobe action.
environment = dict(os.environ)
environment.pop("CIX_SQUASHFS_SOURCE_RECEIPT", None)
environment.update({
    "CIX_LINUX_SRC": str(source),
    "CIX_KERNEL_BUILD": str(headers),
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
    "source_manifest": str(manifest),
    "source_manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
    "source_manifest_mode": "bundled-default; CIX_SQUASHFS_SOURCE_RECEIPT omitted",
    "profile_identity_against_module_v3": profile_identity,
    "host_module_load": False,
    "input_hashes": str(job / "input-hashes.json"),
}
(job / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
raise SystemExit(prepare.returncode if build is None else build.returncode)
