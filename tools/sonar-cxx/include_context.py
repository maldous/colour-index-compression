"""Rebase recorded compiler include operands onto read-only scanner mounts.

The helper is intentionally mechanical: it resolves only paths named by a
recorded command and reports every disposition.  It neither creates headers
nor supplies macros or declarations.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any


_DIRECTORY_FLAGS = ("-isystem", "-idirafter", "-iquote", "-I")
_FILE_FLAGS = ("-include", "-imacros")
_SYSROOT_FLAGS = ("--sysroot", "-isysroot")
_NON_PATH_VALUE_FLAGS = {"-D", "-U", "-x", "-std", "-stdlib", "-target", "--target", "-Xclang", "-Xpreprocessor"}


class IncludeContextError(ValueError):
    """A compiler record has malformed include-operand syntax."""


def _absolute(value: str, directory: Path) -> Path:
    if "$" in value or value.startswith("="):
        raise IncludeContextError("unresolved environment or sysroot-relative path operand: " + value)
    path = Path(value)
    return (path if path.is_absolute() else directory / path).resolve()


def _operand_at(arguments: list[str], index: int) -> tuple[str, str, str, int] | None:
    """Return flag, value, spelling, and value index for one recognised operand."""
    argument = arguments[index]
    for flag in (*_FILE_FLAGS, *_DIRECTORY_FLAGS, *_SYSROOT_FLAGS):
        if argument == flag:
            if index + 1 >= len(arguments):
                raise IncludeContextError(flag + " has no operand")
            return flag, arguments[index + 1], "two-token", index + 1
        if flag == "--sysroot" and argument.startswith("--sysroot="):
            return flag, argument[len("--sysroot="):], "joined-equals", index
        if argument.startswith(flag) and len(argument) > len(flag):
            return flag, argument[len(flag):], "joined", index
    return None


def _inside(path: Path, root: Path) -> bool:
    try:
        return path.is_relative_to(root)
    except ValueError:
        return False


def _external_disjoint(path: Path, source: Path) -> bool:
    """Avoid mounting the source tree itself or a broad ancestor of it."""
    return not _inside(path, source) and not _inside(source, path)


def _disposition(flag: str, resolved: Path) -> tuple[str, Path | None]:
    if resolved.is_dir():
        return "resolved-directory", resolved
    if flag in _DIRECTORY_FLAGS:
        # GCC commonly ignores an absent include directory.  Preserve that
        # actual command condition rather than treating it as a fabricated
        # header closure or rejecting otherwise useful compiler records.
        return "absent-ignored-include-directory", None
    return "absent-sysroot-directory", None


def _forced_file(value: str, directory: Path, search_roots: list[Path]) -> tuple[Path, str]:
    """Resolve only direct or explicit user-include candidates.

    Implicit compiler system directories are intentionally unavailable here.
    If none of the recorded user stages selects a file, closure is unknown and
    the caller fails closed instead of substituting a host header.
    """
    direct = _absolute(value, directory)
    if direct.is_file():
        return direct, "resolved-forced-file"
    for root in search_roots:
        candidate = (root / value).resolve()
        if candidate.is_file():
            return candidate, "resolved-forced-file-via-recorded-include-search"
    raise IncludeContextError("recorded forced include does not resolve to a file: " + value)


def _user_include_search_roots(operands: list[tuple[str, str, str, int]], directory: Path) -> list[Path]:
    """Return GCC quoted-include user stages, preserving order within stages.

    ``-idirafter`` is deliberately excluded because unknown implicit system
    roots precede it.  Do not deduplicate roots across the remaining flag
    classes: that would change the compiler's search ordering.  Implicit
    system roots are deliberately not guessed by this bounded mapping helper.
    """
    roots: list[Path] = []
    system_roots = {
        _absolute(value, directory) for flag, value, _, _ in operands
        if flag == "-isystem" and _absolute(value, directory).is_dir()
    }
    for expected_flag in ("-iquote", "-I", "-isystem"):
        for flag, value, _, _ in operands:
            if flag != expected_flag:
                continue
            resolved = _absolute(value, directory)
            # GCC ignores an -I directory that is also named by -isystem;
            # retaining it in the earlier stage would select a different
            # header context from the compiler.
            if expected_flag == "-I" and resolved in system_roots:
                continue
            if resolved.is_dir():
                roots.append(resolved)
    return roots


def _path_mapper(source: Path, mounts: list[tuple[Path, str]]):
    longest_first = sorted(mounts, key=lambda item: len(str(item[0])), reverse=True)

    def map_path(value: str, directory: Path) -> str:
        resolved = _absolute(value, directory)
        if _inside(resolved, source):
            return "/usr/src" + str(resolved)[len(str(source)):]
        for host, container in longest_first:
            if resolved == host or _inside(resolved, host):
                return container + str(resolved)[len(str(host)):]
        return value
    return map_path


def rebase_include_context(commands: list[dict[str, Any]], source: Path) -> tuple[list[dict[str, Any]], list[tuple[Path, str]], list[dict[str, Any]]]:
    """Return mapped rows, read-only mount roots, and per-operand evidence.

    The first two return values match the shape expected by existing
    ``containerize_commands`` callers.  The third is deliberately separate so
    a scan receipt can record resolved, absent, and forced-file dispositions.
    """
    source = source.resolve()
    candidates: set[Path] = set()
    parsed_rows: list[tuple[dict[str, Any], Path, list[dict[str, Any]]]] = []
    for row in commands:
        if not isinstance(row.get("directory"), str) or not isinstance(row.get("file"), str):
            raise IncludeContextError("record requires string directory and file fields")
        arguments = row.get("arguments")
        if not isinstance(arguments, list) or not all(isinstance(value, str) for value in arguments):
            raise IncludeContextError("record requires a string arguments array")
        directory = Path(row["directory"])
        if not directory.is_absolute():
            raise IncludeContextError("recorded compiler directory must be absolute")
        directory = directory.resolve()
        if directory.is_dir() and _external_disjoint(directory, source):
            candidates.add(directory)
        raw_operands: list[tuple[str, str, str, int]] = []
        index = 0
        while index < len(arguments):
            parsed = _operand_at(arguments, index)
            if parsed is None:
                index += 1
                continue
            raw_operands.append(parsed)
            index += 2 if parsed[2] == "two-token" else 1
        search_roots = _user_include_search_roots(raw_operands, directory)
        operands: list[dict[str, Any]] = []
        for flag, value, spelling, value_index in raw_operands:
            if flag in _FILE_FLAGS:
                resolved, disposition = _forced_file(value, directory, search_roots)
                mount_root = resolved.parent
            else:
                resolved = _absolute(value, directory)
                disposition, mount_root = _disposition(flag, resolved)
            if mount_root is not None and _external_disjoint(mount_root, source):
                candidates.add(mount_root)
            operands.append({
                "flag": flag, "original": value, "spelling": spelling,
                "argument_index": value_index, "resolved": str(resolved),
                "disposition": disposition, "mount_root": str(mount_root) if mount_root else None,
            })
        parsed_rows.append((row, directory, operands))

    roots = sorted(candidates, key=lambda path: str(path))
    mounts = [(root, f"/cix-external/{index}") for index, root in enumerate(roots)]
    map_path = _path_mapper(source, mounts)
    mapped_rows: list[dict[str, Any]] = []
    evidence: list[dict[str, Any]] = []
    for row, directory, operands in parsed_rows:
        rewritten = list(row["arguments"])
        for operand in operands:
            index = operand["argument_index"]
            if operand["mount_root"] is not None:
                # A bare forced name may have been found through a recorded
                # include directory.  Rebase that selected file, not the
                # original cwd-relative spelling.
                mapped = map_path(operand["resolved"], directory)
                if operand["spelling"] == "two-token":
                    rewritten[index] = mapped
                elif operand["spelling"] == "joined-equals":
                    rewritten[index] = "--sysroot=" + mapped
                else:
                    rewritten[index] = operand["flag"] + mapped
                operand["mapped"] = mapped
            else:
                operand["mapped"] = None
            evidence.append({"source": row["file"], "directory": str(directory), "mount_read_only": True,
                             "forced_fallback_limit": "direct file then explicit user include stages; no implicit system roots",
                             **operand})
        source_file = _absolute(row["file"], directory)
        non_path_values = {index + 1 for index, argument in enumerate(rewritten)
                           if argument in _NON_PATH_VALUE_FLAGS and index + 1 < len(rewritten)}
        operand_values = {operand["argument_index"] for operand in operands}
        for index, argument in enumerate(rewritten):
            if index in operand_values or index in non_path_values or argument.startswith("-"):
                continue
            if argument.startswith("/"):
                rewritten[index] = map_path(argument, directory)
            else:
                try:
                    if _absolute(argument, directory) == source_file:
                        rewritten[index] = map_path(argument, directory)
                except IncludeContextError:
                    # A non-path token such as a paired macro value remains
                    # opaque.  Only a recognised operand may fail closure.
                    continue
        mapped_rows.append({**row, "file": map_path(row["file"], directory),
                            "directory": map_path(row["directory"], directory), "arguments": rewritten})
    return mapped_rows, mounts, evidence
