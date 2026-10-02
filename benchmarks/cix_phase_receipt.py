#!/usr/bin/env python3
"""Retain the actual child status before a transient service is collected."""
import json
import os
from pathlib import Path
import subprocess
import sys


def main(argv):
    if len(argv) < 3 or argv[1] != "--":
        raise SystemExit("usage: cix_phase_receipt.py RECEIPT -- COMMAND [ARG...]")
    receipt, command = Path(argv[0]), argv[2:]
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
