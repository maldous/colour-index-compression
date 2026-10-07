"""Exercise the integrated current compiler closure and five projected TUs."""
import collections
import importlib.util
import json
import os
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[5]
JOB = Path(__file__).resolve().parent


def main():
    if os.environ.get("CIX_RELEASE_LEASE") != "1":
        raise RuntimeError("root scheduler lease required")
    spec = importlib.util.spec_from_file_location("cix_repair_integration", ROOT / "tools/sonar-cxx/repair.py")
    repair = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = repair
    spec.loader.exec_module(repair)
    tools = [ROOT / "tools/sonar-cxx/repair.py", ROOT / "tools/sonar-cxx/compiler_refresh.py"]
    before = {str(path.relative_to(ROOT)): repair.digest(path) for path in tools}
    prepared = ROOT / "docs/research/2026-10-04-execution/sonar-preparation/prepared-v5"
    repair.prepare(ROOT, prepared)
    plan = json.loads((prepared / "plan.json").read_text())
    if plan["unconfigured_translation_units"]:
        raise RuntimeError("current compiler closure is incomplete: " + repr(plan["unconfigured_translation_units"]))
    commands = json.loads((prepared / "compile_commands.host.json").read_text())
    files = sorted(repair.CPPHECK_PROJECTED_RELATIVES)
    out = ROOT / "benchmark-work/native-rc-check-v1/cppcheck-integration-v1"
    budget = repair.EvidenceBudget(out)
    budget.mkdir(out)
    repair.cppcheck(ROOT, files, out, commands, budget)
    errors = list(ET.parse(out / "cppcheck.xml").iter("error"))
    counts = dict(collections.Counter(error.get("id") for error in errors))
    fatal = {key: counts[key] for key in ("syntaxError", "internalError", "unknownMacro", "preprocessorErrorDirective") if counts.get(key)}
    projections = json.loads((out / "cppcheck-preprocessing.json").read_text())
    actual = json.loads((out / "compile_commands.cppcheck.json").read_text())
    expected = {row["projected"] for row in projections}
    if len(projections) != 5 or {row["file"] for row in actual} != expected:
        raise RuntimeError("analyzer did not receive all five compiler projections")
    unchanged = all(repair.digest(ROOT / path) == identity for path, identity in before.items())
    receipt = {"tool_sha256": before, "tools_unchanged": unchanged,
               "prepared_plan_sha256": repair.digest(prepared / "plan.json"),
               "projected_translation_units": len(projections), "diagnostics": counts,
               "fatal_configuration": fatal, "evidence_accounted_bytes": budget.used(),
               "source_sha256": {name: repair.digest(ROOT / name) for name in files},
               "status": "pass" if unchanged and not fatal else "fail"}
    repair.save(out / "receipt.json", receipt, budget)
    for name in ("receipt.json", "cppcheck-preprocessing.json", "cppcheck-execution.json", "cppcheck.host.xml", "cppcheck.xml"):
        (JOB / name).write_bytes((out / name).read_bytes())
    return 0 if receipt["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
