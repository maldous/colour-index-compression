import json,hashlib,subprocess,os
from pathlib import Path
assert os.environ.get("CIX_SUPPORT_LEASE")=="1"
root=Path("/home/user/src/colour-index-compression");area=root/"docs/research/2026-10-03-constraint-space/segmentation/support-evidence";binary=root/"benchmark-work/segmentation-support/build/support"
rows=[]
for row in json.loads((area.parent/"mask-evidence/results.json").read_text()):
 q=row["candidates"]["auto"];path=Path(q["archive"]);assert hashlib.sha256(path.read_bytes()).hexdigest()==q["archive_sha256"]
 cp=subprocess.run([str(binary),"inspect",str(path)],capture_output=True,text=True,check=True);v=json.loads(cp.stdout);assert v["archive_bytes"]==q["bytes"] and v["header_bytes"]+v["lane_metadata_bytes"]+v["payload_bytes"]==q["bytes"]
 rows.append(dict(fixture=row["fixture"]["name"],archive_sha256=q["archive_sha256"],inspection=v))
(area/"results.json").write_text(json.dumps(rows,indent=2)+"\n");print("Verified",len(rows),"existing archives; no new archives or codec timing cells",flush=True)
