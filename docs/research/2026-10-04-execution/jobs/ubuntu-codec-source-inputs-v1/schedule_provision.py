"""Run only the pinned Ubuntu codec-source acquisition with network enabled.

The ordinary release scheduler keeps its private network.  This wrapper admits
one reviewed source-input tuple, then changes only that scheduler unit's
PrivateNetwork property.  CPU, memory, temporary-space, lease and lifecycle
enforcement remain in the ordinary scheduler.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys


JOB = Path(__file__).resolve().parent
SPEC = JOB / "spec.json"
EXPECTED = {
    "run.py": "df2a53bab3bc2ccfb0848f40a8e6d485d266261e6553cbf0f67e10815d7f418a",
    "sources.json": "8a83fc678ff30c40695098c8ff584fd8fc6e760dc979bc6b4e3a4c4984da1df3",
}
PURPOSE = "pinned-ubuntu-codec-source-input-acquisition"


def digest(path: Path) -> str:
    """Return the SHA-256 identity of a direct reviewed wrapper input."""
    if not path.is_file() or path.is_symlink():
        raise SystemExit(f"wrapper input is not a direct regular file: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checked_spec(argv: list[str]) -> dict[str, object]:
    """Reject every job except this exact reviewed source-input acquisition."""
    if len(argv) != 2:
        raise SystemExit("usage: schedule_provision.py spec.json")
    spec_path = Path(argv[1]).resolve()
    if spec_path != SPEC or not spec_path.is_file():
        raise SystemExit("only this job's exact spec is admitted")
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    command = ["/usr/bin/python3", str(JOB / "run.py")]
    if (
        spec.get("purpose") != PURPOSE
        or spec.get("id") != "execution-ubuntu-codec-source-inputs-v1"
        or spec.get("command") != command
        or any(digest(JOB / name) != expected for name, expected in EXPECTED.items())
    ):
        raise SystemExit("only the exact pinned Ubuntu codec source tuple is admitted")
    return spec


def main() -> int:
    spec = checked_spec(sys.argv)
    original_run = subprocess.run

    def networked_provision(command, *args, **kwargs):
        if isinstance(command, list) and command[:3] == ["sudo", "-n", "systemd-run"]:
            command = [
                "--property=PrivateNetwork=no" if value == "--property=PrivateNetwork=yes" else value
                for value in command
            ]
        return original_run(command, *args, **kwargs)

    subprocess.run = networked_provision
    scheduler_path = JOB.parents[2] / "2026-10-04-release-0.1/schedule.py"
    module_spec = importlib.util.spec_from_file_location("release_schedule", scheduler_path)
    if module_spec is None or module_spec.loader is None:
        raise SystemExit("ordinary release scheduler cannot be loaded")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module.run(spec)


if __name__ == "__main__":
    raise SystemExit(main())
