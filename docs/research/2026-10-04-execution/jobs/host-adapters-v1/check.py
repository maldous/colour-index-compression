"""Focused installed-host adapter checks; invoked only under root's lease."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser()
    for name in ['source', 'work', 'sdk', 'host', 'cix']:
        parser.add_argument('--' + name, type=Path, required=True)
    a = parser.parse_args()
    assert os.environ.get('CIX_RELEASE_LEASE') == '1'
    a.work.mkdir(exist_ok=False)
    receipt = {'sources': {str(p.relative_to(a.source)): hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in sorted(a.source.rglob('*')) if p.is_file()},
               'cix_sha256': hashlib.sha256(a.cix.read_bytes()).hexdigest(),
               'native_library_sha256': hashlib.sha256((a.sdk/'lib/libcix_native.so').read_bytes()).hexdigest(),
               'components': {}}
    active = None
    def save():
        (a.work/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
    def run(argv, env=None, cwd=None):
        record={'argv':list(map(str,argv)), 'env_extra':env or {}, 'cwd':str(cwd or a.work)}
        receipt['components'][active]['commands'].append(record)
        p=subprocess.run(record['argv'],cwd=cwd or a.work,env={**os.environ,**(env or {})},capture_output=True,text=True)
        record.update(returncode=p.returncode,stdout=p.stdout,stderr=p.stderr)
        print(active, record['argv'], p.returncode,flush=True)
        save()
        if p.returncode: raise RuntimeError(p.stderr[-4000:] or p.stdout[-4000:])
    native=a.sdk/'lib/libcix_native.so'
    def hdf5():
        build=a.work/'hdf5'
        run(['cmake','-S',a.source/'hdf5','-B',build,
             '-DCIX_NATIVE_INCLUDE_DIR='+str(a.sdk/'include'),'-DCIX_NATIVE_LIBRARY='+str(native),
             '-DCIX_HDF5_FILTER_ID=65001','-DCIX_HDF5_BUILD_CONTRACT_TEST=ON',
             '-DHDF5_C_INCLUDE_DIR='+str(a.host/'usr/include/hdf5/serial'),
             '-DHDF5_C_LIBRARY_hdf5=/usr/lib/x86_64-linux-gnu/libhdf5_serial.so.103'])
        run(['cmake','--build',build,'-j4'])
        run(['ctest','--test-dir',build,'--output-on-failure'])
        run(['cc','-std=c99','-Wall','-Wextra','-Werror','-I'+str(a.host/'usr/include'),
             '-DCIX_HDF5_FILTER_ID=65001',a.source/'hdf5/examples/netcdf_filter.c',
             '/usr/lib/x86_64-linux-gnu/libnetcdf.so.19','-o',a.work/'netcdf-contract'])
        run([a.work/'netcdf-contract'],{'HDF5_PLUGIN_PATH':str(build)})
    def gio():
        build=a.work/'gio'
        run(['cmake','-S',a.source/'gio','-B',build,'-DCIX_INCLUDE_DIR='+str(a.sdk/'include'),
             '-DCIX_NATIVE_LIBRARY='+str(native)])
        run(['cmake','--build',build,'-j4'])
        run([build/'cix-gconverter-contract'])
    def archive():
        env={'CIX_TAR_CIX':str(a.cix),'TMPDIR':str(a.work),
             'CIX_TAR_RECEIPT_DIR':str(a.work/'tar-receipt')}
        run([a.source/'libarchive/qualify.sh'],env)
        run(['cc','-std=c11','-Wall','-Wextra','-Werror','-I'+str(a.host/'usr/include'),
             a.source/'libarchive/libarchive_program_filter.c','/usr/lib/x86_64-linux-gnu/libarchive.so.13',
             '-o',a.work/'libarchive-contract'])
        run([a.work/'libarchive-contract',a.source/'libarchive/cix-tar-filter.sh',a.work/'libarchive.tar.cix'],env)
    for name, fn in [('hdf5',hdf5),('gio',gio),('libarchive',archive)]:
        active=name; receipt['components'][name]={'commands':[],'status':'running'}
        try:
            fn();receipt['components'][name]['status']='pass'
        except Exception as error:
            receipt['components'][name].update(status='fail',error=str(error))
        save()
    return int(any(v['status']!='pass' for v in receipt['components'].values()))

if __name__=='__main__':raise SystemExit(main())
