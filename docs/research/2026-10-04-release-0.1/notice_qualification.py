"""Qualify the documentation-only distribution amendment; reuse frozen binaries."""
from pathlib import Path
import hashlib
import json
import subprocess
import argparse

A = Path(__file__).resolve().parent
R = A.parents[2]
q=argparse.ArgumentParser();q.add_argument("--attempt",default="v1",choices=["v1","v2"]);args=q.parse_args()
SUFFIX="" if args.attempt=="v1" else "-"+args.attempt
W = R / ("benchmark-work/release-notice-qualification"+SUFFIX)
S = Path("/home/user/src/cix-0.1-distribution")
B = Path("/home/user/src/cix-0.1-artifacts/final/bin")
P = Path("/home/user/src/cix-0.1-artifacts/distribution"+SUFFIX+"/packages")
C = "/home/user/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin/cargo"

W.mkdir(exist_ok=True)
for name in ("package-work", "third-party"):
    (W / name).mkdir(exist_ok=False)

commands = [
    ("packages", ["python3", str(A / "package_release.py"), "--source-dir", str(S),
        "--binary-dir", str(B), "--output-dir", str(P), "--work-dir", str(W / "package-work"),
        "--source-date-epoch", "1791072000", "--execute"]),
    ("third-party", ["python3", str(A / "third_party_validate.py"), "--packages-dir", str(P),
        "--reference-bin", str(B), "--work-dir", str(W / "third-party"), "--cargo", C,
        "--jobs", "4", "--timeout", "1000", "--execute"]),
]
results = []
for name, command in commands:
    with (W / f"{name}.stdout").open("w") as out, (W / f"{name}.stderr").open("w") as err:
        result = subprocess.run(command, stdout=out, stderr=err)
    results.append({"name": name, "command": command, "exit": result.returncode,
                    "stdout": str(W / f"{name}.stdout"), "stderr": str(W / f"{name}.stderr")})
    (A / ("notice-qualification-results"+SUFFIX+".json")).write_text(json.dumps(results, indent=2) + "\n")
    if result.returncode:
        raise SystemExit(f"{name} failed; preserve this attempt")

freeze = json.loads((A / "release-binary-freeze-final.json").read_text())
for item in freeze["files"]:
    data = Path(item["path"]).read_bytes()
    assert len(data) == item["bytes"] and hashlib.sha256(data).hexdigest() == item["sha256"]
print("Documentation-only successor packages pass; frozen binary bytes are unchanged.")
