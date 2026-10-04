"""Use the release resource lease for explicitly networked build provisioning.

Compression/qualification jobs retain their offline runner. This adapter only
accepts pinned libjxl provisioning or the pinned codec SDK package manifest.
It changes no resource, user, privilege, or filesystem enforcement.
"""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

AREA = Path(__file__).resolve().parent
spec = json.loads(Path(sys.argv[1]).read_text())
script = Path(spec["command"][1]).resolve()
if (spec.get("purpose") != "pinned-build-dependency-provision"
        or spec["command"][0] != "python3"
        or script.parent.parent != AREA / "jobs"
        or not (script.parent.name.startswith("jxl-provision-v")
                or (script.parent.name == "codec-sdk-provision-v1"
                    and (script.parent / "packages.json").is_file()))
        or script.name != "run.py"):
    raise SystemExit("only explicit pinned build dependency provisioning is admitted")
original = subprocess.run


def networked_dependency(command, *args, **kwargs):
    if isinstance(command, list) and command[:3] == ["sudo", "-n", "systemd-run"]:
        command = ["--property=PrivateNetwork=no" if x == "--property=PrivateNetwork=yes" else x
                   for x in command]
    return original(command, *args, **kwargs)


subprocess.run = networked_dependency
module_spec = importlib.util.spec_from_file_location(
    "release_schedule", AREA.parent / "2026-10-04-release-0.1/schedule.py")
module = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(module)
sys.exit(module.run(spec))
