"""Record read-only GPU/toolchain metadata; never launch a compute kernel."""
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

AREA = Path(__file__).resolve().parent
ROOT = AREA.parents[2]

def query(argv):
    try:
        result = subprocess.run(argv, capture_output=True, text=True, timeout=15, check=False)
        return {"argv": argv, "returncode": result.returncode,
                "stdout": result.stdout.strip(), "stderr": result.stderr.strip()}
    except (OSError, subprocess.TimeoutExpired) as error:
        return {"argv": argv, "error": str(error)}

def main():
    commands = [
        ["nvidia-smi", "--query-gpu=name,driver_version,memory.total,memory.used,pci.bus_id,compute_cap,utilization.gpu,temperature.gpu,power.limit", "--format=csv"],
        ["nvidia-smi", "--query-compute-apps=pid,process_name,used_memory", "--format=csv"],
        ["/usr/local/cuda/bin/nvcc", "--version"],
        ["lspci", "-nn", "-s", "01:00.0"],
    ]
    libraries = query(["ldconfig", "-p"])
    libraries["stdout"] = "\n".join(line for line in libraries.get("stdout", "").splitlines()
                                      if any(name in line.lower() for name in ("cuda", "nvrtc", "nvcomp", "cubwt")))
    paths = ["rust/cix-native/build.rs", "rust/cix-native/src/bsc_ffi.rs",
             "rust/cix-native/vendor/libbsc/UPSTREAM.md",
             "rust/cix-native/vendor/libbsc/libbsc/bwt/bwt.cpp",
             "rust/cix-native/vendor/libbsc/libbsc/bwt/libcubwt/libcubwt.cuh"]
    source = [{"path": path, "sha256": hashlib.sha256((ROOT / path).read_bytes()).hexdigest()}
              for path in paths]
    version_file = Path("/usr/local/cuda/version.json")
    result = {
        "schema": "cix.gpu-cuda-host.v1",
        "observed_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "scope": "read-only metadata; no GPU kernel, codec, benchmark, installation or host tuning",
        "nvcc_on_path": shutil.which("nvcc"),
        "queries": [query(command) for command in commands],
        "dynamic_library_cache": libraries,
        "cuda_version_manifest": json.loads(version_file.read_text()) if version_file.exists() else None,
        "source_identity": source,
        "limitations": ["Instantaneous device availability is not a resource reservation.",
                        "Metadata/toolchain presence does not prove compilation or kernel compatibility.",
                        "Library cache absence does not prove no private installation exists."]
    }
    destination = AREA / "host.json"
    if destination.exists():
        raise SystemExit("Preserve existing receipt; choose a new observation file explicitly.")
    destination.write_text(json.dumps(result, indent=2) + "\n")
    print(destination)

if __name__ == "__main__":
    main()
