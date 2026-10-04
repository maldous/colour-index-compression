#!/usr/bin/env python3
"""Static production-runtime hygiene receipt; it never imports codecs or runs them."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

# These fragments denote executable-path coupling, rather than ordinary prose.
FORBIDDEN_PATH_FRAGMENTS = ("benchmark-work/", "/benchmarks/", "/results/", "/research/")
FORBIDDEN_IMPORT_ROOTS = {"benchmarks", "cix"}


def _module_name(root: Path, source: Path) -> str:
    relative = source.relative_to(root).with_suffix("")
    parts = list(relative.parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _targets(node: ast.ImportFrom, current: str) -> list[str]:
    package = current.split(".")[:-1]
    if node.level - 1 > len(package):
        return []
    package = package[:len(package) - (node.level - 1)]
    if node.module:
        return [".".join(package + node.module.split("."))]
    return [".".join(package + [alias.name]) for alias in node.names]


def _digest(files: list[Path], root: Path) -> str:
    digest = hashlib.sha256()
    for source in files:
        digest.update(source.relative_to(root).as_posix().encode() + b"\0")
        digest.update(source.read_bytes())
    return digest.hexdigest()


def _docstring_nodes(tree: ast.AST) -> set[int]:
    nodes: set[int] = set()
    for owner in ast.walk(tree):
        body = getattr(owner, "body", None)
        if isinstance(body, list) and body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
            if isinstance(body[0].value.value, str):
                nodes.add(id(body[0].value))
    return nodes


def _is_forbidden_import(target: str | None) -> bool:
    if not target:
        return False
    root = target.split(".", 1)[0]
    return root in FORBIDDEN_IMPORT_ROOTS


def _append_missing_imports(report, node, current, modules, relative):
    if not (isinstance(node, ast.ImportFrom) and node.level and node.module):
        return
    for target in _targets(node, current):
        present = target in modules or any(module.startswith(target + ".") for module in modules)
        if target and not present:
            report["unresolved_local_imports"].append({"file": relative, "line": node.lineno, "target": target})


def _append_forbidden_import(report, node, relative):
    if isinstance(node, ast.Import):
        targets = [alias.name for alias in node.names]
    elif isinstance(node, ast.ImportFrom):
        targets = [node.module]
    else:
        return
    for target in targets:
        if _is_forbidden_import(target):
            report["forbidden_runtime_coupling"].append({"file": relative, "line": node.lineno, "kind": "import", "value": target})


def _append_path_constant(report, node, docstrings, relative):
    if not (isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstrings):
        return
    if any(fragment in node.value for fragment in FORBIDDEN_PATH_FRAGMENTS):
        report["forbidden_runtime_coupling"].append({"file": relative, "line": node.lineno, "kind": "path-constant", "value": node.value})


def _append_exception(report, node, relative):
    if not isinstance(node, ast.ExceptHandler):
        return
    broad = node.type is None or (isinstance(node.type, ast.Name) and node.type.id in {"Exception", "BaseException"})
    if not broad:
        return
    item = {"file": relative, "line": node.lineno, "type": None if node.type is None else node.type.id}
    report["broad_exception_handlers"].append(item)
    if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
        report["silent_exception_handlers"].append(item)


def _inspect_source(root, source, modules, report):
    text = source.read_text(encoding="utf-8"); relative = source.relative_to(root).as_posix()
    try:
        tree = ast.parse(text, filename=str(source)); compile(tree, str(source), "exec")
    except SyntaxError as error:
        report["syntax_errors"].append({"file": relative, "line": error.lineno, "message": error.msg})
        return
    current = _module_name(root, source); docstrings = _docstring_nodes(tree)
    for node in ast.walk(tree):
        _append_missing_imports(report, node, current, modules, relative)
        _append_forbidden_import(report, node, relative)
        _append_path_constant(report, node, docstrings, relative)
        _append_exception(report, node, relative)


def inspect(root: Path) -> dict[str, Any]:
    if root.name != "cix_runtime" or not (root / "__init__.py").is_file():
        raise ValueError("--runtime must name the production cix_runtime package directory")
    sources = sorted(root.rglob("*.py")); modules = {_module_name(root, source) for source in sources}
    report: dict[str, Any] = {
        "scope": "production-runtime-package-only", "root": str(root), "files": len(sources), "tree_sha256": _digest(sources, root),
        "syntax_errors": [], "forbidden_runtime_coupling": [], "unresolved_local_imports": [],
        "broad_exception_handlers": [], "silent_exception_handlers": [],
    }
    for source in sources:
        _inspect_source(root, source, modules, report)
    for key in ("syntax_errors", "forbidden_runtime_coupling", "unresolved_local_imports", "broad_exception_handlers", "silent_exception_handlers"):
        report[key].sort(key=lambda item: (item["file"], item.get("line", 0), str(item.get("target", item.get("value", "")))))
    report["pass"] = not any(report[key] for key in ("syntax_errors", "forbidden_runtime_coupling", "unresolved_local_imports"))
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", type=Path, required=True, help="production runtime/cix_runtime package directory")
    parser.add_argument("--json", type=Path, required=True)
    args = parser.parse_args()
    report = inspect(args.runtime.resolve())
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
