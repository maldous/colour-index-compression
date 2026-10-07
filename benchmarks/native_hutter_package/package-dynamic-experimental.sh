#!/usr/bin/env bash
set -euo pipefail
usage(){ echo "usage: $0 --cix PATH --uncix PATH --out DIR [--payload ARCHIVE9.BHM]" >&2; exit 2; }
cix= uncix= payload= out=
while (($#)); do case "$1" in --cix)cix=$2;shift 2;;--uncix)uncix=$2;shift 2;;--payload)payload=$2;shift 2;;--out)out=$2;shift 2;;*)usage;;esac;done
[[ -n $cix && -n $uncix && -n $out && ! -e $out ]] || usage
for x in "$cix" "$uncix";do [[ -f $x ]]||{ echo "missing: $x" >&2;exit 1;};done
[[ -z $payload || -f $payload ]] || { echo "missing: $payload" >&2; exit 1; }
mkdir -p "$out/build" "$out/bundle";cp "$cix" "$out/bundle/cix";cp "$uncix" "$out/bundle/uncix";[[ -n $payload ]] && cp "$payload" "$out/archive9.bhm"
for x in "$cix" "$uncix";do ldd "$x"|awk '/=> \/.*\.so/{print $3}';done|sort -u|while read -r lib;do case "$(basename "$lib")" in ld-linux*|libc.so.*|libm.so.*);;*)cp -L "$lib" "$out/bundle/$(basename "$lib")";;esac;done
inc="$out/build/embedded_bundle.inc";: > "$inc";declare -a names=(cix uncix)
while read -r f;do case "$f" in cix|uncix);;*)names+=("$f");;esac;done < <(find "$out/bundle" -maxdepth 1 -type f -printf '%f\n'|sort)
for n in "${names[@]}";do sym="blob_${n//[^A-Za-z0-9]/_}";xxd -i -n "$sym" "$out/bundle/$n"|sed 's/^unsigned char /static const unsigned char /' >> "$inc";done
echo 'static const struct Embedded embedded_files[] = {' >> "$inc"
for n in "${names[@]}";do sym="blob_${n//[^A-Za-z0-9]/_}";mode=0644;[[ $n == cix || $n == uncix ]]&&mode=0755;echo "{\"$n\",$sym,sizeof $sym,$mode}," >> "$inc";done
echo '}; static const size_t embedded_files_count = sizeof embedded_files / sizeof embedded_files[0];' >> "$inc"
cp "$(dirname "$0")/hutter_launcher.c" "$out/build/";cc -O2 -std=c11 -Wall -Wextra -Werror -o "$out/cix9" "$out/build/hutter_launcher.c" -I"$out/build";ln "$out/cix9" "$out/comp9a";ln "$out/cix9" "$out/decomp9"
sha256sum "$out"/cix9 "$out"/bundle/* > "$out/SHA256SUMS";[[ -n $payload ]] && sha256sum "$out/archive9.bhm" >> "$out/SHA256SUMS"
printf '%s\n' 'S = length(comp9a) + length(decomp9) + length(archive9.bhm) = 2 * length(cix9) + length(archive9.bhm); zero external option bytes.' > "$out/ACCOUNTING.txt"
python3 - "$out" "$cix" "$uncix" <<'PY'
import hashlib,json,os,subprocess,sys
out,cix,uncix=map(os.path.abspath,sys.argv[1:])
def row(p): return {"basename":os.path.basename(p),"bytes":os.path.getsize(p),"sha256":hashlib.sha256(open(p,"rb").read()).hexdigest()}
def ldd_identity(p):
    identities=[]
    for line in subprocess.check_output(["ldd",p],text=True).splitlines():
        fields=line.strip().split()
        if len(fields)>=3 and fields[1]=="=>":
            identities.append({"soname":fields[0],"resolved_basename":os.path.basename(fields[2])})
        elif fields:
            identities.append({"entry":fields[0]})
    return identities
libs=[row(os.path.join(out,"bundle",n)) for n in sorted(os.listdir(os.path.join(out,"bundle"))) if n not in {"cix","uncix"}]
v={"schema":"cix-native-hutter-package-v1","source_revision":"d66739120c40fc409f2bf011b165389fc1062c2b","launcher":row(os.path.join(out,"cix9")),"programs":{"comp9a":row(os.path.join(out,"comp9a")),"decomp9":row(os.path.join(out,"decomp9"))},"native_clients":{"cix":row(cix),"uncix":row(uncix)},"bundled_libraries":libs,"system_dependencies":{"excluded_from_bundle":["ld-linux","libc","libm"],"ldd":{"cix":ldd_identity(cix),"uncix":ldd_identity(uncix)}},"compiled_flags":{"encode":["--best","--threads","1","--verbose","-o","archive9.bhm","enwik9"],"decode":["-o","data9","archive9.bhm"],"memory":"native default 512MiB"},"external_option_bytes":0,"package_sources":{"hutter_launcher.c_sha256":hashlib.sha256(open(os.path.join(out,"build","hutter_launcher.c"),"rb").read()).hexdigest()}}
open(os.path.join(out,"native-package.json"),"w").write(json.dumps(v,sort_keys=True,indent=2)+"\n")
PY
printf '%s\n' 'Third-party library licenses require explicit inventory and approval before release.' > "$out/LICENSES-PENDING.txt"
