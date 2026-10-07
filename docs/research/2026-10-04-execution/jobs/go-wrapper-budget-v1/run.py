"""Source-bound installed-SDK qualification for the Go wrapper allocation cap."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess


def sha256(path: Path) -> str:
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def tree_bytes(path: Path) -> int:
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


assert os.environ.get("CIX_RELEASE_LEASE") == "1"
job = Path(__file__).resolve().parent
root = job.parents[4]
manifest = json.loads((job / "source.json").read_text())
workspace = root / "benchmark-work/native-rc-check-v1"
snapshot = Path(os.environ.get(
    "CIX_GO_WRAPPER_SNAPSHOT", workspace / "execution-go-wrapper-budget-v1"
))
binding = snapshot / "bindings/go"
sdk = root / manifest["sdk"]
out = workspace / "go-wrapper-budget-v1"
out.mkdir(exist_ok=False)

receipt = {
    "source_snapshot": str(snapshot),
    "sdk": str(sdk),
    "source_hashes": {},
    "sdk_hashes": {},
    "commands": [],
    "cache": {},
}


def save() -> None:
    (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")


def verify(base: Path, expected: dict[str, str], destination: str) -> None:
    observed = {}
    for relative, wanted in expected.items():
        path = base / relative
        assert path.is_file(), f"missing frozen input: {path}"
        actual = sha256(path)
        assert actual == wanted, f"source closure changed: {path}"
        observed[relative] = actual
    receipt[destination] = observed


def run(label: str, command: list[str], env: dict[str, str]) -> None:
    result = subprocess.run(command, cwd=binding, env=env, capture_output=True,
                            timeout=manifest["limits"]["timeout_seconds"])
    (out / f"{label}.stdout.log").write_bytes(result.stdout)
    (out / f"{label}.stderr.log").write_bytes(result.stderr)
    receipt["commands"].append({
        "label": label,
        "argv": command,
        "returncode": result.returncode,
        "cwd": str(binding),
    })
    save()
    if result.returncode:
        raise RuntimeError(f"{label} failed; inspect the bounded job logs")


verify(snapshot, manifest["binding_files"], "source_hashes")
verify(sdk, manifest["sdk_files"], "sdk_hashes")
cache = out / "go-cache"
temporary = out / "go-tmp"
module_cache = out / "go-mod-cache"
for path in (cache, temporary, module_cache):
    path.mkdir()
env = os.environ.copy()
env.update({
    "CGO_ENABLED": "1",
    "GOCACHE": str(cache),
    "GOMODCACHE": str(module_cache),
    "GOTMPDIR": str(temporary),
    "GOTOOLCHAIN": "local",
    "GOFLAGS": "-mod=readonly",
    "GOPROXY": "off",
    "GOSUMDB": "off",
    "LC_ALL": "C",
    "GOMAXPROCS": str(manifest["limits"]["parallel_packages"]),
    "PKG_CONFIG_PATH": str(sdk / "lib/pkgconfig"),
    "LD_LIBRARY_PATH": str(sdk / "lib"),
})

try:
    run("go-version", ["/usr/bin/go", "version"], env)
    run("pkg-config", ["pkg-config", "--modversion", "cix-native"], env)
    run("go-wrapper-contract", ["/usr/bin/go", "test", "-v", "-count=1", "-p=2", "./..."], env)
finally:
    receipt["cache"] = {
        "go_cache_bytes_before_cleanup": tree_bytes(cache),
        "go_tmp_bytes_before_cleanup": tree_bytes(temporary),
        "go_mod_cache_bytes_before_cleanup": tree_bytes(module_cache),
    }
    total = sum(receipt["cache"].values())
    receipt["cache"]["total_bytes_before_cleanup"] = total
    receipt["cache"]["post_run_cap_bytes"] = manifest["limits"]["post_run_cache_bytes"]
    if total > manifest["limits"]["post_run_cache_bytes"]:
        save()
        raise RuntimeError("Go compiler cache exceeded the qualified post-run cap")
    for path in (cache, temporary, module_cache):
        shutil.rmtree(path)
    receipt["cache"]["cleaned"] = True
    save()
