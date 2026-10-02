#!/usr/bin/env python3
"""Queue one complete, local native Rust enwik9 qualification attempt.

The controller waits for the catalog wave, builds the pinned source, packages
and smoke-tests the actual static client, freezes one full manifest, then lets
the root dispatch that single cell.  It does not claim a Prize score.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from benchmarks.hutter_bounded_runner import REQUIRED, build_identity, canonical, execute_phase, replace_tokens, sha256, utcnow, valid_receipt
from benchmarks.hutter_experiment_scheduler import WaveScheduler, _core

AUTHORIZATION = "2026-10-02-user-one-full-rust-hutter-qualification"
STAGE = "rust_hutter_enwik9_qualification_v2"
SOURCE = Path("/home/user/src/cix-baseline-data/inputs/enwik9")
SOURCE_BYTES = 1_000_000_000
SOURCE_SHA256 = "159b85351e5f76e60cbe32e04c677847a9ecba3adc79addab6f4c6c7aa3744bc"
SOURCE_REVISION = "d66739120c40fc409f2bf011b165389fc1062c2b"
WORKTREE = Path("/home/user/src/cix-hutter-rust-qualification-d667")
CPUS, RSS_BYTES, TEMP_BYTES = [16], 9_000_000_000, 4_000_000_000
WALL_SECONDS, BUILD_WALL_SECONDS, SMOKE_WALL_SECONDS, CHUNK = 172800, 1200, 300, 1 << 20
DOC = ROOT / "docs/research/2026-10-02-rust-hutter-qualification"
RULES, AUTH, STATIC_INPUTS = DOC / "rules-snapshot.json", DOC / "authorization.json", DOC / "static-build-inputs.json"
PACKAGE = ROOT / "benchmarks/native_hutter_package"
RUST_BIN = Path("/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin")
CARGO, RUSTC = RUST_BIN / "cargo", RUST_BIN / "rustc"


def rel(path: Path) -> str:
    path = path.resolve()
    if ROOT != path and ROOT not in path.parents: raise ValueError(f"outside repository: {path}")
    return str(path.relative_to(ROOT))


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp"); temp.write_bytes(canonical(value) + b"\n"); temp.replace(path)


def input_spec() -> dict:
    return {"path": str(SOURCE), "offset": 0, "length": SOURCE_BYTES, "sha256": SOURCE_SHA256, "label": "hutter/enwik9"}


def package_sources() -> list[Path]: return [PACKAGE / "package.sh", PACKAGE / "hutter_launcher.c"]
def prebuild_sources() -> list[Path]: return [RULES, AUTH, STATIC_INPUTS, Path(__file__), ROOT / "benchmarks/hutter_bounded_runner.py", ROOT / "benchmarks/hutter_experiment_scheduler.py", *package_sources()]


def require_static(path: Path) -> None:
    hdr = subprocess.run(["readelf", "-h", str(path)], text=True, capture_output=True, check=False)
    prog = subprocess.run(["readelf", "-l", str(path)], text=True, capture_output=True, check=False)
    dyn = subprocess.run(["readelf", "-d", str(path)], text=True, capture_output=True, check=False)
    if hdr.returncode or prog.returncode or dyn.returncode or "ELF" not in hdr.stdout or "INTERP" in prog.stdout or "NEEDED" in dyn.stdout:
        raise ValueError(f"not a static ELF: {path}")


def source_checks() -> None:
    if not SOURCE.is_file() or SOURCE.stat().st_size != SOURCE_BYTES: raise RuntimeError("canonical retained enwik9 unavailable")
    for path in (RULES, AUTH, STATIC_INPUTS, *package_sources()):
        if not path.is_file(): raise RuntimeError(f"missing frozen prerequisite: {path}")
    rev = subprocess.run(["git", "-C", str(WORKTREE), "rev-parse", "HEAD"], text=True, capture_output=True, check=False)
    dirty = subprocess.run(["git", "-C", str(WORKTREE), "status", "--porcelain"], text=True, capture_output=True, check=False)
    if rev.returncode or rev.stdout.strip() != SOURCE_REVISION or dirty.returncode or dirty.stdout.strip():
        raise RuntimeError("static worktree is not the clean pinned d667 source")
    if json.loads(AUTH.read_text()).get("authorization") != AUTHORIZATION: raise RuntimeError("authorization record drift")
    static = json.loads(STATIC_INPUTS.read_text())
    for library in static.get("static_libraries", []):
        candidate = Path(library["path"])
        if not candidate.is_file() or candidate.stat().st_size != library["bytes"] or sha256(candidate) != library["sha256"]:
            raise RuntimeError("static library identity drift: " + library["name"])
    for command, expected in (([str(RUSTC), "--version"], static.get("rustc")), (["cc", "--version"], static.get("cc"))):
        actual = subprocess.run(command, text=True, capture_output=True, check=False)
        if actual.returncode or actual.stdout.splitlines()[0] != expected:
            raise RuntimeError("compiler identity drift: " + command[0])
    for tool in static.get("tools", []):
        candidate = Path(tool["path"])
        if not candidate.is_file() or candidate.stat().st_size != tool["bytes"] or sha256(candidate) != tool["sha256"]:
            raise RuntimeError("tool binary identity drift: " + tool["name"])
        probe = subprocess.run([str(candidate), "--version"], text=True, capture_output=True, check=False)
        if probe.returncode or probe.stdout.splitlines()[0] != tool["version"]:
            raise RuntimeError("tool version drift: " + tool["name"])
    for library in static.get("static_rust_stdlib", []):
        candidate = Path(library["path"])
        if not candidate.is_file() or candidate.stat().st_size != library["bytes"] or sha256(candidate) != library["sha256"]:
            raise RuntimeError("Rust standard-library identity drift: " + str(candidate))


def require_cpu() -> None:
    if not set(CPUS).issubset(os.sched_getaffinity(0)): raise RuntimeError("CPU 16 unavailable")
    if len({_core(c) for c in CPUS}) != len(CPUS): raise RuntimeError("qualification CPU is not a distinct physical core")


@contextmanager
def global_lane():
    """Take the exact WaveScheduler aggregate and physical-core locks."""
    scheduler = WaveScheduler(ROOT, max_jobs=4, max_memory_bytes=12_000_000_000, max_temp_bytes=4_000_000_000)
    scheduler.state.mkdir(parents=True, exist_ok=True)
    lock = scheduler._wave_lock_path().open("a+"); leases = []
    try:
        try: fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as err: raise RuntimeError("active WaveScheduler wave owns the global budget") from err
        leases = scheduler._lease_cores([{ "physical_core": [_core(c) for c in CPUS] }])
        yield
    finally:
        for lease in leases: lease.close()
        lock.close()


def phase(unit: str, command: list[str], work: Path, evidence: Path, wall: int, *, inaccessible: list[Path] | None = None, input_bytes: int = 0) -> dict:
    return execute_phase(unit=unit, command=command, work=work, destination=evidence,
        budget={"wall_seconds": wall, "max_rss_bytes": RSS_BYTES, "max_temp_bytes": TEMP_BYTES}, cpu=CPUS,
        inaccessible=inaccessible or [], input_bytes=input_bytes)


def copy_hash(origin: Path, destination: Path, length: int, digest: str) -> None:
    state, remain = hashlib.sha256(), length
    with origin.open("rb") as src, destination.open("xb") as dst:
        while remain:
            block = src.read(min(CHUNK, remain))
            if not block: raise RuntimeError("source truncated")
            dst.write(block); state.update(block); remain -= len(block)
    if destination.stat().st_size != length or state.hexdigest() != digest: raise RuntimeError("materialized source hash mismatch")


def native_manifest(cix: Path, uncix: Path, output: Path) -> dict:
    require_static(cix); require_static(uncix)
    toolchain = subprocess.run([str(RUSTC), "--version"], text=True, capture_output=True, check=False)
    value = {"schema": "cix-native-static-hutter-build-v1", "source_revision": SOURCE_REVISION,
      "build_method": "two cargo rustc --bin invocations with CARGO_BUILD_JOBS=1 and final-bin -C target-feature=+crt-static",
      "static_build": {"profile":"release-lto", "RUSTFLAGS":"", "CARGO_BUILD_JOBS":1,
                       "offline":True, "locked":True, "target":"host x86_64 Linux static ELF", "rustc":toolchain.stdout.strip(),
                       "cargo":str(CARGO), "RUSTC":str(RUSTC), "final_binary_flags":["-C","target-feature=+crt-static"]},
      "binaries": {n: {"sha256": sha256(p), "bytes": p.stat().st_size} for n,p in (("cix",cix),("uncix",uncix))},
      "static_elf": {"verified_no_pt_interp": True, "verified_no_dt_needed": True}, "no_python_runtime": True}
    write_json(output, value); return value


def check_package(directory: Path) -> dict:
    metadata = directory / "native-package.json"; value = json.loads(metadata.read_text())
    if value.get("schema") != "cix-native-hutter-package-static-v1" or value.get("source_revision") != SOURCE_REVISION: raise ValueError("package metadata mismatch")
    flags = value.get("compiled_flags", {})
    if flags.get("encode") != ["--best", "--threads", "1", "--verbose", "-o", "archive9.bhm", "enwik9"] or flags.get("decode") != ["-d", "-o", "data9", "archive9.bhm"] or "--memory" in flags["encode"] or value.get("external_option_bytes") != 0 or value.get("bundled_clients") != ["cix"]:
        raise ValueError("package commands do not pin ordinary BEST/default memory")
    for name in ("comp9a", "decomp9"):
        path, recorded = directory / name, value.get("programs", {}).get(name, {})
        if not path.is_file() or path.stat().st_size != recorded.get("bytes") or sha256(path) != recorded.get("sha256"): raise ValueError(f"package program mismatch: {name}")
        require_static(path)
    if (directory / "comp9a").stat().st_size != (directory / "decomp9").stat().st_size or sha256(directory / "comp9a") != sha256(directory / "decomp9"):
        raise ValueError("split-package accounting requires byte-identical comp9a and decomp9")
    return value


def area(identity: str) -> Path: return DOC / identity
def queue_state(where: Path, status: str, **extra: object) -> None: write_json(where / "queue-state.json", {"status":status,"authorization":AUTHORIZATION,"updated_at":utcnow(),**extra})


def prepare(identity: str) -> Path:
    source_checks(); require_cpu(); destination = area(identity)
    if destination.exists(): raise RuntimeError("qualification identity already exists")
    destination.mkdir(parents=True); (destination / ".gitignore").write_text("runs/**/work/\nruns/**/build/\n")
    registry = destination / "input-registry.json"; write_json(registry, {"authorization": AUTHORIZATION, "inputs": [input_spec()]})
    write_json(destination / "plan.json", {"status":"PREPARED_NOT_EXECUTED","authorization":AUTHORIZATION,"one_candidate_only":True,"source_revision":SOURCE_REVISION,"worktree":str(WORKTREE),"input":input_spec(),"resource_envelope":{"cpu":CPUS,"max_rss_bytes":RSS_BYTES,"max_temp_bytes":TEMP_BYTES,"swap_bytes":0,"full_encode_decode_wall_seconds":WALL_SECONDS},"compiled_command_intent":"--best --threads 1 --verbose, native default 512MiB, no external options","frozen_prebuild_sources":{rel(p):sha256(p) for p in prebuild_sources()},"limitations":["LOCAL_FULL_MEASUREMENT_PENDING_ELIGIBILITY","No Geekbench 5 normalization.","No OSI public source release or submission authorization.","1GiB ordinary BEST uses bounded CIXG2 streaming; 64MiB CIXB1 whole-archive candidates are excluded."]})
    queue_state(destination,"PREPARED"); return destination


def build_package_smoke(where: Path, identity: str) -> tuple[Path,dict]:
    source_checks(); require_cpu(); root = ROOT / "benchmark-work/cix-hutter-qualification" / identity
    if root.exists(): raise RuntimeError("native build destination exists")
    root.mkdir(parents=True); work,evidence = root / "work",root / "evidence"; work.mkdir(); evidence.mkdir(); target=work / "target"
    base=[str(CARGO),"rustc","--offline","--locked","--profile","release-lto","--manifest-path",str(WORKTREE / "rust/cix-native/Cargo.toml"),"--target-dir",str(target)]
    commands=[["/usr/bin/env","CARGO_BUILD_JOBS=1","RUSTC="+str(RUSTC),*base,"--bin",binary,"--","-C","target-feature=+crt-static"] for binary in ("cix","uncix")]
    with global_lane():
        queue_state(where,"STATIC_BUILD_RUNNING",native_root=rel(root)); phases=[]
        for binary, command in zip(("cix","uncix"),commands):
            row=phase("cix-hutter-static-"+binary+"-"+identity[:18],command,work,evidence,BUILD_WALL_SECONDS); phases.append(row)
            if row["exit_code"] or row["stop_reason"]:
                write_json(evidence / "static-build.json", {"status":"FAILED_STATIC_BUILD","phases":phases}); queue_state(where,"STATIC_BUILD_FAILED",phases=phases); raise RuntimeError("static build failed; no dynamic fallback")
        native=root / "native"; native.mkdir(); outputs=[]
        for binary in ("cix","uncix"):
            candidate=target / "release-lto" / binary
            if not candidate.is_file(): raise RuntimeError("cargo did not produce "+binary)
            shutil.copy2(candidate,native / binary); outputs.append(native / binary)
        # Repeat dependency/tool identity checks after compilation, before an
        # artifact is allowed into the immutable package.
        source_checks()
        native_manifest(*outputs,native / "native-release.json")
        package=work / "package"; command=["bash",str(PACKAGE / "package.sh"),"--cix",str(native / "cix"),"--uncix",str(native / "uncix"),"--native-manifest",str(native / "native-release.json"),"--out",str(package)]
        packed=phase("cix-hutter-package-"+identity[:18],command,work,evidence,SMOKE_WALL_SECONDS)
        if packed["exit_code"] or packed["stop_reason"]: write_json(evidence / "package.json", {"status":"FAILED","phase":packed}); queue_state(where,"PACKAGE_FAILED",phase=packed); raise RuntimeError("package failed")
        metadata=check_package(package); smoke=work / "smoke"; smoke.mkdir(); tiny=b"CIX static package smoke\x00"*257; (smoke / "enwik9").write_bytes(tiny)
        encoded=phase("cix-hutter-smoke-e-"+identity[:16],[str(package / "comp9a")],smoke,evidence,SMOKE_WALL_SECONDS,input_bytes=len(tiny)); decoded=None
        if not encoded["exit_code"] and not encoded["stop_reason"]: decoded=phase("cix-hutter-smoke-d-"+identity[:16],[str(package / "decomp9")],smoke,evidence,SMOKE_WALL_SECONDS,inaccessible=[smoke / "enwik9"],input_bytes=len(tiny))
        exact=bool(decoded and not decoded["exit_code"] and not decoded["stop_reason"] and (smoke / "data9").is_file() and (smoke / "data9").read_bytes()==tiny)
        result={"status":"VERIFIED" if exact else "FAILED","encode":encoded,"decode":decoded,"exact_restoration":exact,"package_sha256":sha256(package / "native-package.json")}; write_json(evidence / "smoke.json",result)
        if not exact: queue_state(where,"SMOKE_FAILED",smoke=result); raise RuntimeError("packaged static smoke failed")
        # Keep all compiler/package scratch under the monitored work directory.
        # The immutable package used by the full manifest is copied only after
        # the measured smoke gate succeeds.
        shutil.copytree(package, root / "package", copy_function=shutil.copy2)
    return root,check_package(root / "package")


def freeze_full_manifest(where: Path, root: Path, package: dict) -> Path:
    package_root=root / "package"; registry=where / "input-registry.json"; programs={n:package_root/n for n in ("comp9a","decomp9")}
    build_paths=[rel(programs["comp9a"]),rel(programs["decomp9"]),rel(package_root / "native-package.json"),rel(root / "native/cix"),rel(root / "native/uncix"),rel(root / "native/native-release.json"),"benchmarks/hutter_rust_qualification.py","benchmarks/hutter_bounded_runner.py","benchmarks/hutter_experiment_scheduler.py",rel(registry),rel(RULES),rel(AUTH),rel(STATIC_INPUTS),*(rel(p) for p in package_sources())]
    manifest={"hypothesis":"One fixed ordinary native Rust CIX BEST package performs a complete exact retained enwik9 encode/decode under bounded resources.","matched_control":"One candidate only; no route/backend/format/block/history/memory/external override and no size termination.","input":input_spec(),"stage":STAGE,"authorization":AUTHORIZATION,"configuration":{"profile":"best","automatic_selection":True,"artifact_package":rel(package_root),"compiled_encode_flags":package["compiled_flags"]["encode"],"compiled_decode_flags":package["compiled_flags"]["decode"],"memory":"native default 512MiB","threads":1},"mechanism":"Complete archive cost includes CIX framing, metadata and footer; encoding includes automatic selection work.","budget":{"cpu":CPUS,"max_rss_bytes":RSS_BYTES,"max_temp_bytes":TEMP_BYTES,"swap_bytes":0,"wall_seconds":WALL_SECONDS},"promotion_criteria":"Fresh package decoder must reproduce 1,000,000,000 bytes with the canonical SHA-256. Result remains LOCAL_FULL_MEASUREMENT_PENDING_ELIGIBILITY.","encode_command":["/usr/bin/time","-v","-o","{workdir}/encode.gnu-time.txt",str(programs["comp9a"])],"decode_command":["/usr/bin/time","-v","-o","{workdir}/decode.gnu-time.txt",str(programs["decomp9"])],"artifacts":{"archive":"{workdir}/archive9.bhm","restored":"{workdir}/data9"},"initial_state":"fresh static package processes; host cache/frequency/load uncontrolled","qualification_registry":{"path":str(registry.resolve()),"sha256":sha256(registry),"build_path":rel(registry)},"package_manifest":{"path":rel(package_root / "native-package.json"),"sha256":sha256(package_root / "native-package.json")},"rules_snapshot":{"path":rel(RULES),"sha256":sha256(RULES)},"authorization_record":{"path":rel(AUTH),"sha256":sha256(AUTH)},"static_build_inputs":{"path":rel(STATIC_INPUTS),"sha256":sha256(STATIC_INPUTS)},"build_paths":build_paths}
    path=where / "manifest.json"; write_json(path,manifest); return path


def full_load_manifest(path: Path) -> tuple[dict,str]:
    manifest=json.loads(path.read_text()); missing=[k for k in REQUIRED if k not in manifest]
    if missing: raise ValueError("manifest missing: "+", ".join(missing))
    if manifest.get("stage") != STAGE or manifest.get("authorization") != AUTHORIZATION or manifest.get("input") != input_spec(): raise ValueError("not the authorized full native enwik9 manifest")
    budget={"cpu":CPUS,"max_rss_bytes":RSS_BYTES,"max_temp_bytes":TEMP_BYTES,"swap_bytes":0,"wall_seconds":WALL_SECONDS}
    if manifest.get("budget") != budget: raise ValueError("budget drift")
    registry=manifest.get("qualification_registry",{}); rp=Path(registry.get("path", ""))
    if not rp.is_file() or registry.get("sha256") != sha256(rp) or json.loads(rp.read_text()) != {"authorization":AUTHORIZATION,"inputs":[input_spec()]}: raise ValueError("input registry mismatch")
    mp=ROOT / manifest.get("package_manifest",{}).get("path","")
    if not mp.is_file() or manifest["package_manifest"].get("sha256") != sha256(mp): raise ValueError("package identity mismatch")
    package=check_package(mp.parent); config=manifest["configuration"]
    expected_config={"profile":"best","automatic_selection":True,"artifact_package":rel(mp.parent),"compiled_encode_flags":package["compiled_flags"]["encode"],"compiled_decode_flags":package["compiled_flags"]["decode"],"memory":"native default 512MiB","threads":1}
    if config != expected_config: raise ValueError("actual package configuration mismatch")
    package_root = mp.parent
    expected_encode=["/usr/bin/time","-v","-o","{workdir}/encode.gnu-time.txt",str(package_root / "comp9a")]
    expected_decode=["/usr/bin/time","-v","-o","{workdir}/decode.gnu-time.txt",str(package_root / "decomp9")]
    if manifest.get("encode_command") != expected_encode or manifest.get("decode_command") != expected_decode or manifest.get("artifacts") != {"archive":"{workdir}/archive9.bhm","restored":"{workdir}/data9"}:
        raise ValueError("manifest command or artifact path drift")
    native_root = package_root.parent / "native"
    expected_paths=[rel(package_root / "comp9a"),rel(package_root / "decomp9"),rel(package_root / "native-package.json"),rel(native_root / "cix"),rel(native_root / "uncix"),rel(native_root / "native-release.json"),"benchmarks/hutter_rust_qualification.py","benchmarks/hutter_bounded_runner.py","benchmarks/hutter_experiment_scheduler.py",registry["build_path"],rel(RULES),rel(AUTH),rel(STATIC_INPUTS),*(rel(p) for p in package_sources())]
    if manifest.get("build_paths") != expected_paths: raise ValueError("manifest build membership drift")
    for field, frozen in (("rules_snapshot", RULES), ("authorization_record", AUTH)):
        row=manifest.get(field,{})
        if row.get("path") != rel(frozen) or row.get("sha256") != sha256(frozen): raise ValueError(field+" identity mismatch")
    static_record=manifest.get("static_build_inputs",{})
    if static_record.get("path") != rel(STATIC_INPUTS) or static_record.get("sha256") != sha256(STATIC_INPUTS): raise ValueError("static build input identity mismatch")
    for item in manifest["build_paths"]:
        if not (ROOT / item).is_file(): raise ValueError("missing build member: "+item)
    return manifest,hashlib.sha256(canonical(manifest)).hexdigest()


def final_package(manifest: dict, build: dict[str, str], snapshot: Path, work: Path, evidence: Path, archive: Path, unit: str) -> dict:
    """Copy the exact frozen wrapper used by encode/decode; never recompile it."""
    def member(suffix: str) -> Path:
        matches = [name for name in build if name.endswith(suffix)]
        if len(matches) != 1: raise RuntimeError("frozen build is missing unique " + suffix)
        return snapshot / matches[0]
    package_manifest = member("/package/native-package.json")
    source_comp, source_decomp = member("/package/comp9a"), member("/package/decomp9")
    output = work / "package-final"; output.mkdir()
    for origin, name in ((source_comp, "comp9a"), (source_decomp, "decomp9"), (package_manifest, "native-package.json"), (archive, "archive9.bhm")):
        shutil.copy2(origin, output / name)
    payload, launcher = output / "archive9.bhm", output / "comp9a"
    if sha256(payload) != sha256(archive) or sha256(launcher) != sha256(source_comp) or sha256(output / "decomp9") != sha256(source_decomp):
        raise RuntimeError("final package differs from frozen encoder/decoder program or payload")
    metadata = json.loads((output / "native-package.json").read_text())
    score = 2 * launcher.stat().st_size + payload.stat().st_size
    return {"status":"PACKAGED_EXACT_FROZEN_PROGRAMS","package_path":str(output),"package_manifest_sha256":sha256(output / "native-package.json"),
            "launcher_bytes":launcher.stat().st_size,"archive_bytes":payload.stat().st_size,"archive_sha256":sha256(payload),
            "encoder_launcher_sha256":sha256(source_comp),"decoder_launcher_sha256":sha256(source_decomp),
            "formula":"2 * length(cix9) + length(archive9.bhm) + 0 external option bytes","S_bytes":score,
            "published_one_percent_strict_max_bytes":99420424,"below_published_one_percent_strict_max":score <= 99420424,
            "status_label":"LOCAL_FULL_MEASUREMENT_PENDING_ELIGIBILITY","metadata_schema":metadata.get("schema")}


def valid_full_receipt(receipt: Path, identity: dict) -> bool:
    if not valid_receipt(receipt, identity): return False
    try:
        row=json.loads(receipt.read_text()); package=row["package_accounting"]; directory=Path(package["package_path"])
        comp,decomp,payload,metadata=directory/"comp9a",directory/"decomp9",directory/"archive9.bhm",directory/"native-package.json"
        return (package["status"] == "PACKAGED_EXACT_FROZEN_PROGRAMS" and all(p.is_file() for p in (comp,decomp,payload,metadata))
                and sha256(payload)==package["archive_sha256"]==row["archive_sha256"] and payload.stat().st_size==package["archive_bytes"]
                and sha256(comp)==package["encoder_launcher_sha256"] and sha256(decomp)==package["decoder_launcher_sha256"] and sha256(comp)==sha256(decomp) and comp.stat().st_size==decomp.stat().st_size
                and sha256(metadata)==package["package_manifest_sha256"] and package["S_bytes"] == 2*comp.stat().st_size+payload.stat().st_size)
    except (KeyError, OSError, json.JSONDecodeError, TypeError): return False


def run_full(manifest_path: Path, results: Path, root: Path) -> dict:
    manifest,msha=full_load_manifest(manifest_path); build=build_identity(manifest,root); identity={"manifest_sha256":msha,"build_sha256":build,"input":input_spec(),"configuration":manifest["configuration"],"initial_state":manifest["initial_state"]}; eid=hashlib.sha256(canonical(identity)).hexdigest(); dest=results/eid; receipt=dest/"receipt.json"
    if receipt.exists():
        if valid_full_receipt(receipt,identity): return {"status":"REUSED_VERIFIED","experiment_id":eid,"receipt":str(receipt)}
        raise ValueError("receipt identity mismatch")
    if dest.exists(): raise RuntimeError("incomplete full run immutable; no retry")
    dest.mkdir(parents=True); work,snapshot=dest/"work",dest/"build"; work.mkdir(); snapshot.mkdir(); write_json(dest/"manifest.json",manifest); write_json(dest/"identity.json",identity)
    for name,digest in build.items():
        original,copied=root/name,snapshot/name; copied.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(original,copied)
        if sha256(copied)!=digest: raise RuntimeError("snapshot hash mismatch")
        copied.chmod(0o555 if original.stat().st_mode&0o111 else 0o444)
    if not SOURCE.is_file() or SOURCE.stat().st_size != SOURCE_BYTES: raise RuntimeError("source length drift before full copy")
    materialized=work/"enwik9"; copy_hash(SOURCE,materialized,SOURCE_BYTES,SOURCE_SHA256)
    if SOURCE.stat().st_size != SOURCE_BYTES: raise RuntimeError("source length drift after full copy")
    repl={str((root/name).resolve()):str((snapshot/name).resolve()) for name in build}; values={"workdir":str(work)}; encode=[repl.get(v,v) for v in replace_tokens(manifest["encode_command"],values)]; decode=[repl.get(v,v) for v in replace_tokens(manifest["decode_command"],values)]
    started=time.monotonic(); units=["cix-hutter-full-"+eid[:12]+"-encode","cix-hutter-full-"+eid[:12]+"-decode"]; encoded=phase(units[0],encode,work,dest,WALL_SECONDS,input_bytes=SOURCE_BYTES); decoded=None; remaining=max(1,int(WALL_SECONDS-(time.monotonic()-started))); archive,restored=work/"archive9.bhm",work/"data9"
    if not encoded["exit_code"] and not encoded["stop_reason"]: decoded=phase(units[1],decode,work,dest,remaining,inaccessible=[SOURCE,materialized],input_bytes=SOURCE_BYTES)
    matched=bool(decoded and not decoded["exit_code"] and not decoded["stop_reason"] and archive.is_file() and restored.is_file() and restored.stat().st_size==SOURCE_BYTES and sha256(restored)==SOURCE_SHA256); verification={"matched":matched,"source_sha256":SOURCE_SHA256,"restored_sha256":sha256(restored) if restored.is_file() else None}
    packaging = final_package(manifest, build, snapshot, work, dest, archive, "cix-hutter-final-package-"+eid[:12]) if matched else None
    if matched and packaging.get("status") != "PACKAGED_EXACT_FROZEN_PROGRAMS": matched = False; verification["matched"] = False
    row={"status":"VERIFIED_SCREENING" if matched else "FAILED","experiment_id":eid,"identity":identity,"hypothesis":manifest["hypothesis"],"matched_control":manifest["matched_control"],"mechanism":manifest["mechanism"],"promotion_criteria":manifest["promotion_criteria"],"phases":[encoded,decoded],"budget":manifest["budget"],"resource_enforcement":"systemd cgroup MemoryMax + MemorySwapMax=0 + shared WaveScheduler physical-core lease","archive_bytes":archive.stat().st_size if archive.is_file() else None,"archive_sha256":sha256(archive) if archive.is_file() else None,"verification":verification,"artifacts":{"archive":str(archive),"restored":str(restored)},"independent_decode":"fresh packaged decomp9 received archive only; original and copied source paths inaccessible","source_materialization":{"method":"one-pass 1MiB bounded copy and SHA-256","bytes":SOURCE_BYTES},"package_accounting":packaging,"result_status":"LOCAL_FULL_MEASUREMENT_PENDING_ELIGIBILITY","completed_at":utcnow()}; write_json(dest/("receipt.json" if matched else "failed.json"),row)
    if matched: row["receipt"]=str(receipt)
    return row


def catalog_complete(path: Path) -> bool:
    try: return json.loads((path/"run-state.json").read_text()).get("status")=="COMPLETE"
    except (OSError,json.JSONDecodeError): return False


def queue(where: Path,catalog: Path) -> int:
    """One persistent controller may own a prepared identity at a time."""
    lock_path=where / "queue-controller.lock"
    with lock_path.open("a+") as lock:
        try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError as err: raise RuntimeError("qualification controller is already active") from err
        return _queue(where,catalog)


def _queue(where: Path,catalog: Path) -> int:
    # This is deliberately a controller, not a one-shot readiness probe.  It
    # leaves an atomic progress record every 30 seconds while the catalog owns
    # the four-core shared lane, then proceeds exactly once.
    while not catalog_complete(catalog):
        queue_state(where,"WAITING_FOR_CATALOG",catalog_area=str(catalog),poll_seconds=30)
        time.sleep(30)
    source_checks(); plan=json.loads((where/"plan.json").read_text()); current={rel(p):sha256(p) for p in prebuild_sources()}
    if plan.get("frozen_prebuild_sources") != current: raise RuntimeError("prebuild source changed after preparation")
    if (where/"manifest.json").exists():
        queue_state(where,"FULL_MANIFEST_ALREADY_FROZEN")
    else:
        root,package=build_package_smoke(where,where.name); manifest=freeze_full_manifest(where,root,package); frozen,digest=full_load_manifest(manifest); cell={"manifest_sha256":digest,"build_sha256":build_identity(frozen,ROOT)}; write_json(where/"cell.json",cell); queue_state(where,"FULL_MANIFEST_FROZEN",cell=cell,manifest=rel(manifest),native_root=rel(root))
    result=dispatch(where); queue_state(where,"TERMINAL",scheduler_result=result)
    return 0 if result.get("runner_status") in {"VERIFIED_SCREENING","REUSED_VERIFIED"} else 1


def dispatch(where: Path) -> dict:
    manifest_path=where/"manifest.json"; manifest,digest=full_load_manifest(manifest_path); cell={"cell_id":"cix-rust-hutter-"+digest[:32],"owner":"/root","manifest_path":rel(manifest_path),"output_dir":rel(where/"runs/native-best"),"cpu":CPUS,"expected_manifest_sha256":digest,"expected_build_sha256":build_identity(manifest,ROOT),"fresh_justification":"one explicitly authorized full native Rust qualification"}
    import benchmarks.hutter_experiment_scheduler as sched
    sched.load_manifest=full_load_manifest; runner=WaveScheduler(ROOT,max_jobs=4,max_memory_bytes=12_000_000_000,max_temp_bytes=4_000_000_000,runner_command=(sys.executable,str(ROOT/"benchmarks/hutter_rust_qualification.py")))
    # Scheduler's generic receipt check is insufficient for a scored package:
    # require its copied programs, manifest and payload as well as archive and
    # restored bytes before allowing a completed cell to be reused.
    runner._verified_receipt=lambda receipt, plan: valid_full_receipt(Path(receipt), {"manifest_sha256":plan["manifest_sha256"],"build_sha256":plan["build_sha256"],"input":input_spec(),"configuration":plan["manifest"]["configuration"],"initial_state":plan["manifest"].get("initial_state","empty")})
    queue_state(where,"FULL_RUN_DISPATCHED",cell=cell); return runner.run_wave([cell])[0]


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument("--id"); parser.add_argument("--prepare",action="store_true"); parser.add_argument("--queue",action="store_true"); parser.add_argument("--run",action="store_true"); parser.add_argument("--catalog-area",type=Path); parser.add_argument("--manifest",type=Path,help=argparse.SUPPRESS); parser.add_argument("--results",type=Path,help=argparse.SUPPRESS); parser.add_argument("--root",type=Path,default=ROOT,help=argparse.SUPPRESS); args=parser.parse_args()
    if args.manifest or args.results:
        if not(args.manifest and args.results): parser.error("runner needs --manifest and --results")
        row=run_full(args.manifest,args.results,args.root); print(json.dumps(row,sort_keys=True)); return 0 if row["status"] in {"VERIFIED_SCREENING","REUSED_VERIFIED"} else 1
    if not args.id or not args.id.replace("-","").isalnum() or sum((args.prepare,args.queue,args.run)) != 1: parser.error("use exactly one action and an alphanumeric --id")
    where=area(args.id)
    if args.prepare: print(json.dumps({"prepared":rel(prepare(args.id)),"execution":"not started"},sort_keys=True)); return 0
    if not where.is_dir(): raise RuntimeError("qualification identity has not been prepared")
    if args.queue:
        if not args.catalog_area: parser.error("--queue needs --catalog-area")
        return queue(where,args.catalog_area)
    result=dispatch(where); print(json.dumps(result,sort_keys=True)); return 0 if result.get("runner_status") in {"VERIFIED_SCREENING","REUSED_VERIFIED"} else 1

if __name__ == "__main__": raise SystemExit(main())
