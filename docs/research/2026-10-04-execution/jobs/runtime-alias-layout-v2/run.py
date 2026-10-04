"""Focused prebuilt runtime layout and source-extracted CLI alias checks."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[5]
JOB = Path(__file__).resolve().parent
WORK = ROOT / "benchmark-work/native-rc-check-v1/runtime-alias-layout-v2"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if os.environ.get("CIX_RELEASE_LEASE") != "1":
        raise RuntimeError("root scheduler lease required")
    WORK.mkdir()
    runtime = ROOT / "rust/cix-native/packaging/runtime"
    cli = ROOT / "rust/cix-native/src/cli.rs"
    inputs = [cli, runtime / "CMakeLists.txt", runtime / "README.md"]
    before = {str(path): sha(path) for path in inputs}
    frozen = WORK / "source"
    shutil.copytree(runtime, frozen)
    shutil.copyfile(cli, WORK / "cli.rs")
    body = cli.read_text()
    start = body.index("fn normalized_program_name(")
    end = body.index("\nfn takes_option_value(", start)
    fixture = 'use std::path::Path;\n' + body[start:end] + '''
#[test]
fn aliases() {
    for name in ["uncix.ExE", "UNCIX.EXE", "UNCIX"] {
        assert_eq!(normalized_program_name(name, true), "uncix");
    }
    assert_eq!(normalized_program_name("CIXCAT.eXe", true), "cixcat");
    assert_eq!(normalized_program_name("uncix.exe", false), "uncix.exe");
    assert_eq!(normalized_program_name("Uncix", false), "Uncix");
    assert_eq!(decoder_program_name(&["/usr/bin/uncix".into()]), (true, false));
    assert_eq!(decoder_program_name(&["/usr/bin/cixcat".into()]), (true, true));
    assert_eq!(decoder_program_name(&["/usr/bin/cix".into()]), (false, false));
    assert_eq!(decoder_program_name(&["/usr/bin/uncix.exe".into()]), (false, false));
}
'''
    (WORK / "aliases.rs").write_text(fixture)
    executable = WORK / "selected-cix.exe"
    executable.write_bytes(b"CIX synthetic prebuilt runtime staging fixture\n")
    receipt = {"status": "started", "source_sha256": before, "commands": [],
               "scope": "synthetic CMake Windows/Linux layout and exact extracted Rust alias functions; no Windows executable or whole CLI qualification"}

    def run(argv, label, expected=0):
        result = subprocess.run([str(value) for value in argv], cwd=WORK, text=True,
                                capture_output=True, timeout=60)
        receipt["commands"].append({"label": label, "argv": result.args,
            "returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr})
        if (expected == 0 and result.returncode) or (expected != 0 and not result.returncode):
            raise RuntimeError(label + " returned an unexpected status")

    try:
        run(["rustc", "--edition=2021", "--test", "-Dwarnings", "-O", WORK / "aliases.rs", "-o", WORK / "aliases"], "compile-extracted-alias-functions")
        run([WORK / "aliases"], "execute-extracted-alias-checks")
        for platform in ("Linux", "Windows"):
            build, prefix = WORK / (platform + "-build"), WORK / (platform + "-prefix")
            run(["cmake", "-S", frozen, "-B", build, "-DCMAKE_SYSTEM_NAME=" + platform,
                 "-DCIX_RUNTIME_CAPABILITY=native-only", "-DCIX_RUNTIME_CIX_EXECUTABLE=" + str(executable),
                 "-DCMAKE_INSTALL_PREFIX=" + str(prefix)], platform + "-configure")
            run(["cmake", "--install", build], platform + "-install")
            suffix = ".exe" if platform == "Windows" else ""
            for name in ("cix", "uncix", "cixcat"):
                installed = prefix / "bin" / (name + suffix)
                if not installed.is_file() or sha(installed) != sha(executable):
                    raise RuntimeError(platform + " alias bytes differ")
                if platform == "Windows" and installed.is_symlink():
                    raise RuntimeError("Windows alias requires a symlink")
            if platform == "Linux" and not (prefix / "bin/uncix").is_symlink():
                raise RuntimeError("Linux alias behavior changed")
        for platform in ("Windows", "Darwin", "FreeBSD"):
            run(["cmake", "-S", frozen, "-B", WORK / (platform + "-full-refusal"), "-DCMAKE_SYSTEM_NAME=" + platform,
                 "-DCIX_RUNTIME_CAPABILITY=full-engine", "-DCIX_RUNTIME_CIX_EXECUTABLE=" + str(executable)],
                platform + "-full-engine-refused", expected=1)
            if "requires qualified ELF/Linux inputs" not in receipt["commands"][-1]["stderr"]:
                raise RuntimeError("full-engine refusal did not identify the platform boundary")
        receipt["inputs_unchanged"] = all(sha(Path(name)) == value for name, value in before.items())
        if not receipt["inputs_unchanged"]:
            raise RuntimeError("source changed during layout check")
        receipt["status"] = "pass_scoped_layout_and_alias_logic"
    except Exception as error:
        receipt.update(status="fail", error=str(error))
        raise
    finally:
        shutil.copyfile(WORK / "aliases.rs", JOB / "aliases.rs.txt")
        (JOB / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
