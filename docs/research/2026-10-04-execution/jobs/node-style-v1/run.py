#!/usr/bin/env python3
"""Lease-gated fresh Node add-on build and contract qualification."""
from __future__ import annotations
import hashlib, json, os, resource, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
JOB = Path(__file__).resolve().parent
WORK = ROOT / "benchmark-work/native-rc-check-v1/node-style-v1"
NODE = ROOT / "rust/cix-native/bindings/node"
SDK = ROOT / "benchmark-work/native-rc-check-v1/sdk-bindings-relocated-cli-bindings-v8"
SOURCE = NODE / "src/cix_node.c"
INPUTS = JOB / "inputs.json"

CAP = 8 << 20
ADDITIONAL_TEMP_BYTES = 32 << 20

def digest(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()
def key(path: Path) -> str:
    try: return str(path.relative_to(ROOT))
    except ValueError: return str(path)
def child_file_limit() -> None:
    resource.setrlimit(resource.RLIMIT_FSIZE, (CAP, CAP))
def execute(label: str, argv: list[str], env: dict[str,str], receipt: dict) -> None:
    out, err = JOB/(label+".stdout.log"), JOB/(label+".stderr.log")
    with out.open("wb") as so, err.open("wb") as se:
        result = subprocess.run(argv, cwd=WORK, env=env, stdout=so, stderr=se,
                                timeout=300, preexec_fn=child_file_limit)
    receipt["commands"].append({"label":label,"argv":argv,"returncode":result.returncode,
        "stdout":str(out.relative_to(ROOT)),"stderr":str(err.relative_to(ROOT))})
    if result.returncode: raise RuntimeError(label+" failed")
def main() -> int:
    if os.environ.get("CIX_RELEASE_LEASE") != "1": raise RuntimeError("root scheduler lease required")
    if WORK.exists(): raise RuntimeError("refusing to reuse fresh Node-style work directory")
    expected=json.loads(INPUTS.read_text())
    paths={key(path): path for path in (SOURCE, NODE / "CMakeLists.txt", NODE / "test/contract.js", SDK / "include/cix.h", SDK / "include/cix_stream.h", SDK / "lib/libcix_native.so", Path("/usr/include/node/node_api.h"), Path("/usr/include/node/js_native_api.h"), Path("/usr/include/node/js_native_api_types.h"), Path("/usr/include/node/node_api_types.h"), Path("/usr/bin/cmake"), Path("/usr/bin/cc"), Path("/usr/bin/node"), JOB / "spec.json", JOB / "run.py")}
    if set(paths) != set(expected) or any(not path.is_file() or digest(path) != expected[name] for name,path in paths.items()):
        raise RuntimeError("exact retained source, SDK, header, or tool identity changed")
    retained_bytes=int(subprocess.check_output(["du","-sx","-B1",str(WORK.parent)],text=True).split()[0])
    if retained_bytes + ADDITIONAL_TEMP_BYTES > 4_000_000_000: raise RuntimeError("shared temporary-space admission failed")
    WORK.mkdir(parents=True)
    before={name:digest(path) for name,path in paths.items()}
    receipt={"status":"started","scope":"fresh Node add-on CMake build and contract only; Sonar is excluded",
             "input_sha256_before":before,"commands":[],"child_file_size_limit_bytes":CAP,"shared_work_bytes_before":retained_bytes,"additional_work_budget_bytes":ADDITIONAL_TEMP_BYTES}
    env={"PATH":"/usr/bin:/bin","LD_LIBRARY_PATH":str(SDK/"lib"),
         "CIX_NODE_ADDON":str(WORK/"build/cix_node.node")}
    try:
        execute("configure",["/usr/bin/cmake","-S",str(NODE),"-B",str(WORK/"build"),
            "-DCIX_SDK_INCLUDE_DIR="+str(SDK/"include"),"-DCIX_SDK_LIBRARY="+str(SDK/"lib/libcix_native.so"),
            "-DNODE_API_INCLUDE_DIR=/usr/include/node","-DCMAKE_C_COMPILER=/usr/bin/cc",
            "-DCMAKE_BUILD_TYPE=Release"],env,receipt)
        execute("build-addon-only",["/usr/bin/cmake","--build",str(WORK/"build"),"--parallel","2"],env,receipt)
        execute("node-contract",["/usr/bin/node",str(NODE/"test/contract.js")],env,receipt)
        receipt["work_allocated_bytes"] = int(subprocess.check_output(["du", "-sx", "-B1", str(WORK)], text=True).split()[0])
        if receipt["work_allocated_bytes"] > ADDITIONAL_TEMP_BYTES:
            raise RuntimeError("Node build exceeded local temporary-space reservation")
        receipt["status"]="pass"
    except Exception as error:
        receipt.update(status="fail",error=str(error))
    finally:
        receipt["input_sha256_after"]={name:digest(path) for name,path in paths.items()}
        artifact=WORK / "build/cix_node.node"
        receipt["fresh_addon_sha256"] = digest(artifact) if artifact.is_file() else None
        receipt["inputs_unchanged"]=receipt["input_sha256_after"]==before
        if not receipt["inputs_unchanged"]: receipt["status"]="fail_input_changed"
        (JOB/"receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
    return 0 if receipt["status"]=="pass" else 1
if __name__=="__main__": sys.exit(main())
