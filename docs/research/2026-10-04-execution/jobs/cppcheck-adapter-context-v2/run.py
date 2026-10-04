"""Check six adapter projections, retaining new kernel context as analysis only."""
import collections
import importlib.util
import json
import os
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[5]
JOB = Path(__file__).resolve().parent
OUT = ROOT / "benchmark-work/native-rc-check-v1/cppcheck-adapter-context-v2"


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


def main():
    if os.environ.get("CIX_RELEASE_LEASE") != "1":
        raise RuntimeError("root scheduler lease required")
    repair = module("adapter_context_repair", ROOT / "tools/sonar-cxx/repair.py")
    context = module("adapter_context_validation", ROOT / "tools/sonar-cxx/translation_context.py")
    paths = [ROOT / "tools/sonar-cxx" / name for name in ("repair.py", "translation_context.py")]
    before = {str(path.relative_to(ROOT)): repair.digest(path) for path in paths}
    prepared = ROOT / "docs/research/2026-10-04-execution/sonar-preparation/prepared-v6"
    commands = json.loads((prepared / "compile_commands.host.json").read_text())
    files = sorted(context.PROJECTABLE_RELATIVES)
    plan = json.loads((prepared / "plan.json").read_text())
    selected = {name: repair.digest(ROOT / name) for name in files}
    # These six source TUs are unchanged from the recorded prepared closure.
    for name, value in selected.items():
        matches = [item for scope in plan["scopes"].values() for item in scope["files"] if item["path"] == name]
        if len(matches) != 1 or matches[0]["sha256"] != value:
            raise RuntimeError("prepared adapter source identity changed: " + name)
    budget = repair.EvidenceBudget(OUT)
    budget.mkdir(OUT)
    receipt = {"status": "started", "tool_sha256": before, "source_sha256": selected,
               "prepared_compile_database_sha256": repair.digest(prepared / "compile_commands.host.json")}
    for path in paths:
        (JOB / (path.name + ".txt")).write_bytes(path.read_bytes())
    try:
        repair.cppcheck(ROOT, files, OUT, commands, budget)
        errors = list(ET.parse(OUT / "cppcheck.xml").iter("error"))
        counts = dict(collections.Counter(error.get("id") for error in errors))
        fatal = {key: counts[key] for key in ("syntaxError", "internalError", "unknownMacro", "preprocessorErrorDirective") if counts.get(key)}
        projections = json.loads((OUT / "cppcheck-preprocessing.json").read_text())
        if len(projections) != 6:
            raise RuntimeError("not all six adapter compiler projections were analyzed")
        actual = json.loads((OUT / "compile_commands.cppcheck.json").read_text())
        if any(argument.startswith("-Wp,-MMD,") for row in actual for argument in row["arguments"]):
            raise RuntimeError("old dependency output survived into the analyzer database")
        receipt.update(projected_translation_units=6, diagnostics=counts, fatal_configuration=fatal,
                       old_dependency_outputs_absent_from_analyzer_database=True)
        if fatal:
            raise RuntimeError("adapter analysis configuration gaps remain")
        receipt["source_and_tools_unchanged"] = all(repair.digest(ROOT / name) == value for name, value in {**before, **selected}.items())
        if not receipt["source_and_tools_unchanged"]:
            raise RuntimeError("analysis input changed during the action")
        receipt["status"] = "pass_scoped_analysis"
    except Exception as error:
        receipt.update(status="fail", error=str(error))
        raise
    finally:
        repair.save(OUT / "receipt.json", receipt, budget)
        for path in OUT.iterdir():
            if path.is_file():
                (JOB / path.name).write_bytes(path.read_bytes())


if __name__ == "__main__":
    main()
