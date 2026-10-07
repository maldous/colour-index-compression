import json,os,subprocess
from pathlib import Path
assert os.environ.get('CIX_RELEASE_LEASE')=='1'
r=Path(__file__).resolve().parents[5];w=r/'benchmark-work/native-rc-check-v1';out=w/'gstreamer-host-v2';out.mkdir();src=w/'gstreamer-source-v2';sdk=w/'sdk-bindings-relocated-cli-bindings-v8';rows=[]
env={**os.environ,'TMPDIR':str(out),'PKG_CONFIG_PATH':str(w/'gstreamer-sdk-v1/prefix/cix-pkgconfig'),'GST_REGISTRY':str(out/'gst-registry.bin')}
def run(args):
 p=subprocess.run(list(map(str,args)),env=env,cwd=out,capture_output=True,text=True,timeout=180)
 rows.append(dict(argv=list(map(str,args)),returncode=p.returncode,stdout=p.stdout,stderr=p.stderr));(out/'receipt.json').write_text(json.dumps(rows,indent=2)+'\n');print(args,p.returncode,flush=True)
 if p.returncode:raise RuntimeError(p.stderr[-6000:] or p.stdout[-6000:])
run(['cmake','-S',src,'-B',out/'gst-build','-DCIX_INCLUDE_DIR='+str(sdk/'include'),'-DCIX_NATIVE_LIBRARY='+str(sdk/'lib/libcix_native.so'),'-DCMAKE_C_FLAGS=-Wall -Wextra -Werror'])
run(['cmake','--build',out/'gst-build','-j4'])
run(['ctest','--test-dir',out/'gst-build','--output-on-failure','--timeout','30'])
