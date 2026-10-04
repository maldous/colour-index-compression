"""Verify an official SDK package while retaining only required reader source."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile
import threading
import urllib.request

assert os.environ.get("CIX_RELEASE_LEASE") == "1"
root = Path(__file__).resolve().parents[5]
out = root / "benchmark-work/native-rc-check-v1/kernel-source-v3"
out.mkdir()
url = "https://archive.ubuntu.com/ubuntu/pool/main/l/linux/linux-source-6.8.0_6.8.0-142.142_all.deb"
expected_sha = "44fedf5db02cfae6d21cd9682a90f37cfb998711732436218031aa8ea462fd59"
expected_size = 357053416
digest = hashlib.sha256()
size = 0
errors = []
files = {}
process = subprocess.Popen(["dpkg-deb", "--fsys-tarfile", "-"], stdin=subprocess.PIPE,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def download():
    global size
    try:
        with (root / "benchmark-work/native-rc-check-v1/linux-source-6.8.0-142.142.deb").open("rb") as response:
            while block := response.read(1 << 20):
                size += len(block)
                if size > expected_size:
                    raise RuntimeError("package exceeded index size")
                digest.update(block)
                process.stdin.write(block)
    except BaseException as error:
        errors.append(str(error))
    finally:
        process.stdin.close()

worker = threading.Thread(target=download)
worker.start()
try:
    with tarfile.open(fileobj=process.stdout, mode="r|") as outer:
        for package_member in outer:
            if not package_member.name.endswith("linux-source-6.8.0.tar.bz2"):
                continue
            stream = outer.extractfile(package_member)
            with tarfile.open(fileobj=stream, mode="r|bz2") as inner:
                for member in inner:
                    parts = Path(member.name).parts
                    if "fs" not in parts:
                        continue
                    at = parts.index("fs")
                    if parts[at:at + 2] != ("fs", "squashfs"):
                        continue
                    if not member.isfile():
                        continue
                    relative = Path(*parts[at:])
                    if ".." in relative.parts or member.size > 1 << 20:
                        raise RuntimeError("unexpected reader member")
                    data = inner.extractfile(member).read()
                    target = out / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(data)
                    files[str(relative)] = hashlib.sha256(data).hexdigest()
            stream.close()
    process.stdout.read()
    worker.join()
    stderr = process.stderr.read().decode(errors="replace")
    code = process.wait()
    assert code == 0, stderr
    assert not errors, errors
    assert size == expected_size and digest.hexdigest() == expected_sha
    assert len(files) >= 30 and "fs/squashfs/super.c" in files
    receipt = dict(url=url, package="linux-source-6.8.0", version="6.8.0-142.142",
                   sha256=digest.hexdigest(), bytes=size, files=files,
                   verification="Ubuntu apt index SHA256 and size match; SDK payload streamed; only fs/squashfs retained",
                   status="verified")
    (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print("Verified exact Ubuntu142 reader source files:", len(files))
finally:
    failure = dict(errors=errors, download_bytes=size, sha256_so_far=digest.hexdigest(), process_status=process.poll())
    (out / "attempt.json").write_text(json.dumps(failure, indent=2) + "\n")
    if process.poll() is None:
        process.kill()
    worker.join(timeout=10)
    print("DOWNLOAD", errors, size, "DPKG", process.stderr.read().decode(errors="replace"), flush=True)
