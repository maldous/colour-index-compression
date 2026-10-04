import hashlib,json,os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5]; OUT=Path(__file__).resolve().parent
BINARY=ROOT/"benchmark-work/native-rc-check-v1/native-final-source-v3/target/debug/deps/cix_native-704a8ba0453fec81"
EXPECTED="0372375648c9fea6e0a29cb2ff9898929bfc184567ee0abf36044338caf15ca8"
TEST="cli::policy_tests::program_name_normalization_is_platform_specific"
if os.environ.get("CIX_RELEASE_LEASE")!="1":raise RuntimeError("root lease required")
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(BINARY)==EXPECTED
result=subprocess.run([str(BINARY),TEST,"--exact","--test-threads=1"],capture_output=True,text=True)
(OUT/"stdout.log").write_text(result.stdout);(OUT/"stderr.log").write_text(result.stderr)
passed=result.returncode==0 and "running 1 test" in result.stdout and "1 passed; 0 failed" in result.stdout and ("test "+TEST+" ... ok") in result.stdout
assert sha(BINARY)==EXPECTED
(OUT/"receipt.json").write_text(json.dumps({"status":"pass" if passed else "fail","binary_sha256":EXPECTED,"test":TEST,"exit_code":result.returncode,"scope":"exact existing frozen-source unit test, no rebuild, Linux execution of pure Windows/Unix name-normalization cases; not Windows runtime qualification"},indent=2)+"\n")
if not passed:raise RuntimeError("exact test did not run and pass")
