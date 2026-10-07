#!/usr/bin/env python3
"""Bounded local contract checks for the platform inventory writer; no workflow dispatch."""
from __future__ import annotations
import hashlib, importlib.util, json, os, shutil, subprocess, sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[5]
TOOL = PROJECT / "tools/platform-validation/inventory.py"
WORKFLOW = PROJECT / ".github/workflows/cix-platform-validation.yml"
WORK = PROJECT / "benchmark-work/native-rc-check-v1/platform-inventory-local-v1"

def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def run(args: list[str], expected: int) -> dict[str, object]:
    result = subprocess.run([sys.executable, str(TOOL), *args], text=True, capture_output=True,
                            timeout=15, check=False)
    if result.returncode != expected:
        raise RuntimeError(f"unexpected return code {result.returncode}: {result.stderr}")
    return {"argv": args, "returncode": result.returncode, "stderr": result.stderr[:512]}

def main() -> None:
    if os.environ.get("CIX_RELEASE_LEASE") != "1": raise RuntimeError("root scheduler lease required")
    if WORK.exists(): raise RuntimeError("refusing to reuse work")
    WORK.mkdir(parents=True)
    inputs_before = {str(path.relative_to(PROJECT)): digest(path) for path in (TOOL, WORKFLOW)}
    receipt: dict[str, object] = {"schema":"cix-platform-inventory-local-v1","inputs_before":inputs_before,"phases":[]}
    try:
        valid = WORK / "valid.json"
        receipt["phases"].append(run(["--source-sha", "0" * 40, "--target", "linux-arm64", "--output", str(valid)], 0))
        observed = json.loads(valid.read_text())
        if "target_matches_observed_host" not in observed["observed"]: raise RuntimeError("target observation missing")
        receipt["phases"].append(run(["--source-sha", "0" * 40, "--target", "linux-arm64", "--output", str(valid)], 1))
        receipt["phases"].append(run(["--source-sha", "A" * 40, "--target", "linux-arm64", "--output", str(WORK / "bad-sha.json")], 1))
        receipt["phases"].append(run(["--source-sha", "0" * 40, "--target", "not-a-target", "--output", str(WORK / "bad-target.json")], 2))
        spec = importlib.util.spec_from_file_location("platform_inventory", TOOL)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        overflow = WORK / "overflow-tool"
        timeout = WORK / "timeout-tool"
        overflow.write_text("#!/usr/bin/env python3\nprint('x' * 8192)\n")
        timeout.write_text("#!/usr/bin/env python3\nimport time; time.sleep(10)\n")
        overflow.chmod(0o755); timeout.chmod(0o755)
        old_path = os.environ.get("PATH", "")
        os.environ["PATH"] = str(WORK) + os.pathsep + old_path
        try:
            overflow_fact = module.toolchain_fact("overflow-tool")
            timeout_fact = module.toolchain_fact("timeout-tool")
        finally:
            os.environ["PATH"] = old_path
        if not overflow_fact.get("output_overflow_observed") or len(overflow_fact.get("version_first_line", "")) > 512:
            raise RuntimeError("overflow probe did not retain a bounded result")
        if not timeout_fact.get("timed_out") or timeout_fact.get("termination_scope") not in {"process-group", "direct-child"}:
            raise RuntimeError("timeout probe did not record bounded termination")
        receipt["probe_fixtures"] = {"overflow": overflow_fact, "timeout": timeout_fact}
        inputs_after = {str(path.relative_to(PROJECT)): digest(path) for path in (TOOL, WORKFLOW)}
        receipt["inputs_after"] = inputs_after
        if inputs_before != inputs_after: raise RuntimeError("workflow or inventory tool changed during local contract check")
        receipt["status"] = "pass"
    except Exception as error:
        receipt["status"] = "fail"; receipt["error"] = str(error); raise
    finally:
        (WORK / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
if __name__ == "__main__": main()
