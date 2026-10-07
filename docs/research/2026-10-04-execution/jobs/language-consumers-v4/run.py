import os,subprocess,json
from pathlib import Path
assert os.environ.get("CIX_RELEASE_LEASE")=="1"
r=subprocess.run(['/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1/python-host-sdk-v1/bin/python', '-m', 'pytest', '-q', '-p', 'no:cacheprovider', '/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1/execution-language-consumers-v4/bindings/python/tests/test_integrations.py'],capture_output=True)
p=Path('/home/user/src/colour-index-compression/docs/research/2026-10-04-execution/jobs/language-consumers-v4')
(p/"python-host-contract.stdout.log").write_bytes(r.stdout)
(p/"python-host-contract.stderr.log").write_bytes(r.stderr)
(p/"consumer-results.json").write_text(json.dumps({"command":['/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1/python-host-sdk-v1/bin/python', '-m', 'pytest', '-q', '-p', 'no:cacheprovider', '/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1/execution-language-consumers-v4/bindings/python/tests/test_integrations.py'],"exit_code":r.returncode},indent=2)+"\n")
raise SystemExit(r.returncode)
