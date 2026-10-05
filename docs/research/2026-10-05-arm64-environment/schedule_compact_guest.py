"""Root-leased network access only for pinned ARM guest/Rust acquisition."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

AREA = Path(__file__).resolve().parent / "compact-guest-v1"
spec_path = Path(sys.argv[1]).resolve()
spec = json.loads(spec_path.read_text())
expected = {'run.py': '266c05ff24a0cab67e20967826b9f4bd5336a0a621b511e48e56ea8ede8f73a6', 'init.c': 'f1be1f0a60a3473195bd8a4f3bd41e3d4f8a2dbdb5ebbb04fd0a64392327bc63', 'input.json': 'f1fd0db6fd8ae6c49614cf0cd91d55f6b13797b80640ddd5bf82cb69af45c18a', 'SHA256SUMS': '2a9f11933bcee43d6080f2ba3f9bb9aad14e37c1a55416bc5604030e23013645', 'SHA256SUMS.gpg': '9dae5d0c95120b406ba407bf10214790a6fa630c525707d833666ee22680ef27'}
if (spec_path != AREA / "acquire-spec.json"
        or spec.get("purpose") != "pinned-arm64-compact-guest-acquire"
        or spec.get("command") != ["python3", str(AREA / "run.py"), "acquire"]
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
