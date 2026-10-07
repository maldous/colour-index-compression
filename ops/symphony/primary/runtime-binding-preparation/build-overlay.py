#!/usr/bin/env python3
"""Prepared only; run inside the owner's freshly admitted bounded helper."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

PREP = Path(__file__).resolve().parent
PLAN = PREP / "plan.json"
plan = json.loads(PLAN.read_text())
runtime = Path(plan["public_runtime_root"]).resolve()
out = Path(plan["output_root"])

def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

cg = next(line.split(":", 2)[2] for line in Path("/proc/self/cgroup").read_text().splitlines() if line.startswith("0::"))
if not cg.startswith(plan["resource_preflight"]["required_parent"]):
    raise SystemExit("not in the admitted system aggregate")
control = Path("/sys/fs/cgroup") / cg.lstrip("/")
limit = control.joinpath("memory.max").read_text().strip()
if limit == "max" or int(limit) > plan["resource_preflight"]["max_memory_bytes"]:
    raise SystemExit("memory limit unbound")
if control.joinpath("memory.swap.max").read_text().strip() != "0":
    raise SystemExit("swap limit unbound")
if sorted(os.sched_getaffinity(0)) != plan["resource_preflight"]["cpu_affinity"]:
    raise SystemExit("CPU affinity unbound")
for source in plan["source_files"]:
    if sha(Path(source["path"])) != source["sha256"]:
        raise SystemExit("reviewed source changed")
for name, digest in plan["public_entry_input_pins"].items():
    if sha(runtime / name) != digest:
        raise SystemExit("public entry/compiler input changed")
loader = plan["external_musl_loader"]
if sha(Path(loader["path"])) != loader["sha256"]:
    raise SystemExit("public external musl loader changed")
# Fresh namespace only; preserve a failed partial derivation for owner reconciliation.
out.mkdir(mode=0o700, exist_ok=False)
closure = {}

def copy_public(relative):
    source = runtime / relative
    resolved = source.resolve(strict=True)
    if not resolved.is_relative_to(runtime):
        raise RuntimeError("external runtime symlink rejected")
    if not resolved.is_file():
        raise RuntimeError("non-regular public runtime input")
    destination = out / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(resolved, destination)
    digest = sha(resolved)
    if sha(destination) != digest:
        raise RuntimeError("public runtime copy pin mismatch")
    closure[str(relative)] = digest

for subtree in plan["public_copy_trees"]:
    for path in sorted((runtime / subtree).rglob("*")):
        if path.is_file() or path.is_symlink():
            if path.is_symlink() and path.resolve().is_dir():
                raise RuntimeError("directory symlink requires explicit closure binding")
            copy_public(path.relative_to(runtime))
for relative in plan["public_copy_files"]:
    copy_public(Path(relative))
for file in ["bootstrap.exs", "launch.sh"]:
    shutil.copy2(PREP / file, out / file)
shutil.copy2(PLAN, out / "derivation-plan.json")
out.joinpath("launch.vm.args").write_text("-noinput\n")
# Materialize the retained official ERTS launcher template in this new closure.
launcher = out / "erts-16.4/bin/erl"
if launcher.exists():
    raise RuntimeError("unexpected existing erl launcher")
launcher.write_bytes((out / "erts-16.4/bin/erl.src").read_bytes().replace(b"%FINAL_ROOTDIR%", str(out).encode()))
launcher.chmod(0o700)
# No COOKIE/auth files are copied. Extracted official eval gets an unused cookie
# with distribution disabled; credential injection remains the owner's boundary.
env = {key: value for key, value in os.environ.items() if key in ["PATH", "LANG", "LC_ALL", "TMPDIR"]}
env.update(ROOTDIR=str(out), BINDIR=str(out / "erts-16.4/bin"), EMU="beam", PROGNAME="erl", ERL_FLAGS="")
args = [str(out / "erts-16.4/bin/erlexec"), "+S", "1:1", "-noshell", "-boot", str(out / "releases/0.0.3/start_clean"),
        "-boot_var", "RELEASE_LIB", str(out / "lib"), "-pa", str(out / "lib/elixir-1.19.5/ebin"),
        "-s", "elixir", "start_cli", "-extra", str(PREP / "compile-overlay.exs"), str(out), str(PLAN)]
with out.joinpath("derivation.log").open("wb") as log:
    result = subprocess.run(args, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=90)
receipt = {"status": "DERIVED_NOT_ACTIVATED" if result.returncode == 0 else "DERIVATION_FAILED",
           "exit_code": result.returncode, "control_group": cg, "memory_max_actual_bytes": int(limit),
           "memory_peak_bytes": int(control.joinpath("memory.peak").read_text()), "swap_max": 0,
           "public_closure_sha256": closure, "plan_sha256": sha(PLAN),
           "builder_inputs_sha256": {p.name: sha(p) for p in [Path(__file__), PREP / "compile-overlay.exs", PREP / "bootstrap.exs", PREP / "launch.sh"]},
           "external_loader": loader, "reviewed_patch_sha256": plan["reviewed_patch_sha256"],
           "services_started": False, "tests_replayed": False, "credentials_copied": False,
           "closure_bytes": sum(p.stat().st_size for p in out.rglob("*") if p.is_file())}
out.joinpath("artifact-derivation.json").write_text(json.dumps(receipt, indent=2) + "\n")
raise SystemExit(result.returncode)
