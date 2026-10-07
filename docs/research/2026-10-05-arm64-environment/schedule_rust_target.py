"""Root-leased network access only for pinned ARM guest/Rust acquisition."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

AREA = Path(__file__).resolve().parent / "rust-target-v1"
spec_path = Path(sys.argv[1]).resolve()
spec = json.loads(spec_path.read_text())
expected = {'run.py': '022b101aa9eed0f9cd334a3652c1783ba23b55794c9ad31c01bab87a39431d69', 'input.json': 'e7485801dc7f0a455b40121f14717c116c3efb8fc4eca93fcf3c0c15f623a064'}
if (spec_path != AREA / "spec.json"
        or spec.get("purpose") != "pinned-arm64-rust-target-acquire"
        or spec.get("command") != ["python3", str(AREA / "run.py")]
        or any(hashlib.sha256((AREA / name).read_bytes()).hexdigest() != digest
               for name, digest in expected.items())):
    raise SystemExit("only pinned ARM guest and Rust target acquisition is admitted")
original = subprocess.run


def networked(command, *args, **kwargs):
    if isinstance(command, list) and command[:3] == ["sudo", "-n", "systemd-run"]:
        command = ["--property=PrivateNetwork=no" if x == "--property=PrivateNetwork=yes" else x
                   for x in command]
    return original(command, *args, **kwargs)


subprocess.run = networked
module_spec = importlib.util.spec_from_file_location(
    "release_schedule", AREA.parents[1] / "2026-10-04-release-0.1/schedule.py")
module = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(module)
sys.exit(module.run(spec))
