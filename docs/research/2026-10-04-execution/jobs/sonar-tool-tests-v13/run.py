"""Root-leased focused checks for analysis tooling, with unchanged-source proof."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
TOOLS = [ROOT / "tools" / "sonar-cxx", ROOT / "tools" / "sonar-native"]
PLANNING = ROOT / "docs/research/2026-10-04-execution/reviews/validate_planning_graph.py"


def identities():
    paths = [path for folder in TOOLS for path in sorted(folder.glob("*.py"))]
    paths.extend([ROOT / "rust/cix-native/src/cli.rs", PLANNING, ROOT / "docs/research/2026-10-04-execution/dependency-blockers.json",
                  ROOT / "docs/research/2026-10-04-rc-reconciliation/requirements.json"])
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


def main():
    if os.environ.get("CIX_RELEASE_LEASE") != "1":
        raise RuntimeError("root scheduler lease required")
    before = identities()
    for name, expected in before.items():
        body = (ROOT / name).read_bytes()
        if hashlib.sha256(body).hexdigest() != expected:
            raise RuntimeError("source changed while freezing tests")
        frozen = OUT / "frozen-inputs" / name
        frozen.parent.mkdir(parents=True, exist_ok=True)
        frozen.write_bytes(body)
    receipt = {"source_sha256": before, "commands": [], "status": "started"}
    for folder in TOOLS:
        argv = [sys.executable, "-m", "unittest", "discover", "-s", str(folder), "-p", "test_*.py", "-v"]
        result = subprocess.run(argv, check=False, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        receipt["commands"].append({"argv": argv, "returncode": result.returncode})
    argv = [sys.executable, str(PLANNING)]
    result = subprocess.run(argv, check=False, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    receipt["commands"].append({"argv": argv, "returncode": result.returncode})
    argv = ["/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/rustfmt", "--edition", "2021", "--check", str(ROOT / "rust/cix-native/src/cli.rs")]
    result = subprocess.run(argv, check=False)
    receipt["commands"].append({"argv": argv, "returncode": result.returncode})
    receipt["source_unchanged"] = identities() == before
    receipt["status"] = "pass" if receipt["source_unchanged"] and all(
        row["returncode"] == 0 for row in receipt["commands"]) else "fail"
    (OUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return 0 if receipt["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
