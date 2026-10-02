#!/usr/bin/env bash
set -euo pipefail
usage(){ echo "usage: $0 --cix PATH --uncix PATH --native-manifest NATIVE-RELEASE.JSON --out DIR [--payload ARCHIVE9.BHM]" >&2; exit 2; }
cix= uncix= payload= out= native_manifest=
while (($#)); do case "$1" in --cix)cix=$2;shift 2;;--uncix)uncix=$2;shift 2;;--native-manifest)native_manifest=$2;shift 2;;--payload)payload=$2;shift 2;;--out)out=$2;shift 2;;*)usage;;esac;done
[[ -n $cix && -n $uncix && -n $native_manifest && -n $out && ! -e $out ]] || usage
for x in "$cix" "$uncix" "$native_manifest";do [[ -f $x ]]||{ echo "missing: $x" >&2;exit 1;};done
[[ -z $payload || -f $payload ]] || { echo "missing: $payload" >&2; exit 1; }
python3 - "$native_manifest" "$cix" "$uncix" <<'PY'
import hashlib,json,sys
manifest,cix,uncix=sys.argv[1:]
with open(manifest,encoding="utf-8") as f: doc=json.load(f)
pin="d66739120c40fc409f2bf011b165389fc1062c2b"
if doc.get("source_revision") != pin: raise SystemExit(f"native manifest is not pinned to {pin}")
def find(v,name):
 if isinstance(v,dict):
  if v.get("basename")==name and isinstance(v.get("sha256"),str): return v
  if name in v and isinstance(v[name],dict) and isinstance(v[name].get("sha256"),str): return v[name]
  for x in v.values():
   r=find(x,name)
   if r:return r
 if isinstance(v,list):
  for x in v:
   r=find(x,name)
   if r:return r
 return None
for path,name in ((cix,"cix"),(uncix,"uncix")):
 row=find(doc,name)
 if not row: raise SystemExit(f"native manifest has no SHA-256 identity for {name}")
 with open(path,"rb") as f: actual=hashlib.sha256(f.read()).hexdigest()
 if actual != row["sha256"]: raise SystemExit(f"{name} SHA-256 does not match native manifest")
PY
verify_static(){
  local b=$1
  local header program dynamic
  header=$(readelf -hW "$b") || { echo "cannot read ELF header: $b" >&2; exit 1; }
  case "$header" in
    *"Class:"*"ELF64"*"Machine:"*"Advanced Micro Devices X86-64"*) ;;
    *) echo "not an ELF64 x86_64 binary: $b" >&2; exit 1 ;;
  esac
  program=$(readelf -lW "$b") || { echo "cannot read ELF program headers: $b" >&2; exit 1; }
  dynamic=$(readelf -dW "$b") || { echo "cannot read ELF dynamic section: $b" >&2; exit 1; }
  if grep -q 'INTERP' <<<"$program"; then
    echo "not static (PT_INTERP): $b" >&2
    exit 1
  fi
  if grep -q '(NEEDED)' <<<"$dynamic"; then
    echo "not static (DT_NEEDED): $b" >&2
    exit 1
  fi
  return 0
}
verify_static "$cix";verify_static "$uncix"
mkdir -p "$out/build" "$out/bundle";cp "$cix" "$out/bundle/cix";[[ -n $payload ]] && cp "$payload" "$out/archive9.bhm"
inc="$out/build/embedded_bundle.inc";: > "$inc";declare -a names=(cix)
for n in "${names[@]}";do sym="blob_${n//[^A-Za-z0-9]/_}";xxd -i -n "$sym" "$out/bundle/$n"|sed 's/^unsigned char /static const unsigned char /' >> "$inc";done
echo 'static const struct Embedded embedded_files[] = {' >> "$inc"
for n in "${names[@]}";do sym="blob_${n//[^A-Za-z0-9]/_}";mode=0644;[[ $n == cix || $n == uncix ]]&&mode=0755;echo "{\"$n\",$sym,sizeof $sym,$mode}," >> "$inc";done
echo '}; static const size_t embedded_files_count = sizeof embedded_files / sizeof embedded_files[0];' >> "$inc"
cp "$(dirname "$0")/hutter_launcher.c" "$out/build/"
cp "$(dirname "$0")/package.sh" "$out/build/package.sh"
cc -static -O2 -std=c11 -Wall -Wextra -Werror -o "$out/cix9" "$out/build/hutter_launcher.c" -I"$out/build"
verify_static "$out/cix9"
ln "$out/cix9" "$out/comp9a"
ln "$out/cix9" "$out/decomp9"
sha256sum "$out"/cix9 "$out"/bundle/* > "$out/SHA256SUMS";[[ -n $payload ]] && sha256sum "$out/archive9.bhm" >> "$out/SHA256SUMS"
printf '%s\n' 'S = length(comp9a) + length(decomp9) + length(archive9.bhm) = 2 * length(cix9) + length(archive9.bhm); zero external option bytes.' > "$out/ACCOUNTING.txt"
python3 - "$out" "$cix" "$uncix" "$native_manifest" <<'PY'
import hashlib,json,os,sys
out,cix,uncix,native_manifest=map(os.path.abspath,sys.argv[1:])
def row(p): return {"basename":os.path.basename(p),"bytes":os.path.getsize(p),"sha256":hashlib.sha256(open(p,"rb").read()).hexdigest()}
with open(native_manifest,encoding="utf-8") as f: native_doc=json.load(f)
build_fields={}
for source in (native_doc, native_doc.get("intended_build",{}), native_doc.get("static_build",{})):
    if isinstance(source,dict):
        for key in ("profile","RUSTFLAGS","CARGO_BUILD_JOBS","offline","locked","target"):
            if key in source: build_fields[key]=source[key]
script_path=os.path.join(out,"build","package.sh")
v={"schema":"cix-native-hutter-package-static-v1","source_revision":"d66739120c40fc409f2bf011b165389fc1062c2b","native_manifest":{"basename":os.path.basename(native_manifest),"sha256":row(native_manifest)["sha256"]},"native_build_settings":build_fields,"launcher":row(os.path.join(out,"cix9")),"programs":{"comp9a":row(os.path.join(out,"comp9a")),"decomp9":row(os.path.join(out,"decomp9"))},"native_clients":{"cix":{"artifact":row(cix),"included_in_package":True},"uncix":{"artifact":row(uncix),"included_in_package":False,"purpose":"provenance_only"}},"bundled_clients":["cix"],"bundled_libraries":[],"static_elf":{"verified_no_pt_interp":True,"verified_no_dt_needed":True,"verified_elf_class":"ELF64","verified_machine":"Advanced Micro Devices X86-64"},"compiled_flags":{"encode":["--best","--threads","1","--verbose","-o","archive9.bhm","enwik9"],"decode":["-d","-o","data9","archive9.bhm"],"memory":"native default 512MiB"},"external_option_bytes":0,"package_sources":{"hutter_launcher.c_sha256":hashlib.sha256(open(os.path.join(out,"build","hutter_launcher.c"),"rb").read()).hexdigest(),"package.sh_sha256":hashlib.sha256(open(script_path,"rb").read()).hexdigest()}}
open(os.path.join(out,"native-package.json"),"w").write(json.dumps(v,sort_keys=True,indent=2)+"\n")
PY
printf '%s\n' 'No bundled shared libraries: static ELF verification is required for native clients and launcher.' > "$out/LIBRARY-INVENTORY.txt"
