"""Lease-dispatched qualification for the private profile alignment-probe cleanup."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

# The root dispatcher supplies this lease marker; the job specification must never forge it.
if os.environ.get("CIX_RELEASE_LEASE") != "1":
    raise RuntimeError("root scheduler lease required")

ROOT = Path(__file__).resolve().parents[5]
WORK = ROOT / "benchmark-work/native-rc-check-v1"
OUT = WORK / "squashfs-profile-alignment-v1"
BEFORE = WORK / "squashfs-profile-source-v2/profile"
AFTER = ROOT / "rust/cix-native/adapters/squashfs/profile"
OLD_SOURCE_SHA256 = "192e40b06d410cb689b581d5f8fc8128d83b8fdd0e5f16cba981f189756ac080"
NEW_SOURCE_SHA256 = "597a97bcd3ed91b0d1cfa2bd26cf48a70fe1f3b15ed14b65655f4abebf04e663"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_digests(root: Path) -> dict[str, str]:
    return {path.relative_to(root).as_posix(): digest(path)
            for path in sorted(root.rglob("*")) if path.is_file()}


def tool_identity(name: str) -> dict[str, str]:
    resolved = Path(shutil.which(name) or "").resolve()
    if not resolved.is_file():
        raise RuntimeError("required tool is absent: " + name)
    return {"path": str(resolved), "sha256": digest(resolved)}


def normalise_objdump_preamble(body: str, object_path: Path) -> str:
    """Compare only after replacing objdump's known input-path preamble."""
    # GNU objdump emits an empty first line before its file-format heading.
    leading = "\n" if body.startswith("\n") else ""
    preamble, separator, remainder = body[len(leading):].partition("\n")
    expected = str(object_path) + ":"
    if not separator or not preamble.startswith(expected):
        raise RuntimeError("objdump output lacks the expected object-path preamble")
    return leading + "<object>:" + preamble[len(expected):] + separator + remainder


def main() -> None:
    if OUT.exists():
        raise RuntimeError("refusing to overwrite an alignment qualification attempt")
    tracked = {
        "before_source": BEFORE / "src/cix_squashfs_profile.c",
        "before_header": BEFORE / "include/cix_squashfs_profile.h",
        "after_source": AFTER / "src/cix_squashfs_profile.c",
        "after_header": AFTER / "include/cix_squashfs_profile.h",
        "after_contract": AFTER / "tests/profile_contract.c",
        "native_differential": AFTER / "tests/native_differential.rs",
        "portable_cargo": WORK / "portable-source-v1/cix-portable/Cargo.toml",
    }
    hashes = {name: digest(path) for name, path in tracked.items()}
    hashes["portable_crate"] = tree_digests(WORK / "portable-source-v1/cix-portable")
    hashes["tools"] = {name: tool_identity(name) for name in ("cc", "objdump", "ar", "cargo")}
    if hashes["before_source"] != OLD_SOURCE_SHA256 or hashes["after_source"] != NEW_SOURCE_SHA256:
        raise RuntimeError("profile source identity differs from the declared alignment cleanup scope")
    OUT.mkdir()
    rows = []

    def run(argv, *, cwd=None, env=None):
        completed = subprocess.run([str(item) for item in argv], cwd=cwd or OUT,
                                   env={**os.environ, **(env or {})}, text=True,
                                   capture_output=True, timeout=180)
        rows.append({"argv": [str(item) for item in argv], "cwd": str(cwd or OUT),
                     "env_extra": env or {}, "returncode": completed.returncode,
                     "stdout": completed.stdout, "stderr": completed.stderr})
        (OUT / "receipt.json").write_text(json.dumps({"status": "running", "source_sha256": hashes,
            "commands": rows}, indent=2) + "\n")
        if completed.returncode:
            raise RuntimeError(completed.stderr[-6000:] or completed.stdout[-6000:])

    try:
        common = ["cc", "-std=c11", "-O2", "-fno-ident", "-Wall", "-Wextra", "-Werror"]
        before_object = OUT / "before.o"
        after_object = OUT / "after.o"
        run([*common, "-I" + str(BEFORE / "include"), "-c", BEFORE / "src/cix_squashfs_profile.c",
             "-o", before_object])
        run([*common, "-I" + str(AFTER / "include"), "-c", AFTER / "src/cix_squashfs_profile.c",
             "-o", after_object])
        run(["cmp", "-s", before_object, after_object])
        run(["objdump", "-dr", "--no-addresses", before_object])
        before_disassembly = normalise_objdump_preamble(rows[-1]["stdout"], before_object)
        run(["objdump", "-dr", "--no-addresses", after_object])
        if before_disassembly != normalise_objdump_preamble(rows[-1]["stdout"], after_object):
            raise RuntimeError("optimized object disassembly differs despite required byte equality")
        run([*common, "-I" + str(AFTER / "include"), AFTER / "src/cix_squashfs_profile.c",
             AFTER / "tests/profile_contract.c", "-o", OUT / "profile-contract"])
        run([OUT / "profile-contract"])
        run(["ar", "rcs", OUT / "libcix_squashfs_profile.a", after_object])

        differential = OUT / "differential"
        (differential / "src").mkdir(parents=True)
        (differential / "Cargo.toml").write_text(
            "[package]\nname=\"cix-squashfs-alignment\"\nversion=\"0.0.0\"\nedition=\"2021\"\n"
            "[dependencies]\ncix-portable={path=\"" + str(WORK / "portable-source-v1/cix-portable") + "\"}\n")
        (differential / "build.rs").write_text(
            "fn main(){println!(\"cargo:rustc-link-search=native=" + str(OUT) +
            "\");println!(\"cargo:rustc-link-lib=static=cix_squashfs_profile\");}\n")
        (differential / "src/main.rs").write_text(
            "#[path=\"" + str(AFTER / "tests/native_differential.rs") + "\"] mod differential;\n"
            "fn main(){let mut cases=0;for size in (0usize..=512).chain([8192,131072]){for mode in 0..3{"
            "let input:Vec<u8>=(0..size).map(|i|match mode{0=>65,1=>((i/7+i/31)%5)as u8,_=>((i*12345+(i*i>>3))&255)as u8}).collect();"
            "differential::compare_one(&input,false);if size<=8192{differential::compare_one(&input,true);}cases+=1;}}"
            "println!(\"native adaptive/profile exact-choice cases={cases}\");}\n")
        run(["cargo", "run", "--offline", "--manifest-path", differential / "Cargo.toml"],
            env={"CARGO_BUILD_JOBS": "4", "CARGO_INCREMENTAL": "0",
                 "CARGO_TARGET_DIR": str(OUT / "cargo-target")})
        final_hashes = {name: digest(path) for name, path in tracked.items()}
        final_hashes["portable_crate"] = tree_digests(WORK / "portable-source-v1/cix-portable")
        final_hashes["tools"] = {name: tool_identity(name) for name in ("cc", "objdump", "ar", "cargo")}
        if final_hashes != hashes:
            raise RuntimeError("profile inputs, complete portable crate, or tool identities changed during qualification")
        result = {"status": "pass", "input_sha256": hashes, "commands": rows,
                  "object_sha256": {"before": digest(before_object), "after": digest(after_object)},
                  "equivalence": "optimized objects byte-identical; raw objdump retained and only its known object-path preamble normalized before comparison",
                  "contract": "optimized C contract plus prior profile-qual-v2 Rust exact-choice harness (1545 cases, stack and caller-workspace decodes)"}
    except Exception as error:
        result = {"status": "fail", "input_sha256": hashes, "commands": rows, "error": str(error)}
        raise
    finally:
        (OUT / "receipt.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
