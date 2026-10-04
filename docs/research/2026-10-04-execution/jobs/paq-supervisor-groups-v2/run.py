"""Continue the unchanged frozen source after correcting test prerequisite order."""
import importlib.util
import json
import os
from pathlib import Path
import shutil

JOB = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("supervisor_v1", JOB.parent / "paq-supervisor-groups-v1/run.py")
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)


def main():
    if os.environ.get("CIX_RELEASE_LEASE") != "1":
        raise RuntimeError("root scheduler lease required")
    previous = json.loads((h.WORK / "receipt.json").read_text())
    if previous.get("status") != "fail" or previous.get("error") != "paq-supervisor failed; inspect " + str(h.WORK / "paq-supervisor.stderr.log"):
        raise RuntimeError("unexpected predecessor failure")
    for name in ("format", "clippy", "paq-worker"):
        if previous["phases"][name]["returncode"] != 0:
            raise RuntimeError("prerequisite did not pass")
    if "set CIX_TEST_EXECUTABLE, CIX_TEST_PAQ_LIBDIR and CIX_TEST_PAQ_WORKROOT together" not in (h.WORK / "paq-supervisor.stderr.log").read_text():
        raise RuntimeError("predecessor does not have the known prerequisite-order failure")
    frozen = previous["source_before"]
    if h.snapshot() != frozen:
        raise RuntimeError("frozen predecessor source changed")
    h.scope()
    cargo = shutil.which("cargo")
    receipt = {"status": "running", "source_before": frozen,
        "predecessor_receipt_sha256": h.sha256(h.WORK / "receipt.json"),
        "providers_before": h.providers(), "phases": {},
        "scope": "same v1 source/cache; build CLI before opt-in supervisor and archive fixtures"}
    def save(value):
        (JOB / "receipt.json").write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    h.write_receipt = save
    env = os.environ.copy()
    env.update({"CARGO_TARGET_DIR": str(h.TARGET), "CARGO_BUILD_JOBS": "4", "CARGO_INCREMENTAL": "0",
        "CARGO_NET_OFFLINE": "true", "CARGO_PROFILE_DEV_DEBUG": "0", "CARGO_PROFILE_TEST_DEBUG": "0",
        "TMPDIR": str(h.TMP), "CIX_NATIVE_LIBRARY_DIR": str(h.SDK), "LIBRARY_PATH": str(h.SDK),
        "CIX_TEST_PAQ_LIBDIR": str(h.PAQ), "CIX_TEST_PAQ_WORKROOT": str(h.PAQ_ROOT), "CIX_TEST_JXL_BRIDGE": str(h.JXL)})
    common = ["--manifest-path", str(h.SOURCE / "Cargo.toml"), "--locked", "--offline", "-p", "cix-native"]
    try:
        h.phase("build-cix-v2", [cargo, "build", *common, "--bin", "cix"], env, receipt, frozen)
        cix = h.TARGET / "debug/cix"
        receipt["providers_before"] = h.providers(cix)
        env["CIX_TEST_EXECUTABLE"] = str(cix)
        for label, name in (("supervisor-v2", "paq_supervisor::tests"),
                            ("provider-dispatch-v2", "full_engine::dispatch::tests::installed_paq_and_jxl_complete_archive_dispatch")):
            h.phase(label, [cargo, "test", *common, "--lib", name, "--", "--test-threads=1", "--nocapture"], env, receipt, frozen, True)
        receipt["status"] = "pass"
    except Exception as error:
        receipt.update(status="fail", error=str(error))
        raise
    finally:
        receipt["source_after"] = h.snapshot()
        save(receipt)


if __name__ == "__main__":
    main()
