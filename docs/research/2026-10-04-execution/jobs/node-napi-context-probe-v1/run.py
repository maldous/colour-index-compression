#!/usr/bin/env python3
"""Capture one bounded Node N-API compiler context, without an analyzer run."""
from __future__ import annotations
import argparse, hashlib, json, os, signal, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
JOB = Path(__file__).resolve().parent
SOURCE = ROOT / "rust/cix-native/bindings/node/src/cix_node.c"
SDK = ROOT / "benchmark-work/native-rc-check-v1/sdk-bindings-relocated-cli-bindings-v8/include"
NODE = Path("/usr/include/node")
CC = Path("/usr/bin/cc")
BWRAP = Path("/usr/bin/bwrap")
CARRIER = ROOT / "docs/research/2026-10-04-execution/sonar-preparation/prepared-v6/compile_commands.host.json"
NODE_V2 = ROOT / "docs/research/2026-10-04-execution/jobs/node-unwrap-v2/receipt.json"
NODE_V3 = ROOT / "docs/research/2026-10-04-execution/jobs/node-unwrap-v3/receipt.json"
CAP = 8 << 20
ARGS = ["/usr/bin/cc", "-DNAPI_VERSION=8", "-Dcix_node_EXPORTS", "-I/mnt", "-I/usr/include/node", "-fPIC", "-fvisibility=hidden", "-c", "/usr/src/rust/cix-native/bindings/node/src/cix_node.c"]

def sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()
def key(path: Path) -> str:
    try: return str(path.relative_to(ROOT))
    except ValueError: return str(path)
def write(path: Path, data: bytes) -> None:
    if len(data) > CAP: raise RuntimeError("bounded output exceeds cap: " + path.name)
    path.write_bytes(data)
def command(argv: list[str], out: Path, err: Path) -> dict:
    proc = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            start_new_session=True, env={"PATH":"/usr/bin:/bin","LC_ALL":"C"})
    try: stdout, stderr = proc.communicate(timeout=45)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL); stdout, stderr = proc.communicate()
        raise RuntimeError("preprocessor timeout")
    write(out, stdout); write(err, stderr)
    return {"argv":argv, "returncode":proc.returncode,
            "stdout":str(out.relative_to(ROOT)), "stderr":str(err.relative_to(ROOT))}
def sandbox(arguments: list[str]) -> list[str]:
    return [str(BWRAP), "--unshare-net", "--die-with-parent", "--new-session", "--ro-bind", "/", "/",
            "--ro-bind", str(ROOT), "/usr/src", "--ro-bind", str(SDK), "/mnt",
            "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp", "--chdir", "/usr/src", *arguments]
def historical_context() -> dict:
    v2, v3 = json.loads(NODE_V2.read_text()), json.loads(NODE_V3.read_text())
    source_key = str(SOURCE)
    if v3.get("status") != "pass" or v3.get("source_and_artifact_sha256",{}).get(source_key) != sha(SOURCE):
        raise RuntimeError("passed Node-v3 receipt does not bind current source")
    rows = json.loads(CARRIER.read_text())
    row = next((r for r in rows if r.get("file") == source_key), None)
    expected = [str(CC), "-DNAPI_VERSION=8", "-Dcix_node_EXPORTS", "-I"+str(SDK), "-I"+str(NODE), "-fPIC", "-fvisibility=hidden", "-c", source_key]
    if not isinstance(row,dict) or row.get("arguments") != expected:
        raise RuntimeError("prepared command carrier differs from measured Node command")
    build = next((r for r in v2.get("commands",[]) if r.get("label") == "build-addon-only"), None)
    if not build or build.get("returncode") != 0:
        raise RuntimeError("Node-v2 receipt lacks successful add-on compilation")
    return {"node_v2_receipt_sha256":sha(NODE_V2), "node_v3_receipt_sha256":sha(NODE_V3),
            "command_carrier_sha256":sha(CARRIER), "historical_build_addon_returncode":0}
def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument("--out",type=Path,required=True); args=parser.parse_args()
    if os.environ.get("CIX_RELEASE_LEASE") != "1": raise RuntimeError("root scheduler lease required")
    out=args.out.resolve()
    if out.exists(): raise RuntimeError("refusing to overwrite Node context attempt")
    inputs=(SOURCE, SDK/"cix.h", NODE/"node_api.h", NODE/"js_native_api.h", NODE/"js_native_api_types.h", CC, CC.resolve(), BWRAP, CARRIER, NODE_V2, NODE_V3, Path(__file__), JOB/"spec.json")
    if any(not path.is_file() for path in inputs): raise RuntimeError("required input absent")
    before={key(path):sha(path) for path in inputs}
    out.mkdir(parents=True); raw=out/"raw"; raw.mkdir()
    receipt={"status":"started", "scope":"newly measured compiler preprocessing context; not historical compiler qualification", "qualified_command_carrier":str(CARRIER.relative_to(ROOT)), "command":ARGS, "input_sha256":before, "historical_context":historical_context(), "commands":[]}
    try:
        for name, extra in (("effective-macros",["-E","-dM"]),("include-trace",["-E","-H"]),("registration-expansion",["-E","-dD"])):
            row=command(sandbox([*ARGS[:-2],*extra,ARGS[-1]]), raw/(name+".stdout"), raw/(name+".stderr")); receipt["commands"].append(row)
            if row["returncode"]: raise RuntimeError(name+" failed")
        expansion=(raw/"registration-expansion.stdout").read_text(errors="replace")
        trace=(raw/"include-trace.stderr").read_text(errors="replace")
        included=sorted({Path(line.lstrip(". ")) for line in trace.splitlines() if line.lstrip(". ").startswith("/usr/include/node/")})
        receipt["effective_node_header_sha256"]={str(path):sha(path) for path in included if path.is_file()}
        tokens=("node_api_module_get_api_version_v1","napi_register_module_v1","return init(env, exports)")
        receipt["registration_tokens_present"]={t:t in expansion for t in tokens}
        if not all(receipt["registration_tokens_present"].values()): raise RuntimeError("expected Node registration expansion absent")
        receipt["status"]="captured_no_analyzer_run"
    except Exception as error:
        receipt.update(status="failed",error=str(error))
    finally:
        receipt["input_sha256_after"]={key(path):sha(path) for path in inputs}
        if receipt["input_sha256_after"] != before: receipt["status"]="failed_input_changed"
        write(out/"receipt.json",(json.dumps(receipt,indent=2)+"\n").encode())
    return 0 if receipt["status"]=="captured_no_analyzer_run" else 1
if __name__=="__main__": sys.exit(main())
