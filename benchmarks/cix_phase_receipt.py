#!/usr/bin/env python3
"""Retain the actual child status before a transient service is collected."""
import json
import hashlib
import os
from pathlib import Path
import subprocess
import sys


def main(argv):
    if len(argv) == 4 and argv[1] == "--command-file":
        source = Path(argv[2])
        if not source.is_absolute() or not source.is_file():
            raise SystemExit("command file must be an absolute regular file")
        data = source.read_bytes()
        if hashlib.sha256(data).hexdigest() != argv[3]:
            raise SystemExit("command file checksum mismatch")
        command = json.loads(data)
        if (not isinstance(command, list) or not command
                or any(not isinstance(arg, str) or "\0" in arg for arg in command)
                or not command[0]):
            raise SystemExit("invalid command argument list")
    elif len(argv) >= 3 and argv[1] == "--":
        command = argv[2:]
    else:
        raise SystemExit("usage: cix_phase_receipt.py RECEIPT -- COMMAND [ARG...]")
    receipt = Path(argv[0])
    try:
        status = subprocess.run(command, check=False).returncode
        error = None
    except OSError as exc:
        status, error = 127, str(exc)
    value = {"command": command, "child_exit_code": status, "launch_error": error}
    temporary = receipt.with_name(receipt.name + ".tmp")
    with temporary.open("w") as stream:
        json.dump(value, stream, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(receipt)
    return status if status >= 0 else 128 - status


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
