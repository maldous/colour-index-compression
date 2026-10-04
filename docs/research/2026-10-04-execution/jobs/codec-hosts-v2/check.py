"""Pinned Blosc2/Squash host contracts, run under the shared root lease only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    for name in ('source', 'work', 'sdk', 'archives', 'submodules', 'lz4'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--component', action='append', choices=['blosc2', 'squash'])
    a = parser.parse_args()
    assert os.environ.get('CIX_RELEASE_LEASE') == '1'
    a.work.mkdir(exist_ok=False)
    receipt = {'sources': {str(p.relative_to(a.source)): digest(p)
                           for p in sorted(a.source.rglob('*')) if p.is_file()},
               'native_library_sha256': digest(a.sdk / 'lib/libcix_native.so'),
               'archives': [], 'components': {}}
    active = None

    def save():
        (a.work / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')

    def run(argv, env=None):
        item = {'argv': list(map(str, argv)), 'env_extra': env or {}}
        receipt['components'][active]['commands'].append(item)
        result = subprocess.run(item['argv'], cwd=a.work,
                                env={**os.environ, **(env or {})}, capture_output=True, text=True)
        item.update(returncode=result.returncode, stdout=result.stdout, stderr=result.stderr)
        print(active, item['argv'], result.returncode, flush=True)
        save()
        if result.returncode:
            raise RuntimeError(result.stderr[-4000:] or result.stdout[-4000:])
        return result.stdout

    def unpack(path, expected, destination):
        assert digest(path) == expected, str(path)
        destination.mkdir(parents=True, exist_ok=True)
        with tarfile.open(path) as archive:
            members = archive.getmembers()
            roots = {p.name.split('/')[0] for p in members}
            assert len(roots) == 1
            for member in members:
                parts = Path(member.name).parts[1:]
                if not parts:
                    continue
                assert not member.islnk(), 'hard links require explicit root remapping'
                member.name = str(Path(*parts))
                archive.extract(member, destination, filter='data')
        receipt['archives'].append({'path': str(path), 'sha256': expected,
                                    'destination': str(destination)})
        save()

    def blosc2():
        source, build, prefix = [a.work / ('blosc2-' + n) for n in ('source', 'build', 'prefix')]
        unpack(a.archives / 'blosc2-3.3.2.tar.gz',
               '925088d8bbe9be5a2d010fa4ea6adeeb843566ec300a59533098e1d8da8a497f', source)
        run(['cmake', '-S', source, '-B', build, '-DCMAKE_BUILD_TYPE=Release',
             '-DCMAKE_INSTALL_PREFIX=' + str(prefix), '-DBUILD_SHARED=ON', '-DBUILD_STATIC=OFF',
             '-DBUILD_TESTS=OFF', '-DBUILD_FUZZERS=OFF', '-DBUILD_BENCHMARKS=OFF',
             '-DBUILD_EXAMPLES=OFF', '-DBUILD_PLUGINS=OFF', '-DBLOSC_ENABLE_ZFP=OFF',
             '-DDEACTIVATE_ZLIB=ON', '-DDEACTIVATE_ZSTD=ON', '-DBLOSC_DEPENDENCY_MODE=EXTERNAL',
             '-DBLOSC_INSTALL=ON', '-DLZ4_INCLUDE_DIR=' + str(a.lz4 / 'include'),
             '-DLZ4_LIBRARY=' + str(a.lz4 / 'lib/x86_64-linux-gnu/liblz4.so')])
        run(['cmake', '--build', build, '-j4'])
        run(['cmake', '--install', build])
        adapter = a.work / 'blosc2-adapter'
        run(['cmake', '-S', a.source / 'adapters/blosc2', '-B', adapter,
             '-DCIX_NATIVE_INCLUDE_DIR=' + str(a.sdk / 'include'),
             '-DCIX_NATIVE_LIBRARY=' + str(a.sdk / 'lib/libcix_native.so'),
             '-DBLOSC2_INCLUDE_DIR=' + str(prefix / 'include'),
             '-DBLOSC2_LIBRARY=' + str(prefix / 'lib/libblosc2.so'),
             '-DCIX_BLOSC2_EXPERIMENTAL_CODEC_ID=240', '-DCIX_BLOSC2_BUILD_CONTRACT_TEST=ON'])
        run(['cmake', '--build', adapter, '-j4'])
        run(['ctest', '--test-dir', adapter, '--output-on-failure'])

    def squash():
        source, build, prefix = [a.work / ('squash-' + n) for n in ('source', 'build', 'prefix')]
        unpack(a.archives / 'squash-pinned.tar.gz',
               '0ce6819a07d2ffe26aad7dff7f3e26709ec57a32cf7771d6b6969a58353fc697', source)
        for item in json.loads(a.submodules.read_text())['submodules']:
            unpack(Path(item['archive']), item['sha256'], source / item['path'])
        plugins = ['BRIEFLZ', 'BROTLI', 'BSC', 'BZIP2', 'COPY', 'CRUSH', 'CSC', 'DENSITY',
                   'DOBOZ', 'FARI', 'FASTLZ', 'GIPFELI', 'HEATSHRINK', 'LIBDEFLATE', 'LZ4',
                   'LZF', 'LZFSE', 'LZG', 'LZHAM', 'LZJB', 'LZMA', 'LZO', 'MINIZ', 'MS_COMPRESS',
                   'NCOMPRESS', 'QUICKLZ', 'SNAPPY', 'WFLZ', 'YALZ77', 'ZLIB', 'ZLIB_NG',
                   'ZLING', 'ZPAQ', 'ZSTD']
        run(['cmake', '-S', source, '-B', build, '-DCMAKE_BUILD_TYPE=Release',
             '-DCMAKE_INSTALL_PREFIX=' + str(prefix)] + ['-DENABLE_' + n + '=no' for n in plugins])
        # The old upstream test suite uses common-symbol declarations that fail
        # with modern GCC's -fno-common default. Build the host library and CLI
        # needed for this contract without editing upstream test source.
        run(['cmake', '--build', build, '--target', 'squash0.8', 'squash', '-j4'])
        run(['cmake', '--install', build])
        env = {'PKG_CONFIG_PATH': str(prefix / 'lib/pkgconfig'),
               'LD_LIBRARY_PATH': str(prefix / 'lib'),
               'SQUASH_SOURCE_REVISION': '713eeca85cccadde39bf57f8b59ea663a085a347',
               'CIX_NATIVE_LIBRARY': str(a.sdk / 'lib/libcix_native.so'),
               'CIX_INCLUDE_DIR': str(a.sdk / 'include'),
               'SQUASH_PLUGIN_ROOT': str(a.work / 'squash-plugins')}
        run(['sh', a.source / 'packaging/squash/build-plugin.sh'], env)
        import shlex
        flags = shlex.split(run(['pkg-config', '--cflags', '--libs', 'squash-0.8'], env))
        run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
             a.source / 'packaging/squash/contract.c', *flags, '-o', a.work / 'squash-contract'], env)
        run([a.work / 'squash-contract', a.work / 'squash-plugins'], env)

    for name, function in [('blosc2', blosc2), ('squash', squash)]:
        if a.component and name not in a.component:
            continue
        active = name
        receipt['components'][name] = {'commands': [], 'status': 'running'}
        try:
            function()
            receipt['components'][name]['status'] = 'pass'
        except Exception as error:
            receipt['components'][name].update(status='fail', error=str(error))
        save()
    return int(any(v['status'] != 'pass' for v in receipt['components'].values()))


if __name__ == '__main__':
    raise SystemExit(main())
