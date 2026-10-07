import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile

assert os.environ.get('CIX_RELEASE_LEASE') == '1'
JOB = Path(__file__).resolve().parent
WORK = Path('/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1')
receipt = json.loads((JOB.parent / 'dotnet-provision-v1/download.json').read_text())
archive = Path(receipt['archive'])
assert hashlib.file_digest(archive.open('rb'), 'sha512').hexdigest() == receipt['expected_sha512']
sdk = WORK / 'dotnet-sdk-8.0.425'
assert (sdk / 'dotnet').is_file()
source = WORK / 'execution-job-mode-v5/bindings/dotnet'
library = WORK / 'sdk-bindings-relocated-cli-bindings-v8/lib/libcix_native.so'
env = os.environ.copy()
env.update(DOTNET_ROOT=str(sdk), DOTNET_CLI_HOME=str(WORK / 'dotnet-cli-home'),
           DOTNET_CLI_TELEMETRY_OPTOUT='1', DOTNET_SKIP_FIRST_TIME_EXPERIENCE='1',
           DOTNET_CLI_WORKLOAD_UPDATE_NOTIFY_DISABLE='true', DOTNET_NOLOGO='1',
           NUGET_PACKAGES=str(WORK / 'dotnet-nuget-cache'), CIX_NATIVE_LIBRARY=str(library))
results = []
commands = [
    ('info', [str(sdk / 'dotnet'), '--info']),
    ('restore', [str(sdk / 'dotnet'), 'restore', str(source / 'Cix.Native.Contract'),
                 '--configfile', str(JOB / 'NuGet.Config')]),
    ('build', [str(sdk / 'dotnet'), 'build', str(source / 'Cix.Native.Contract'),
               '--no-restore', '-m:4', '-p:UseSharedCompilation=false']),
    ('contract', [str(sdk / 'dotnet'), str(source / 'Cix.Native.Contract/bin/Debug/net8.0/Cix.Native.Contract.dll')]),
]
for label, command in commands:
    result = subprocess.run(command, env=env, capture_output=True, timeout=300)
    (JOB / (label + '.stdout.log')).write_bytes(result.stdout)
    (JOB / (label + '.stderr.log')).write_bytes(result.stderr)
    results.append({'label': label, 'command': command, 'exit_code': result.returncode})
    (JOB / 'consumer-results.json').write_text(json.dumps(results, indent=2) + '\n')
    if result.returncode:
        raise SystemExit(result.returncode)
