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
        run(['cmake', '--build', str(consumer), '--parallel', '2'])
        run([str(consumer/'cix_installed_cpp_consumer')])
        run([str(consumer/'cix_installed_stream_consumer')])
        run([str(consumer/'cix_installed_format_consumer')])
        run([str(consumer/'cix_installed_dictionary_consumer')])
        packages = list(relocated.rglob('cix-native.pc'))
        assert len(packages) == 1
        env = dict(os.environ, PKG_CONFIG_PATH=str(packages[0].parent))
        arguments = ['pkg-config'] + (['--static'] if kind == 'static' else []) + ['--cflags','--libs','cix-native']
        flags = shlex.split(subprocess.check_output(arguments, env=env, text=True))
        assert str(original) not in ' '.join(flags), 'pkg-config retained the old prefix'
        c_consumer = consumer/'c_installed_consumer'
        run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', str(source/'tests/c_api_consumer.c'),
             '-o',str(c_consumer), *flags, '-Wl,-rpath,'+str(packages[0].parent.parent)])
        run([str(c_consumer)])
        results.append({'kind':kind,'status':'passed','relocated_prefix':str(relocated),'pkg_config_flags':flags})
    except (subprocess.SubprocessError, OSError, AssertionError) as error:
        results.append({'kind':kind,'status':'failed','error':str(error)})
Path(__file__).with_name('sdk-results.json').write_text(json.dumps(results, indent=2)+'\n')
sys.exit(0 if all(x['status']=='passed' for x in results) else 1)
