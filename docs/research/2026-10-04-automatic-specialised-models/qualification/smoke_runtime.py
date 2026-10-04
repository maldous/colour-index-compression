"""Focused staged-command/backend verification; never uses corpus assets."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def main() -> None:
    stage, work = map(Path, sys.argv[1:3])
    work.mkdir(parents=True, exist_ok=True)
    source = work / "fixture.bin"
    data = b"CIX staged closure: arbitrary bytes\n" * 8 + bytes(range(256))
    source.write_bytes(data)
    results = []
    profiles = () if "--image-only" in sys.argv else (("fast", ["--fast"]), ("default", []), ("best", ["--best"]))
    for profile, flags in profiles:
        archive, restored = work / (profile + ".cix"), work / (profile + ".out")
        report = work / (profile + ".json")
        subprocess.run([str(stage / "bin/cix"), *flags, "--report", str(report),
                        "-o", str(archive), str(source)], check=True)
        subprocess.run([str(stage / "bin/uncix"), "-o", str(restored), str(archive)], check=True)
        if restored.read_bytes() != data:
            raise RuntimeError("staged command restoration mismatch")
        selection = json.loads(report.read_text())
        failures = [row for row in selection["trials"] if row["status"] != "completed"]
        if failures:
            raise RuntimeError(f"staged candidate failure: {failures}")
        results.append({"profile": profile, "archive_bytes": archive.stat().st_size,
                        "selected": selection["selected"], "status": "VERIFIED"})
    environment = dict(os.environ, PYTHONPATH=str(stage / "python/site-packages"),
                       CIX_BACKEND_ROOT=str(stage / "libexec/cix"),
                       LD_LIBRARY_PATH=str(stage / "python/site-packages/imagecodecs.libs"))
    script = work / "image_fixture.py"
    script.write_text('''from pathlib import Path
import sys
from cix_runtime.image_grid import _mode3_identity
from cix_runtime.legacy import spatial_image_codec, multiscale_volume
from cix_runtime.engine import decode
def tag(g,e,v):
    return g.to_bytes(2,"little")+e.to_bytes(2,"little")+len(v).to_bytes(4,"little")+v
data=(tag(0x28,0x10,b"\\x02\\x00")+tag(0x28,0x11,b"\\x02\\x00")
      +tag(0x28,0x100,b"\\x10\\x00")+tag(0x7fe0,0x10,bytes(range(16))))
p=Path(sys.argv[1])
if sys.argv[2]=="encode":
    region=spatial_image_codec.regions(data)[0]
    frame,details=_mode3_identity(data,region)
    assert details["shared_current_encode"]
    expected=multiscale_volume.encode(data,region,0,0,0,10)[0]
    assert len(expected)==details["logical_candidate_bytes"]["CIXI2"]
    if details["selected_format"]=="CIXI2":
        assert frame==expected
    assert decode(expected)==data
    p.write_bytes(frame)
else:
    assert decode(p.read_bytes())==data
''')
    archive = work / "image.cix"
    for operation in ("encode", "decode"):
        subprocess.run([str(stage / "python/bin/python3"), str(script), str(archive), operation],
                       env=environment, check=True)
    results.append({"profile": "shared-volume-cixi2", "status": "VERIFIED",
                    "archive_bytes": archive.stat().st_size})
    (work / "result.json").write_text(json.dumps({"results": results,
        "fixture_sha256": hashlib.sha256(data).hexdigest()}, indent=2) + "\n")


if __name__ == "__main__":
    main()
