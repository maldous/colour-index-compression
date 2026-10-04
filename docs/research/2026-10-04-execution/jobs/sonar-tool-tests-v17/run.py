"""Root-leased focused Cppcheck projection-repair checks, with unchanged-source proof."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
TOOLS = [ROOT / "tools" / "sonar-cxx"]
FOCUSED = ["test_repair.py"]


def identities():
    paths = [ROOT / "tools" / "sonar-cxx" / name for name in ("repair.py", "test_repair.py", "include_context.py", "test_include_context.py", "translation_context.py", "test_translation_context.py")]
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
    for name in FOCUSED:
        argv = [sys.executable, "-m", "unittest", "discover", "-s", str(ROOT / "tools" / "sonar-cxx"), "-p", name, "-v"]
        result = subprocess.run(argv, check=False, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        receipt["commands"].append({"argv": argv, "returncode": result.returncode})
    receipt["source_unchanged"] = identities() == before
    receipt["status"] = "pass" if receipt["source_unchanged"] and all(
        row["returncode"] == 0 for row in receipt["commands"]) else "fail"
    (OUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return 0 if receipt["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
