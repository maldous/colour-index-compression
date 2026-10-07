"""One-shot system-service placement check; no scheduler or monitor."""
import json
import os
from fractions import Fraction
from pathlib import Path

parent = "/cix.slice/cix-bau139.slice"
expected = parent + "/cix-symphony-primary.service"
paths = [line.split(":", 2)[2] for line in Path("/proc/self/cgroup").read_text().splitlines() if line.startswith("0::")]
if paths != [expected]:
    raise SystemExit("Primary service must use SYSTEM manager in existing /cix.slice/cix-bau139.slice")
base = Path("/sys/fs/cgroup")
aggregate = base / parent.lstrip("/")
service = base / expected.lstrip("/")
page_bytes = os.sysconf("SC_PAGE_SIZE")

def effective_memory(nominal):
    return nominal // page_bytes * page_bytes

if int((aggregate / "memory.max").read_text().strip()) != effective_memory(24000000000):
    raise SystemExit("Unexpected aggregate memory limit")
if (aggregate / "memory.swap.max").read_text().strip() != "0":
    raise SystemExit("Aggregate swap must remain disabled")
quota, period = (aggregate / "cpu.max").read_text().split()
if quota == "max" or Fraction(int(quota), int(period)) != 8:
    raise SystemExit("Unexpected aggregate CPU quota")
if int((service / "memory.max").read_text().strip()) != effective_memory(20000000000):
    raise SystemExit("Ordinary service envelope must preserve 4GB logical hold")
if (service / "memory.swap.max").read_text().strip() != "0":
    raise SystemExit("Service swap must remain disabled")
print(json.dumps({"placement":"SYSTEM_AGGREGATE_PASS","control_group":expected,"aggregate_memory_max":24000000000,"ordinary_memory_max":20000000000,"page_bytes":page_bytes,"effective_ordinary_memory_max":effective_memory(20000000000),"repair_hold_released":False}))
