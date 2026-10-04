#!/usr/bin/python3
import json, os, sys
from pathlib import Path
compiler = "/usr/bin/c++" if Path(sys.argv[0]).name.endswith("cxx") else "/usr/bin/cc"
record = {"directory": os.getcwd(), "arguments": [compiler, *sys.argv[1:]]}
path = Path(__file__).resolve().parent / "compiler-invocations.jsonl"
fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
os.write(fd, (json.dumps(record) + "\n").encode())
os.close(fd)
os.execv(compiler, [compiler, *sys.argv[1:]])
