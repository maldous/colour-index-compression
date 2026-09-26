#!/usr/bin/env python3
import json
from pathlib import Path

EXPECTED={"alice29.txt":152089,"asyoulik.txt":125179,"cp.html":24603,"fields.c":11150,
"grammar.lsp":3721,"kennedy.xls":1029744,"lcet10.txt":426754,
"plrabn12.txt":481861,"ptt5":513216,"sum":38240,"xargs.1":4227}

rows=[]
for p in Path("member-results").rglob("member-*.json"):
    rows.append(json.loads(p.read_text()))
rows.sort(key=lambda r:list(EXPECTED).index(r["member"]))
seen={r["member"] for r in rows}
missing=[m for m in EXPECTED if m not in seen]

out=["# Native CIX Canterbury matrix","",
     "| file | native CIX | xz-9 | seconds |","|---|---:|---:|---:|"]
for r in rows:
    out.append(f'| {r["member"]} | {100*r["cix"]/r["original"]:.2f}% | {100*r["xz"]/r["original"]:.2f}% | {r["seconds"]:.2f} |')
out.append("")
if rows:
    original=sum(r["original"] for r in rows)
    out.append(f"- Completed: {len(rows)}/11")
    out.append(f"- Completed-members native CIX aggregate: {100*sum(r['cix'] for r in rows)/original:.2f}%")
    out.append(f"- Completed-members xz aggregate: {100*sum(r['xz'] for r in rows)/original:.2f}%")
if not missing:
    total=sum(EXPECTED.values())
    out.append(f"- Full native CIX aggregate: {100*sum(r['cix'] for r in rows)/total:.2f}%")
    out.append(f"- Full xz aggregate: {100*sum(r['xz'] for r in rows)/total:.2f}%")
else:
    out.append("- Missing/timed-out: "+", ".join(missing))
out.append("")
out.append("## Winning block models")
for r in rows:
    from collections import Counter
    c=Counter(r["models"])
    summary=", ".join(f"{k}×{v}" for k,v in c.most_common())
    out.append(f'- {r["member"]}: {summary}')
Path("native-matrix-results.md").write_text("\n".join(out)+"\n")
print("\n".join(out))
