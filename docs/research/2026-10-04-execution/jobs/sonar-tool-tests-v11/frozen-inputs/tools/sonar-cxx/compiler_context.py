"""Derive one C/C++ compiler context from one recorded successful TU command.

The caller executes the returned argv in its own bounded evidence sandbox.  The
probe deliberately preprocesses *empty stdin*: macro output from the final TU
would be affected by include guards and is not a reliable header context.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any


class CompilerContextError(ValueError):
    """The retained argv cannot safely be converted to an empty-input probe."""


_VALUE_OUTPUT_FLAGS = {"-o", "-MF", "-MT", "-MQ", "-MJ", "--dependency-file"}
_DROP_FLAGS = {"-c", "-MD", "-MMD", "-MP", "-MM", "-M", "-MG"}
_SIDE_EFFECT_FLAGS = {"-save-temps", "-ftime-trace", "-fprofile-arcs", "--coverage"}
_WRAPPERS = {"ccache", "sccache", "distcc", "icecc", "env", "xcrun"}
_SEMANTIC_VALUE_FLAGS = {"-D", "-U", "-I", "-isystem", "-iquote", "-include", "-imacros",
                         "-isysroot", "--sysroot", "-std", "-stdlib", "-target", "--target"}


def _inferred_language(source: Path) -> str:
    if source.suffix == ".c":
        return "c"
    if source.suffix.lower() in {".cc", ".cpp", ".cxx", ".c++"} or source.suffix == ".C":
        return "c++"
    raise CompilerContextError("unsupported or ambiguous TU suffix: " + source.suffix)


def _same_path(value: str, source: Path, directory: Path) -> bool:
    try:
        path = Path(value)
        if not path.is_absolute():
            path = directory / path
        return path.resolve() == source.resolve()
    except OSError:
        return False


def prepare_argv(record: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
    """Return an empty-input macro/include probe from one unambiguous TU argv.

    ``record`` must contain the exact successful ``arguments``, ``file``, and
    ``directory`` fields retained by the compiler receipt.  No flags are
    invented; semantic options are retained in their original order.
    """
    arguments = record.get("arguments")
    directory = record.get("directory")
    file_value = record.get("file")
    if not isinstance(arguments, list) or not arguments or not all(isinstance(x, str) for x in arguments):
        raise CompilerContextError("record requires a non-empty string arguments array")
    if not isinstance(directory, str) or not isinstance(file_value, str):
        raise CompilerContextError("record requires string directory and file fields")
    working_directory = Path(directory).resolve()
    source = Path(file_value)
    if not source.is_absolute():
        source = working_directory / source
    source = source.resolve()
    compiler = arguments[0]
    if not compiler or Path(compiler).name in _WRAPPERS:
        raise CompilerContextError("compiler wrappers are not an unambiguous compiler identity")

    retained: list[str] = []
    removed: list[str] = []
    sources = 0
    explicit_language = False
    index = 1
    while index < len(arguments):
        arg = arguments[index]
        if _same_path(arg, source, working_directory):
            sources += 1
            removed.append(arg)
        elif arg == "-x":
            if index + 1 >= len(arguments) or arguments[index + 1] not in {"c", "c++"}:
                raise CompilerContextError("unsupported explicit compiler language")
            retained.extend((arg, arguments[index + 1]))
            explicit_language = True
            index += 1
        elif arg.startswith("-x") and len(arg) > 2:
            if arg[2:] not in {"c", "c++"}:
                raise CompilerContextError("unsupported explicit compiler language")
            retained.append(arg)
            explicit_language = True
        elif arg in _VALUE_OUTPUT_FLAGS:
            if index + 1 >= len(arguments):
                raise CompilerContextError(f"output flag without value: {arg}")
            removed.extend((arg, arguments[index + 1]))
            index += 1
        elif any(arg.startswith(flag + "=") for flag in _VALUE_OUTPUT_FLAGS if flag.startswith("--")):
            removed.append(arg)
        elif any(arg.startswith(flag) and len(arg) > len(flag) for flag in ("-o", "-MF", "-MT", "-MQ", "-MJ")):
            removed.append(arg)
        elif arg in _DROP_FLAGS:
            removed.append(arg)
        elif arg in _SEMANTIC_VALUE_FLAGS:
            if index + 1 >= len(arguments):
                raise CompilerContextError(f"semantic flag without value: {arg}")
            retained.extend((arg, arguments[index + 1]))
            index += 1
        elif (arg in _SIDE_EFFECT_FLAGS or arg.startswith(("-save-temps", "-ftime-trace", "-fprofile-generate", "-fprofile-use", "-fprofile-dir=", "-fplugin", "-Wp,"))
              or arg in {"-Xclang", "-Xpreprocessor"}):
            raise CompilerContextError(f"unrecognized probe side effect: {arg}")
        elif arg in ("-E", "-S"):
            raise CompilerContextError(f"recorded argv is not a compile TU command: {arg}")
        elif arg.startswith("-"):
            retained.append(arg)
        else:
            raise CompilerContextError("unexpected positional operand: " + arg)
        index += 1
    if sources != 1:
        raise CompilerContextError(f"expected exactly one recorded TU source, found {sources}")
    # stdin avoids any final-TU include guards.  -dM emits the actual builtin
    # macro context after the retained compiler options have been applied.
    language = None if explicit_language else _inferred_language(source)
    argv = [compiler, *retained, *( [] if language is None else ["-x", language]), "-E", "-dM", "-v", "-"]
    return argv, {"compiler": compiler, "source": str(source), "directory": str(working_directory),
                  "recorded_argv": list(arguments), "removed": removed, "retained": retained,
                  "empty_input": True, "language": language or "recorded-explicit",
                  "execution_requirement": "caller must use a read-only bounded sandbox"}


def parse_compiler_output(stdout: str, stderr: str) -> dict[str, Any]:
    """Parse raw ``-dM`` macros and verbose system include search paths only."""
    if not isinstance(stdout, str) or not isinstance(stderr, str):
        raise CompilerContextError("compiler output must be text")
    macros: list[dict[str, str]] = []
    for line in stdout.splitlines():
        if not line.startswith("#define "):
            continue
        tail = line[len("#define "):]
        name, sep, value = tail.partition(" ")
        if not name:
            raise CompilerContextError("empty macro name in compiler output")
        macros.append({"name": name, "value": value if sep else "", "raw": line})
    if not macros:
        raise CompilerContextError("compiler produced no -dM macro definitions")
    paths: list[str] = []
    in_search = False
    for line in stderr.splitlines():
        stripped = line.strip()
        if stripped == "#include <...> search starts here:":
            in_search = True
            continue
        if in_search and stripped == "End of search list.":
            break
        if in_search and stripped:
            # GCC/Clang may annotate a path with "(framework directory)".
            paths.append(stripped.removesuffix(" (framework directory)"))
    if not paths:
        raise CompilerContextError("compiler verbose output has no system include search list")
    return {"macros": macros, "system_include_paths": paths,
            "raw_macro_count": len(macros), "preserves_compiler_macros": True,
            "does_not_infer_header_guard_macros": True}
