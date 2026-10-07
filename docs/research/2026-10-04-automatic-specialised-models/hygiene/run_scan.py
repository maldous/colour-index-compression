#!/usr/bin/env python3
"""Root-scheduled final Sonar gate. Uses only local pinned images; never pulls.

The caller must hold the global WaveScheduler lease and provide its cgroup parent.
This harness starts at most a 4 GiB server and one 1 GiB scanner concurrently.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request

SERVER_IMAGE = "sonarqube@sha256:4905574ab8584dcac1a06c01cdc43a4ce9e369723ac4a7ab1d029c1bf71e6fe9"
SCANNER_IMAGE = "sonarsource/sonar-scanner-cli@sha256:a3f4215076706c95a17a68c19322ee916e40a3acd081a8c1a1e839e0194afa57"
CPUS = "8,10,12,14"
SERVER_MEMORY = 4 * 1024**3
SCANNER_MEMORY = 1 * 1024**3
PORT = 9016


def run(command: list[str], *, timeout: int = 120, **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(command, check=True, text=True, timeout=timeout, **kwargs)


def sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def source_tree(root: Path) -> tuple[str, list[dict[str, str]]]:
    ignored = {"target", ".scannerwork", ".sonar", "__pycache__"}
    records: list[dict[str, str]] = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if path.is_dir() or any(part in ignored for part in relative.parts):
            continue
        if path.is_symlink() or not path.is_file():
            raise RuntimeError(f"unsupported staged source entry: {path}")
        records.append({"path": relative.as_posix(), "sha256": sha256(path)})
    encoded = json.dumps(records, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest(), records


def api(base: str, path: str, user: str, password: str, data: bytes | None = None) -> dict:
    request = urllib.request.Request(base + path, data=data, method="POST" if data else "GET")
    request.add_header("Authorization", "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode())
    if data:
        request.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urllib.request.urlopen(request, timeout=20) as response:
        body = response.read()
    return json.loads(body) if body else {}


def scrub(text: str, values: list[str | None]) -> str:
    for value in values:
        if value:
            text = text.replace(value, "[REDACTED]").replace(urllib.parse.quote_plus(value), "[REDACTED]")
    return text


def image_receipt(image: str) -> str:
    """Require the exact image to exist locally; intentionally no docker pull."""
    return run(["docker", "image", "inspect", image], timeout=30, capture_output=True).stdout


def inspect_container(name: str, expected_memory: int, cgroup_parent: str) -> dict:
    item = json.loads(run(["docker", "inspect", name], capture_output=True).stdout)[0]
    host = item.get("HostConfig", {})
    if host.get("Memory") != expected_memory or host.get("MemorySwap") != expected_memory:
        raise RuntimeError(f"{name}: memory/swap limit receipt mismatch")
    if host.get("CpusetCpus") != CPUS or host.get("CpuQuota") != 400000 or host.get("CpuPeriod") != 100000:
        raise RuntimeError(f"{name}: CPU limit receipt mismatch")
    if host.get("CgroupParent") != cgroup_parent:
        raise RuntimeError(f"{name}: cgroup parent receipt mismatch")
    return item


def docker_run(name: str, image: str, memory: int, parent: str, options: list[str], command: list[str] | None = None) -> None:
    run([
        "docker", "run", "-d", "--name", name, "--hostname", name,
        "--cgroup-parent", parent, "--cpuset-cpus", CPUS, "--cpu-period", "100000", "--cpu-quota", "400000",
        "--memory", str(memory), "--memory-swap", str(memory), *options, image, *(command or []),
    ], timeout=60)
    inspect_container(name, memory, parent)


def stop(name: str) -> None:
    subprocess.run(["docker", "rm", "-f", name], check=False, capture_output=True, text=True, timeout=30)


def wait_server(base: str, password: str) -> None:
    for _ in range(90):
        try:
            if api(base, "/api/system/status", "admin", "admin").get("status") == "UP":
                break
        except Exception:
            pass
        time.sleep(2)
    else:
        raise RuntimeError("Sonar server did not become ready")
    api(base, "/api/users/change_password", "admin", "admin", urllib.parse.urlencode({
        "login": "admin", "previousPassword": "admin", "password": password,
    }).encode())



def containerize_compile_commands(path: Path, source: Path) -> bytes:
    """Rebase a scheduler-generated database for the read-only /usr/src mount."""
    entries = json.loads(path.read_text())
    if not isinstance(entries, list):
        raise RuntimeError("compile_commands.json must be an array")
    host = str(source.resolve())
    def replace(value):
        if isinstance(value, str):
            return value.replace(host, "/usr/src")
        if isinstance(value, list):
            return [replace(item) for item in value]
        if isinstance(value, dict):
            return {key: replace(item) for key, item in value.items()}
        return value
    return (json.dumps(replace(entries), indent=2) + "\n").encode()

def scan_project(*, name: str, image: str, parent: str, envfile: Path, source: Path, out: Path,
                 properties: Path, token_values: list[str | None]) -> str:
    scanner = f"cix-hygiene-scanner-{name}"
    try:
        docker_run(scanner, image, SCANNER_MEMORY, parent, [
            "--network", "host", "--tmpfs", "/tmp:rw,exec,size=512m",
            "--env", "SONAR_USER_HOME=/tmp/.sonar", "--env", "SONAR_SCANNER_JAVA_OPTS=-Xmx512m",
            "--env-file", str(envfile), "-v", f"{source}:/usr/src:ro", "-v", f"{out}:/out",
            "-w", "/usr/src", "--entrypoint", "sh",
        ], ["-c", "sonar-scanner -Dsonar.projectBaseDir=/usr/src -Dproject.settings=/out/properties"])
        code = run(["docker", "wait", scanner], timeout=900, capture_output=True).stdout.strip()
        log = subprocess.run(["docker", "logs", scanner], check=False, capture_output=True, text=True, timeout=30)
        (out / "scanner.log").write_text(scrub(log.stdout + log.stderr, token_values))
        (out / "scanner-exit.txt").write_text(code + "\n")
        if code != "0":
            raise RuntimeError(f"Sonar scanner failed for {name}")
        task = re.search(r"api/ce/task\?id=([^\s]+)", log.stdout + log.stderr)
        if not task:
            raise RuntimeError(f"Sonar scanner did not report a compute task for {name}")
        return task.group(1)
    finally:
        stop(scanner)


def collect(base: str, key: str, task: str, password: str, out: Path) -> None:
    """Wait for this submitted analysis before treating issues/gate as final."""
    for _ in range(90):
        receipt = api(base, f"/api/ce/task?id={urllib.parse.quote(task)}", "admin", password)
        status = receipt.get("task", {}).get("status")
        if status in {"SUCCESS", "FAILED", "CANCELED"}:
            break
        time.sleep(1)
    else:
        raise RuntimeError(f"compute engine did not finish for {key}")
    (out / "ce-task.json").write_text(json.dumps(receipt, indent=2) + "\n")
    if status != "SUCCESS":
        raise RuntimeError(f"compute engine failed for {key}: {status}")
    issues = api(base, f"/api/issues/search?componentKeys={urllib.parse.quote(key)}&resolved=false&ps=500", "admin", password)
    total = issues["paging"]["total"]
    for page in range(2, (total + 499) // 500 + 1):
        issues["issues"].extend(api(base, f"/api/issues/search?componentKeys={urllib.parse.quote(key)}&resolved=false&ps=500&p={page}", "admin", password)["issues"])
    gate = api(base, f"/api/qualitygates/project_status?projectKey={urllib.parse.quote(key)}", "admin", password)
    (out / "issues.json").write_text(json.dumps(issues, indent=2) + "\n")
    (out / "quality-gate.json").write_text(json.dumps(gate, indent=2) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lease", type=Path, required=True)
    parser.add_argument("--native-source", type=Path, required=True)
    parser.add_argument("--runtime-source", type=Path, required=True)
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--clippy-json", type=Path, required=True)
    parser.add_argument("--cgroup-parent", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--compile-commands", type=Path)
    args = parser.parse_args()
    lease = json.loads(args.lease.read_text())
    if lease.get("status") != "ACTIVE" or lease.get("reserved_cpus") != [8, 10, 12, 14]:
        raise RuntimeError("active root lease for CPUs 8,10,12,14 required")
    if lease.get("cgroup_parent") != args.cgroup_parent or lease.get("aggregate_memory_bytes") != SERVER_MEMORY + SCANNER_MEMORY:
        raise RuntimeError("lease must bind the supplied cgroup parent and 4 GiB + 1 GiB aggregate budget")
    if args.out.exists():
        raise RuntimeError("refusing to overwrite hygiene evidence")
    freeze = json.loads(args.freeze.read_text())
    native = args.native_source.resolve(); runtime = args.runtime_source.resolve()
    native_tree, native_files = source_tree(native)
    runtime_tree, runtime_files = source_tree(runtime)
    expected = {project["key"]: project["source_tree_sha256"] for project in freeze["projects"]}
    if expected.get("cix-0.1-native-rust-final") != native_tree or expected.get("cix-0.1-runtime-python-final") != runtime_tree:
        raise RuntimeError("staged source differs from frozen manifest")
    if not args.clippy_json.is_file():
        raise RuntimeError("fresh root-scheduled Clippy JSON is required")
    # This does not pull: missing local images are an immediate reproducibility failure.
    server_image = image_receipt(SERVER_IMAGE); scanner_image = image_receipt(SCANNER_IMAGE)
    args.out.mkdir(parents=True); raw = args.out / "raw"; raw.mkdir()
    (raw / "server-image-inspect.json").write_text(server_image)
    (raw / "scanner-image-inspect.json").write_text(scanner_image)
    password = "Aa1!" + secrets.token_urlsafe(32); token: str | None = None; envfile: Path | None = None
    server = "cix-hygiene-sonarqube"
    base = f"http://127.0.0.1:{PORT}"
    results: dict[str, object] = {"native_tree": native_tree, "runtime_tree": runtime_tree, "native_files": native_files, "runtime_files": runtime_files, "clippy_sha256": sha256(args.clippy_json), "projects": {}}
    try:
        docker_run(server, SERVER_IMAGE, SERVER_MEMORY, args.cgroup_parent, [
            "-p", f"127.0.0.1:{PORT}:9000",
            "--tmpfs", "/opt/sonarqube/data:rw,uid=1000,gid=0,size=1g",
            "--tmpfs", "/opt/sonarqube/logs:rw,uid=1000,gid=0,size=128m",
            "--tmpfs", "/opt/sonarqube/temp:rw,uid=1000,gid=0,size=1536m",
        ])
        wait_server(base, password)
        token = api(base, "/api/user_tokens/generate", "admin", password, b"name=cix-final-hygiene")["token"]
        envfile = raw / ".scanner-env"; envfile.write_text(f"SONAR_HOST_URL={base}\nSONAR_TOKEN={token}\n"); os.chmod(envfile, 0o600)
        for key, source in (("cix-0.1-native-rust-final", native), ("cix-0.1-runtime-python-final", runtime)):
            project = next(item for item in freeze["projects"] if item["key"] == key)
            project_out = args.out / key; project_out.mkdir()
            props = project_out / "properties"
            props.write_text((args.freeze.parent / f"{key}.properties").read_text())
            if key.endswith("rust-final"):
                with props.open("a") as handle:
                    handle.write("sonar.rust.clippy.enabled=false\nsonar.rust.clippyReport.reportPaths=/out/clippy.jsonl\n")
                (project_out / "clippy.jsonl").write_bytes(args.clippy_json.read_bytes())
            task = scan_project(name="rust" if key.endswith("rust-final") else "python", image=SCANNER_IMAGE, parent=args.cgroup_parent, envfile=envfile, source=source, out=project_out, properties=props, token_values=[password, token])
            collect(base, key, task, password, project_out)
            results["projects"][key] = {"required": project["required"], "status": "scanned"}
        languages = api(base, "/api/languages/list", "admin", password)
        cpp = next(item for item in freeze["projects"] if item["key"] == "cix-0.1-native-cpp-first-party-final")
        if any(language.get("key") == "cpp" for language in languages.get("languages", [])) and args.compile_commands and args.compile_commands.is_file():
            project_out = args.out / cpp["key"]; project_out.mkdir(); props = project_out / "properties"
            props.write_text((args.freeze.parent / f"{cpp['key']}.properties").read_text() + f"sonar.cfamily.compile-commands=/out/compile_commands.json\n")
            (project_out / "compile_commands.json").write_bytes(containerize_compile_commands(args.compile_commands, native))
            task = scan_project(name="cpp", image=SCANNER_IMAGE, parent=args.cgroup_parent, envfile=envfile, source=native, out=project_out, properties=props, token_values=[password, token])
            collect(base, cpp["key"], task, password, project_out); results["projects"][cpp["key"]] = {"required": cpp["required"], "status": "scanned"}
        else:
            results["projects"][cpp["key"]] = {"required": cpp["required"], "status": "not-scanned", "reason": "CFamily language or fresh compile commands unavailable"}
        (raw / "languages.json").write_text(json.dumps(languages, indent=2) + "\n")
        (args.out / "manifest.json").write_text(json.dumps(results, indent=2) + "\n")
    finally:
        if token:
            try:
                api(base, "/api/user_tokens/revoke", "admin", password, b"name=cix-final-hygiene")
                (raw / "token-lifecycle.txt").write_text("revocation=success\n")
            except Exception:
                (raw / "token-lifecycle.txt").write_text("revocation=failed\n")
        if envfile and envfile.exists(): envfile.unlink()
        stop(server)


if __name__ == "__main__":
    main()
