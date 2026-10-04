#!/usr/bin/env python3
"""Pinned CXX/Cppcheck analysis of the frozen CIX source, after confirmation.

prepare is read-only with respect to product sources. run requires all 36
confirmation cells VERIFIED and the existing exclusive WaveScheduler lease.
This is SonarOpenCommunity CXX, not SonarSource's licensed CFamily analyzer.
"""
from __future__ import annotations

import argparse
import collections
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import shlex
import subprocess
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
HYGIENE = ROOT / "docs/research/2026-10-04-automatic-specialised-models/hygiene"
SOURCE = ROOT.parent / "cix-integrated-source-candidate"
TOOLS = ROOT.parent / "cix-sonar-cxx-tools"
SUMMARY = HYGIENE.parent / "qualification/silesia-confirmation-v1/summary.json"
STOP = SUMMARY.parent / "stop-20261004-user/stop.json"
STOP_COMMIT = "e9731f4bd"
STOP_PLAN_SHA256 = "6181ed5066495a12bc6fa09a41f5b14cb2442b4aaae0b16e0ddf015356432eaa"
STOP_SHA256 = "ed3c2aaf8ef104e2305c80defffcab8607c608525126b018ed9c85725feeed54"
STOP_VERIFIED = {
    "confirm-fast-dickens", "confirm-default-dickens", "confirm-best-dickens",
    "confirm-fast-mozilla", "confirm-default-mozilla",
}
STOP_INTERRUPTED = "confirm-best-mozilla"
SUFFIXES = {".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx"}
SCOPES = {
    "first-party": ["native/src", "native/packaging/squash"],
    "native-vendor": ["native/vendor"],
    **{f"paq-{name}": [f"vendor/paq/{name}"]
       for name in ("v215", "v216", "joint-discount", "store-state")},
}
PACKAGES = {
    "sonar-cxx-plugin-2.3.0.1496.jar": (
        "https://github.com/SonarOpenCommunity/sonar-cxx/releases/download/cxx-2.3.0/sonar-cxx-plugin-2.3.0.1496.jar",
        "95dd162a04d954a63713dd7cc6b4e14f1d361de6645dffdd8755069a12ea0197"),
    "cppcheck.deb": (
        "https://archive.ubuntu.com/ubuntu/pool/universe/c/cppcheck/cppcheck_2.13.0-2ubuntu3_amd64.deb",
        "c84251e17148b6b4ff3698bb71ceec0f445896d97888bedad8bba471c00aeadf"),
    "libtinyxml2.deb": (
        "https://archive.ubuntu.com/ubuntu/pool/universe/t/tinyxml2/libtinyxml2-10_10.0.0+dfsg-2_amd64.deb",
        "7444576728d0886cc58cee1749dc2ab5a680c1756f0a8b49c973fa0cfb180973"),
}


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def save(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def provision() -> None:
    """Download only checksummed tooling, without installing system packages."""
    TOOLS.mkdir(exist_ok=True)
    for name, (url, expected) in PACKAGES.items():
        path = TOOLS / name
        if not path.exists():
            with urllib.request.urlopen(url, timeout=60) as response:
                body = response.read()
            if hashlib.sha256(body).hexdigest() != expected:
                raise RuntimeError(f"download checksum mismatch: {name}")
            path.write_bytes(body)
        if digest(path) != expected:
            raise RuntimeError(f"tool checksum mismatch: {name}")
        if name.endswith(".deb"):
            subprocess.run(["dpkg-deb", "-x", str(path), str(TOOLS / "cppcheck")], check=True)
    save(TOOLS / "provenance.json", {
        "packages": {name: {"url": url, "sha256": sha}
                     for name, (url, sha) in PACKAGES.items()},
        "cppcheck": "Ubuntu noble 2.13.0-2ubuntu3; private extraction, no system mutation",
        "plugin": "CXX 2.3.0.1496; requires Java >=21; live server compatibility must be verified",
    })


def inventory(source: Path) -> dict:
    result = {}
    for name, roots in SCOPES.items():
        files = []
        for prefix in roots:
            directory = source / prefix
            if not directory.is_dir():
                raise RuntimeError(f"missing source scope: {directory}")
            for path in sorted(directory.rglob("*")):
                if path.is_file() and path.suffix.lower() in SUFFIXES:
                    if path.is_symlink():
                        raise RuntimeError(f"symlink in source scope: {path}")
                    files.append({"path": str(path.relative_to(source)), "sha256": digest(path)})
        if not files:
            raise RuntimeError(f"empty source scope: {name}")
        result[name] = {"roots": roots, "files": files}
    return result


def compilation_metadata(source: Path, scopes: dict) -> tuple[list, dict]:
    """Reuse verified PAQ configuration; describe native build.rs configuration.

    These are analysis settings, NOT a new build or fresh build-wrapper receipt.
    The parser additionally analyzes inventoried files outside the database.
    """
    database, provenance = [], {}
    registry = json.loads((ROOT / "runtime/backend-sources.json").read_text())["base"]
    for name in ("v215", "v216", "joint-discount", "store-state"):
        original = ROOT / registry[name]["source"]
        path = original.parent / "build-local/compile_commands.json"
        records = json.loads(path.read_text())
        for record in records:
            old_file = Path(record["file"])
            relative = old_file.relative_to(original)
            new_file = source / "vendor/paq" / name / relative
            if digest(old_file) != digest(new_file):
                raise RuntimeError(f"retained PAQ translation unit changed: {new_file}")
            args = record.get("arguments") or shlex.split(record["command"])
            args = [item.replace(str(original), str(source / "vendor/paq" / name)) for item in args]
            database.append({"file": str(new_file), "directory": str(source / "vendor/paq" / name), "arguments": args})
        provenance[name] = {"database": str(path), "sha256": digest(path), "entries": len(records),
                            "status": "retained compile settings; each translation unit matches frozen source"}
    for name in ("first-party", "native-vendor"):
        for row in scopes[name]["files"]:
            path = source / row["path"]
            if path.suffix.lower() not in {".cpp", ".c", ".cc", ".cxx"}:
                continue
            flags = ["-std=c++17", "-Dunix", "-D__linux__", "-I" + str(source / "native/vendor/libbsc/libbsc"),
                     "-I" + str(source / "native/vendor/libzpaq715")]
            if "libzpaq" in str(path) or path.name == "zpaq_ffi.cpp":
                flags.append("-DNOJIT")
            compiler = "g++"
            if path.name == "squash-cix.c":
                compiler, flags = "gcc", ["-std=c11", "-Dunix", "-D__linux__"]
            database.append({"file": str(path), "directory": str(source),
                             "arguments": [compiler, *flags, "-c", str(path)]})
    provenance["native"] = {"build_rs_sha256": digest(source / "native/build.rs"),
        "status": "analysis configuration derived from frozen build.rs; not a compilation receipt",
        "squash": "optional C adapter indexed; external Squash SDK include resolution reported by analyzers"}
    return database, provenance


def prepare(source: Path, out: Path) -> None:
    if out.exists():
        raise RuntimeError("refusing to overwrite prepared evidence")
    scopes = inventory(source)
    commands, provenance = compilation_metadata(source, scopes)
    out.mkdir(parents=True)
    excluded = [{"path": str(p.relative_to(source)), "reason": "CUDA header; CUDA/OpenMP disabled in frozen native/build.rs"}
                for p in sorted((source / "native/vendor").rglob("*.cuh"))]
    save(out / "plan.json", {"source": str(source), "scopes": scopes, "analyzer": "SonarOpenCommunity CXX + Cppcheck",
        "commercial_cfamily": False, "excluded": excluded, "confirmation_summary": str(SUMMARY),
        "tools": {name: sha for name, (_, sha) in PACKAGES.items()},
        "status": "PREPARED_NOT_SCANNED", "compilation_metadata": provenance})
    save(out / "compile_commands.host.json", commands)
    save(out / "compile_commands.container.json", json.loads(json.dumps(commands).replace(str(source), "/usr/src")))
    print(json.dumps({"prepared": str(out), "files": {k: len(v["files"]) for k, v in scopes.items()},
                      "compile_commands": len(commands), "excluded_cuda": len(excluded)}))


def require_confirmation(summary: Path) -> None:
    value = json.loads(summary.read_text())
    plan_path = summary.with_name("plan.json")
    plan = json.loads(plan_path.read_text())
    expected = {row["id"]: row for row in plan["cells"]}
    rows = value.get("rows", [])
    if (len(expected) != 36 or len(rows) != 36
            or {row["cell"] for row in rows} != set(expected)
            or value.get("plan_sha256") != digest(plan_path)
            or any(row.get("status") != "VERIFIED" for row in rows)):
        raise RuntimeError("full 36-cell confirmation is not yet VERIFIED; do not compete with the frozen run")
    for row in rows:
        cell = expected[row["cell"]]
        if row["source"] != cell["source"] or row["profile"] != cell["profile"]:
            raise RuntimeError("confirmation identities differ from the frozen plan")


def _committed_stop_bytes(stop: Path) -> bytes:
    """Read the stop receipt from its pinned commit, never trusting a worktree copy."""
    relative = stop.relative_to(ROOT).as_posix()
    result = subprocess.run(["git", "show", f"{STOP_COMMIT}:{relative}"], cwd=ROOT,
                            check=False, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    if result.returncode:
        raise RuntimeError("pinned benchmark-stop receipt is absent from its authenticated checkpoint")
    return result.stdout


def require_stopped_confirmation(summary: Path, stop: Path = STOP, *,
                                 committed_reader=_committed_stop_bytes, root: Path = ROOT) -> None:
    """Authorize non-benchmark hygiene only for the exact user-stopped run.

    This is deliberately narrower than accepting a status string: both the
    receipt and its commit copy must hash-match, and every planned cell must be
    classified exactly once as verified, interrupted, or unstarted.
    """
    plan_path = summary.with_name("plan.json")
    if digest(plan_path) != STOP_PLAN_SHA256:
        raise RuntimeError("stopped-run authorization has a different frozen plan")
    if not stop.is_file() or digest(stop) != STOP_SHA256 or committed_reader(stop) != stop.read_bytes():
        raise RuntimeError("stopped-run receipt is not the pinned committed receipt")
    receipt, value, plan = json.loads(stop.read_text()), json.loads(summary.read_text()), json.loads(plan_path.read_text())
    if receipt.get("status") != "STOPPED_BY_USER" or receipt.get("plan_sha256") != STOP_PLAN_SHA256:
        raise RuntimeError("stopped-run receipt is not an authorized user stop")
    if receipt.get("automatic_restart_allowed") is not False:
        raise RuntimeError("stopped-run receipt permits restart")
    expected = {row["id"] for row in plan.get("cells", [])}
    verified = set(receipt.get("verified_cells", []))
    interrupted = receipt.get("interrupted_cells", [])
    unstarted = set(receipt.get("not_started_cells", []))
    if (len(expected) != 36 or verified != STOP_VERIFIED or len(interrupted) != 1
            or interrupted[0] != {"cell": STOP_INTERRUPTED, "phase": "encode", "status": "INTERRUPTED_UNQUALIFIED", "decode_started": False}
            or len(unstarted) != 30 or expected != verified | {STOP_INTERRUPTED} | unstarted
            or len(verified | {STOP_INTERRUPTED} | unstarted) != 36):
        raise RuntimeError("stopped-run receipt has invalid cell classification")
    rows = value.get("rows", [])
    if (value.get("plan_sha256") != STOP_PLAN_SHA256 or value.get("stop_receipt") != str(stop.relative_to(root))
            or {row.get("cell") for row in rows} != verified or any(row.get("status") != "VERIFIED" for row in rows)):
        raise RuntimeError("summary does not match the pinned stopped-run receipt")


def assert_benchmark_idle(*, runner=subprocess.run, cgroup_root: Path = Path("/sys/fs/cgroup")) -> None:
    """Fail closed if the stopped confirmation could have resumed on this host."""
    listing = runner(["ps", "-eo", "pid=,args="], check=True, text=True,
                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL).stdout
    markers = (str(SUMMARY.parent), "finish-frozen-cix-silesia-confirmation",
               "complete-cix-0-1-release-qualification")
    if any(marker in line for line in listing.splitlines() for marker in markers):
        raise RuntimeError("a stopped benchmark process is active")
    for unit in ("finish-frozen-cix-silesia-confirmation.service", "complete-cix-0-1-release-qualification.service"):
        state = runner(["systemctl", "show", unit, "--property=ActiveState", "--value"],
                               check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL).stdout.strip()
        if state != "inactive":
            raise RuntimeError("a stopped benchmark unit is active or unknown")
    if cgroup_root.exists():
        matches = list(cgroup_root.rglob("*silesia-confirmation*"))
        if any(path.is_dir() and any(path.iterdir()) for path in matches):
            raise RuntimeError("a stopped benchmark cgroup is active or unknown")


def validate_indexed(files: list[str], components: list[dict], log: str) -> set[str]:
    indexed = {row["path"] for row in components if row.get("language") == "cxx"}
    missing = sorted(set(files) - indexed)
    if missing or "Sensor CXX [cxx]" not in log:
        raise RuntimeError(f"CXX source analysis incomplete: missing={missing}")
    return indexed


def cppcheck(source: Path, files: list[str], out: Path, commands: list) -> None:
    executable = TOOLS / "cppcheck/usr/bin/cppcheck"
    cfg = TOOLS / "cppcheck/usr/lib/x86_64-linux-gnu/cppcheck/cfg"
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = str(TOOLS / "cppcheck/usr/lib/x86_64-linux-gnu")
    selected = [row for row in commands if Path(row["file"]).relative_to(source).as_posix() in files]
    database = out / "compile_commands.cppcheck.json"
    save(database, selected)
    arguments = [str(executable), "--xml", "--xml-version=2", "--enable=warning,style,performance,portability,information",
                 "--platform=unix64", "--max-configs=12", "-j", "2", "--library=" + str(cfg / "std.cfg"),
                 "--library=" + str(cfg / "posix.cfg")]
    if selected:
        arguments.append("--project=" + str(database))
    else:
        arguments.extend(str(source / file) for file in files if Path(file).suffix in {".c", ".cpp", ".cc", ".cxx"})
    with (out / "cppcheck.stdout").open("w") as stdout, (out / "cppcheck.host.xml").open("w") as stderr:
        result = subprocess.run(arguments, cwd=source, env=env, stdout=stdout, stderr=stderr, timeout=3600)
    save(out / "cppcheck-execution.json", {"argv": arguments, "exit": result.returncode,
         "checked_translation_units": len(selected), "configuration_limit": 12})
    if result.returncode:
        raise RuntimeError("Cppcheck did not complete")
    report = ET.parse(out / "cppcheck.host.xml")
    for location in report.iter("location"):
        for key in ("file", "file0"):
            if key in location.attrib:
                file = Path(location.attrib[key])
                if file.is_absolute() and file.is_relative_to(source):
                    location.attrib[key] = "/usr/src/" + str(file.relative_to(source))
    report.write(out / "cppcheck.xml", encoding="utf-8", xml_declaration=True)


def request(h, base: str, password: str, endpoint: str, fields=None):
    payload = urllib.parse.urlencode(fields).encode() if fields is not None else None
    return h.api(base, endpoint, "admin", password, payload)


def profile(h, base: str, password: str, raw: Path) -> None:
    repositories = request(h, base, password, "/api/rules/repositories?language=cxx")
    save(raw / "rule-repositories.json", repositories)
    selected = [row["key"] for row in repositories["repositories"]
                if row["key"] == "cxx" or "cppcheck" in row["key"].lower()]
    if not any("cppcheck" in key for key in selected) or "cxx" not in selected:
        raise RuntimeError("CXX native/Cppcheck rule repositories are missing")
    created = request(h, base, password, "/api/qualityprofiles/create", {"language": "cxx", "name": "CIX CXX and Cppcheck"})
    key = created["profile"]["key"]
    activated = request(h, base, password, "/api/qualityprofiles/activate_rules", {"targetKey": key, "repositories": ",".join(selected)})
    request(h, base, password, "/api/qualityprofiles/set_default", {"language": "cxx", "qualityProfile": "CIX CXX and Cppcheck"})
    active = request(h, base, password, "/api/rules/search?activation=true&qprofile=" + urllib.parse.quote(key) + "&ps=1")
    if active.get("total", active.get("paging", {}).get("total", 0)) < 1:
        raise RuntimeError("CXX profile has no active rules")
    save(raw / "profile.json", {"created": created, "activated": activated, "active_rules": active})


def scan(h, base: str, password: str, token: str, envfile: Path, parent: str,
         name: str, source: Path, files: list[str], commands: list, out: Path) -> dict:
    out.mkdir()
    key = "cix-cxx-" + name
    cppcheck(source, files, out, commands)
    mapped = json.loads(json.dumps(commands).replace(str(source), "/usr/src"))
    save(out / "compile_commands.json", mapped)
    (out / "properties").write_text("\n".join([
        f"sonar.projectKey={key}", "sonar.sources=" + ",".join(files), "sonar.sourceEncoding=UTF-8",
        "sonar.scm.disabled=true", "sonar.scm.exclusions.disabled=true", "sonar.working.directory=/tmp/.scannerwork",
        "sonar.cxx.file.suffixes=" + ",".join(sorted(SUFFIXES)), "sonar.cxx.cppcheck.reportPaths=/out/cppcheck.xml",
        "sonar.cxx.jsonCompilationDatabase=/out/compile_commands.json",
        "sonar.cxx.jsonCompilationDatabase.analyzeOnlyContainedFiles=false", ""]) )
    task = h.scan_project(name="cxx-" + name, image=h.SCANNER_IMAGE, parent=parent, envfile=envfile,
                          source=source, out=out, properties=out / "properties", token_values=[password, token])
    h.collect(base, key, task, password, out)
    components, page = [], 1
    while True:
        result = request(h, base, password, f"/api/components/tree?component={key}&qualifiers=FIL&ps=500&p={page}")
        components.extend(result["components"])
        if len(components) >= result["paging"]["total"]:
            break
        page += 1
    save(out / "indexed-files.json", components)
    log = (out / "scanner.log").read_text()
    indexed = validate_indexed(files, components, log)
    issues = json.loads((out / "issues.json").read_text())["issues"]
    if name == "probe" and not any("nullpointer" in row["rule"].lower() for row in issues):
        raise RuntimeError("known null-pointer canary was not imported as a Sonar issue")
    diagnostics = [line for line in log.splitlines() if re.search(r"parse error|parsing error|unable to parse|cannot parse", line, re.I)]
    errors = [row.attrib for row in ET.parse(out / "cppcheck.xml").iter("error")]
    return {"status": "SCANNED", "expected_files": len(files), "indexed_cxx_files": len(indexed),
            "issues": len(issues), "rules": dict(collections.Counter(row["rule"] for row in issues)),
            "parser_diagnostics": diagnostics, "cppcheck_diagnostics": dict(collections.Counter(row["id"] for row in errors)),
            "quality_gate": json.loads((out / "quality-gate.json").read_text())}


def execute(prepared: Path, out: Path, source: Path, parent: str) -> None:
    h = load_module("cix_sonar_runtime", HYGIENE / "run_scan.py")
    plan = json.loads((prepared / "plan.json").read_text())
    if inventory(source) != plan["scopes"]:
        raise RuntimeError("source no longer matches prepared manifest")
    for name, (_, expected) in PACKAGES.items():
        if digest(TOOLS / name) != expected:
            raise RuntimeError("tool package changed: " + name)
    out.mkdir(parents=True)
    raw = out / "raw"; raw.mkdir()
    save(raw / "tool-identities.json", {str(p): digest(p) for p in (
        Path(__file__), HYGIENE / "run_scan.py", HYGIENE / "schedule_scan.py",
        TOOLS / "cppcheck/usr/bin/cppcheck", TOOLS / "cppcheck/usr/lib/x86_64-linux-gnu/libtinyxml2.so.10.0.0")})
    for kind, image in (("server", h.SERVER_IMAGE), ("scanner", h.SCANNER_IMAGE)):
        (raw / (kind + "-image-inspect.json")).write_text(h.image_receipt(image))
    base, server = "http://127.0.0.1:9017", "cix-cxx-sonarqube"
    password = "Aa1!" + secrets.token_urlsafe(32)
    token = None
    envfile = raw / ".scanner-env"
    results = {"status": "STARTED", "analyzer": "SonarOpenCommunity CXX 2.3.0.1496 + Cppcheck 2.13.0",
               "plan_sha256": digest(prepared / "plan.json"), "projects": {}}
    try:
        h.docker_run(server, h.SERVER_IMAGE, h.SERVER_MEMORY, parent, [
            "-p", "127.0.0.1:9017:9000",
            "--tmpfs", "/opt/sonarqube/data:rw,uid=1000,gid=0,size=1g",
            "--tmpfs", "/opt/sonarqube/logs:rw,uid=1000,gid=0,size=128m",
            "--tmpfs", "/opt/sonarqube/temp:rw,uid=1000,gid=0,size=1536m",
            "-v", f"{TOOLS / 'sonar-cxx-plugin-2.3.0.1496.jar'}:/opt/sonarqube/extensions/plugins/sonar-cxx-plugin.jar:ro"])
        h.wait_server(base, password)
        languages = request(h, base, password, "/api/languages/list")
        save(raw / "languages.json", languages)
        save(raw / "plugins.json", request(h, base, password, "/api/plugins/installed"))
        if "cxx" not in {row["key"] for row in languages["languages"]}:
            raise RuntimeError("installed plugin did not register CXX")
        profile(h, base, password, raw)
        token = request(h, base, password, "/api/user_tokens/generate", {"name": "cix-cxx-repair"})["token"]
        fd = os.open(envfile, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "w") as stream:
            stream.write(f"SONAR_HOST_URL={base}\nSONAR_TOKEN={token}\n")
        probe = out / "probe-source"; probe.mkdir()
        (probe / "probe.cpp").write_text("int main() { int *p = nullptr; return *p; }\n")
        results["probe"] = scan(h, base, password, token, envfile, parent, "probe", probe, ["probe.cpp"], [], out / "probe")
        commands = json.loads((prepared / "compile_commands.host.json").read_text())
        for name, scope in plan["scopes"].items():
            results["projects"][name] = scan(h, base, password, token, envfile, parent, name, source,
                [row["path"] for row in scope["files"]], commands, out / name)
            save(out / "result.json", results)
        if inventory(source) != plan["scopes"]:
            raise RuntimeError("source changed during scan")
        gaps = [name for name, result in results["projects"].items()
                if result["parser_diagnostics"] or any(
                    result["cppcheck_diagnostics"].get(key, 0)
                    for key in ("syntaxError", "internalError"))]
        results["status"] = "ANALYSIS_GAPS" if gaps else "SCANNED_WITH_RECORDED_FINDINGS"
        results["analysis_gaps"] = gaps
        if gaps:
            raise RuntimeError(f"analysis configuration requires correction for: {gaps}")
    except Exception as error:
        results["status"] = "FAILED"
        results["error"] = h.scrub(str(error), [password, token])
        raise
    finally:
        if token:
            try:
                request(h, base, password, "/api/user_tokens/revoke", {"name": "cix-cxx-repair"})
            except Exception:
                results["token_revocation"] = "failed; ephemeral server removed"
        if envfile.exists():
            envfile.unlink()
        log = subprocess.run(["docker", "logs", server], text=True, capture_output=True, timeout=30)
        (raw / "server.log").write_text(h.scrub(log.stdout + log.stderr, [password, token]))
        h.stop(server)
        save(out / "result.json", results)


def run(prepared: Path, out: Path) -> None:
    try:
        require_confirmation(SUMMARY)
    except RuntimeError:
        require_stopped_confirmation(SUMMARY)
    if out.exists():
        raise RuntimeError("refusing to overwrite a scan attempt; use a new output directory")
    s = load_module("cix_sonar_scheduler", HYGIENE / "schedule_scan.py")
    scheduler = s.WaveScheduler(ROOT, max_jobs=1, max_memory_bytes=s.AGGREGATE_MEMORY, max_temp_bytes=4_000_000_000)
    scheduler.state.mkdir(exist_ok=True)
    parent, anchor = "cix-cxx-hygiene.slice", "cix-cxx-hygiene-anchor"
    with scheduler._wave_lock_path().open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        leases = scheduler._lease_cores([{"physical_core": [s._core(cpu) for cpu in s.CPUS]}])
        try:
            assert_benchmark_idle()
            s._make_slice(parent, anchor)
            receipt = s._slice_receipt(parent); s._verify_slice(receipt)
            # Put this process (including Cppcheck) in the same aggregate slice.
            command = ["sudo", "-n", "systemd-run", "--uid", str(os.getuid()), "--gid", str(os.getgid()),
                       "--wait", "--pipe", "--collect", "--slice", parent, sys.executable, str(Path(__file__).resolve()),
                       "worker", "--prepared", str(prepared), "--out", str(out)]
            result = subprocess.run(command, timeout=21600)
            if out.exists():
                (out / "slice-receipt.txt").write_text(receipt)
            if result.returncode:
                raise RuntimeError("CXX scan failed; retain evidence and fix before claiming completion")
        finally:
            subprocess.run(["sudo", "-n", "systemctl", "stop", anchor], check=False, capture_output=True)
            for lease in leases:
                lease.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("provision", "prepare", "run", "worker"))
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--prepared", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.action == "provision":
        provision()
    elif args.action == "prepare":
        prepare(args.source.resolve(), args.out.resolve())
    elif args.action == "run":
        run(args.prepared.resolve(), args.out.resolve())
    else:
        # Worker may only be entered through the parent holding the global lease.
        parent = "cix-cxx-hygiene.slice"
        if parent not in Path('/proc/self/cgroup').read_text():
            raise RuntimeError("worker is outside the reserved aggregate slice")
        try:
            require_confirmation(SUMMARY)
        except RuntimeError:
            require_stopped_confirmation(SUMMARY)
        plan = json.loads((args.prepared / "plan.json").read_text())
        execute(args.prepared.resolve(), args.out.resolve(), Path(plan["source"]), parent)


if __name__ == "__main__":
    main()
