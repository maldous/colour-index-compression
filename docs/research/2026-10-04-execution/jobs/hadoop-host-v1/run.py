import os,subprocess,json
from pathlib import Path
assert os.environ.get('CIX_RELEASE_LEASE')=='1'
w=Path('/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1');src=Path('/home/user/src/colour-index-compression/benchmark-work/native-rc-check-v1/hadoop-source-v1');out=w/'hadoop-host-v1';out.mkdir(exist_ok=False);classes=out/'classes';classes.mkdir()
cp=':'.join(map(str,sorted((w/'hadoop-jars-v1').glob('*.jar'))));rows=[]
def run(args,env={}):
 p=subprocess.run(list(map(str,args)),env={**os.environ,**env},capture_output=True,text=True,cwd=out);rows.append(dict(argv=list(map(str,args)),env_extra=env,returncode=p.returncode,stdout=p.stdout,stderr=p.stderr));(out/'receipt.json').write_text(json.dumps(rows,indent=2)+'\n');print(args,p.returncode,flush=True)
 if p.returncode:raise RuntimeError(p.stderr[-4000:] or p.stdout[-4000:])
files=list((src/'bindings/java/src/main/java').rglob('*.java'))+list((src/'adapters/hadoop/src').rglob('*.java'))
run(['/usr/lib/jvm/java-21-openjdk-amd64/bin/javac','--release','17','-cp',cp,'-d',classes,*files])
run(['/usr/lib/jvm/java-21-openjdk-amd64/bin/java','-cp',str(classes)+':'+cp,'dev.cix.hadoop.HadoopContract'],{'CIX_HADOOP_NATIVE_LIBRARY':str(w/'sdk-bindings-relocated-cli-bindings-v8/lib/libcix_native.so'),'CIX_HADOOP_JNI_LIBRARY':str(w/'java-binding-language-consumers-v2/libcix_jni.so')})
