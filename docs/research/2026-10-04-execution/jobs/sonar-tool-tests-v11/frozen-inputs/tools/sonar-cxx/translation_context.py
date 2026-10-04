"""Validate the six recorded adapter contexts eligible for Cppcheck projection.

This module deliberately chooses no compiler options.  It validates a retained
successful compilation record before ``repair.py`` replays that record with
``-E``.  In particular, a path's lexical spelling and its resolved identity
are recorded separately: libtool's retained SquashFS commands contain a
double slash in the source operand, while the compilation database canonicalises
the same path in ``file``.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Any, Mapping


class TranslationContextError(ValueError):
    """A recorded translation unit cannot be projected faithfully."""


@dataclass(frozen=True)
class _Target:
    macro: str | None = None
    require_kernel_context: bool = False


# These are the only remaining adapter configuration gaps identified by the
# scan-v3 evidence.  Adding an adapter requires a new reviewed target entry;
# this is intentionally not a catch-all for difficult Cppcheck inputs.
PROJECTABLE_RELATIVES: Mapping[str, _Target] = {
    "rust/cix-native/adapters/gstreamer/src/gstcixstream.c": _Target(),
    "rust/cix-native/adapters/blosc2/src/cix_blosc2_adapter.c": _Target(),
    "rust/cix-native/adapters/squashfs/kernel/cix_profile_portable.c": _Target(
        "CIX_PORTABLE_PROFILE_SOURCE", True),
    "rust/cix-native/adapters/squashfs/userspace/squashfuse/cix_squashfuse_decode.c": _Target(
        "CIX_SQUASHFUSE_DECOMPRESS_SOURCE"),
    "rust/cix-native/adapters/squashfs/userspace/libsquashfs/cix_sqfsng_compressor.c": _Target(
        "CIX_SQFSNG_COMPRESSOR_SOURCE"),
    "rust/cix-native/adapters/squashfs/userspace/libsquashfs/cix_sqfsng_read_super.c": _Target(
        "CIX_SQFSNG_READ_SUPER_SOURCE"),
}


@dataclass(frozen=True)
class QualifiedInput:
    """An input whose identity and digest have already been receipt-bound."""

    recorded_path: str
    resolved_path: str
    sha256: str


@dataclass(frozen=True)
class TranslationContext:
    relative_source: str
    compiler: str
    directory: str
    source_operand: QualifiedInput
    macro_input: QualifiedInput | None
    forced_include_inputs: tuple[QualifiedInput, ...]


def _resolve(value: str, directory: Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = directory / path
    return path.resolve()


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _qualified(value: str, directory: Path, qualified_inputs: Mapping[str, str]) -> QualifiedInput:
    resolved = _resolve(value, directory)
    if not resolved.is_file():
        raise TranslationContextError("retained input is absent: " + value)
    expected = qualified_inputs.get(str(resolved))
    if not isinstance(expected, str) or len(expected) != 64:
        raise TranslationContextError("retained input has no receipt-bound digest: " + str(resolved))
    actual = _digest(resolved)
    if actual != expected:
        raise TranslationContextError("retained input digest differs from receipt binding: " + str(resolved))
    return QualifiedInput(value, str(resolved), actual)


def _macro_values(arguments: list[str], name: str) -> list[str]:
    values: list[str] = []
    index = 1
    while index < len(arguments):
        argument = arguments[index]
        if argument == "-D":
            if index + 1 >= len(arguments):
                raise TranslationContextError("-D has no value")
            candidate = arguments[index + 1]
            index += 1
        elif argument.startswith("-D"):
            candidate = argument[2:]
        else:
            index += 1
            continue
        if candidate.startswith(name + "="):
            value = candidate[len(name) + 1:]
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            values.append(value)
        index += 1
    return values


def _forced_includes(arguments: list[str]) -> list[str]:
    values: list[str] = []
    index = 1
    while index < len(arguments):
        argument = arguments[index]
        if argument == "-include":
            if index + 1 >= len(arguments):
                raise TranslationContextError("-include has no path")
            values.append(arguments[index + 1])
            index += 2
            continue
        if argument.startswith("-include"):
            raise TranslationContextError("attached -include operand is not an exact retained context")
        index += 1
    return values


def validate_translation_context(record: Mapping[str, Any], source_root: Path,
                                 qualified_inputs: Mapping[str, str]) -> TranslationContext:
    """Validate one of the six contexts against receipt-bound input digests.

    ``qualified_inputs`` must be built from the successful build/capture
    receipts by the caller.  Existence alone is therefore never treated as
    qualification.  The returned values are descriptive only; callers replay
    the original ``arguments`` and ``directory`` verbatim.
    """
    arguments = record.get("arguments")
    file_value = record.get("file")
    directory_value = record.get("directory")
    if not isinstance(arguments, list) or not arguments or not all(isinstance(item, str) for item in arguments):
        raise TranslationContextError("record requires a non-empty string arguments array")
    if not isinstance(file_value, str) or not isinstance(directory_value, str):
        raise TranslationContextError("record requires string file and directory fields")
    directory = Path(directory_value).resolve()
    source = _resolve(file_value, directory)
    try:
        relative = source.relative_to(source_root.resolve()).as_posix()
    except ValueError as error:
        raise TranslationContextError("source is outside the CIX source root: " + str(source)) from error
    target = PROJECTABLE_RELATIVES.get(relative)
    if target is None:
        raise TranslationContextError("source is not a reviewed projection target: " + relative)
    if arguments.count("-c") != 1:
        raise TranslationContextError("record requires exactly one -c operand: " + relative)
    operands = [argument for argument in arguments[1:]
                if not argument.startswith("-") and _resolve(argument, directory) == source]
    if len(operands) != 1:
        raise TranslationContextError("record requires one source operand with matching resolved identity: " + relative)
    source_input = QualifiedInput(operands[0], str(source), "")

    macro_input = None
    if target.macro is not None:
        values = _macro_values(arguments, target.macro)
        if len(values) != 1 or not values[0]:
            raise TranslationContextError("record requires one " + target.macro + " input")
        macro_input = _qualified(values[0], directory, qualified_inputs)

    include_values = _forced_includes(arguments)
    if target.require_kernel_context:
        if "-nostdinc" not in arguments or "-D__KERNEL__" not in arguments:
            raise TranslationContextError("kernel projection lacks its recorded compiler context")
        if not include_values:
            raise TranslationContextError("kernel projection lacks recorded forced headers")
    forced = tuple(_qualified(value, directory, qualified_inputs) for value in include_values)
    return TranslationContext(relative, arguments[0], str(directory), source_input, macro_input, forced)
