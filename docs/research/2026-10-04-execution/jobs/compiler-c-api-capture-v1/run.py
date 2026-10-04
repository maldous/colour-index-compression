import hashlib,json,os,subprocess
from pathlib import Path
assert os.environ.get("CIX_RELEASE_LEASE")=="1"
root=Path(__file__).resolve().parents[5]; work=root/"benchmark-work/native-rc-check-v1"; out=work/"compiler-c-api-capture-v1";out.mkdir()
source=root/"rust/cix-native/tests/c_api_consumer.c";sdk=work/"distribution-engineering-v4/stage/usr"
command=["cc","-std=c11","-Wall","-Wextra","-Werror","-I"+str(sdk/"include"),str(source),"-L"+str(sdk/"lib"),"-Wl,-rpath,"+str(sdk/"lib"),"-lcix_native","-o",str(out/"c_api_consumer")]
r=subprocess.run(command,cwd=out,text=True,capture_output=True)
receipt={"kind":"NEW_ANALYSIS_CONFIGURATION","argv":command,"cwd":str(out),"returncode":r.returncode,"stdout":r.stdout,"stderr":r.stderr,"source":str(source),"source_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),"headers":{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (sdk/"include").glob("*.h")}}
(out/"receipt.json").write_text(json.dumps(receipt,indent=2)+"\n");(Path(__file__).parent/"receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
raise SystemExit(r.returncode)
