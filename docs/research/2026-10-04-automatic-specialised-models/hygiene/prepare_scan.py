#!/usr/bin/env python3
"""Write hash-bound Sonar property files after a root scheduler has frozen sources.

This utility never starts a build, test, Docker container, or scanner.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def digest_tree(root: Path) -> tuple[str, list[dict[str, str]]]:
    ignored = {"target", ".scannerwork", ".sonar", "__pycache__"}
    records: list[dict[str, str]] = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(part in ignored for part in relative.parts) or path.is_dir():
            continue
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"unsupported source entry: {path}")
        with path.open("rb") as handle:
            content_hash = hashlib.file_digest(handle, "sha256").hexdigest()
        records.append({"path": relative.as_posix(), "sha256": content_hash})
    encoded = json.dumps(records, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest(), records


def properties(project: dict[str, object], revision: str) -> str:
    pairs = [("sonar.projectKey", project["key"]), ("sonar.sources", project["sources"]), ("sonar.exclusions", project["exclusions"]), ("sonar.scm.revision", revision), ("sonar.working.directory", "/tmp/.scannerwork")]
    if project.get("tests"):
        pairs.append(("sonar.tests", project["tests"]))
    if project.get("inclusions"):
        pairs.append(("sonar.inclusions", project["inclusions"]))
    if project.get("test_inclusions"):
        pairs.append(("sonar.test.inclusions", project["test_inclusions"]))
    if project.get("python_version"):
        pairs.append(("sonar.python.version", project["python_version"]))
    return "".join(f"{key}={value}\n" for key, value in pairs)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    spec = json.loads(args.spec.read_text())
    output = args.out.resolve()
    output.mkdir(parents=True, exist_ok=False)
    manifest: dict[str, object] = {"status": "prepared", "projects": []}
    for project in spec["sonar_projects"]:
        root = Path(project["root"]).resolve()
        tree, files = digest_tree(root)
        name = project["key"]
        (output / f"{name}.properties").write_text(properties(project, tree))
        manifest["projects"].append({"key": name, "root": str(root), "source_tree_sha256": tree, "files": files, "required": project["required"]})
    (output / "freeze-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
