"""Relocate installed shared/static SDKs and compile independent C/C++ consumers."""
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys

source, libraries, work = map(Path, sys.argv[1:4])
identity = sys.argv[4]
results = []
for kind, suffix in [('shared', '.so'), ('static', '.a')]:
    original = work / f'sdk-{kind}-original-{identity}'
    relocated = work / f'sdk-{kind}-relocated-{identity}'
    build = work / f'sdk-{kind}-install-build-{identity}'
    consumer = work / f'sdk-{kind}-consumer-{identity}'
    def run(command, **kwargs):
        print('SDK_CHECK', command, flush=True)
        subprocess.run(command, check=True, **kwargs)
    try:
        run(['cmake', '-S', str(source/'packaging/sdk'), '-B', str(build), '-G', 'Ninja',
             '-DCIX_NATIVE_LIBRARY='+str(libraries/('libcix_native'+suffix)),
             '-DCMAKE_INSTALL_PREFIX='+str(original)])
        run(['cmake', '--install', str(build)])
        original.rename(relocated)
        run(['cmake', '-S', str(source/'packaging/sdk/tests'), '-B', str(consumer), '-G', 'Ninja',
             '-DCMAKE_PREFIX_PATH='+str(relocated)])
        run(['cmake', '--build', str(consumer), '--target', 'cix_installed_dictionary_consumer', '--parallel', '2'])
        run([str(consumer/'cix_installed_dictionary_consumer')])
        flags = []
        results.append({'kind':kind,'status':'passed','relocated_prefix':str(relocated),'pkg_config_flags':flags})
    except (subprocess.SubprocessError, OSError, AssertionError) as error:
        results.append({'kind':kind,'status':'failed','error':str(error)})
Path(__file__).with_name('sdk-results.json').write_text(json.dumps(results, indent=2)+'\n')
sys.exit(0 if all(x['status']=='passed' for x in results) else 1)
