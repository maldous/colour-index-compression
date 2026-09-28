"""Physical-size CIX ensemble: bounded PPM/mixer, spatial/volume and optional PAQ.

Existing CIX frame magics identify their decoders without another wrapper. For
PAQ, six constant magic bytes are replaced with a six-byte CIX header identifying
the exact backend version. This changes no arithmetic payload and adds no bytes.
PAQ is credited as a backend, not presented as a new CIX model.
"""
import hashlib
import subprocess
import tempfile
import time
import zlib
from pathlib import Path

from cix.multinomial import vencode, vdecode
from benchmarks import spatial_image_codec as spatial
from benchmarks import volume_image_codec as volume

RAW=b'CIXU\x01'
PAQ=b'CIXP\x01'
ROOT=Path(__file__).resolve().parents[1]
PAQ_VERSIONS={1:'v215',2:'v216'}
PAQ_BINARIES={
    'v215':'b982f1e8307d6c38e8febc6415901fafcc2e84a14d51e0af7c5cbbe6322778e7',
    'v216':'4fd7b3e768917a665ee4b91c6df3af1d22f540f7ff5beefe7fec689a8db182cc',
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def paq_binary(version):
    if version not in PAQ_BINARIES:raise ValueError('unsupported PAQ version')
    binary=ROOT/'benchmark-work/references'/('paq8px-'+version)/'build-local/paq8px'
    if sha(binary.read_bytes())!=PAQ_BINARIES[version]:raise ValueError('PAQ binary provenance mismatch')
    return str(binary)


def wrap_paq(blob,version):
    if len(blob)<9 or blob[:6]!=b'paq8px':raise ValueError('invalid PAQ stream')
    mode=next((k for k,v in PAQ_VERSIONS.items() if v==version),None)
    if mode is None:raise ValueError('unsupported PAQ version')
    return PAQ+bytes([mode])+blob[6:]


def unwrap_paq(frame):
    if len(frame)<9 or frame[:5]!=PAQ or frame[5] not in PAQ_VERSIONS:raise ValueError('invalid CIX PAQ frame')
    return PAQ_VERSIONS[frame[5]],b'paq8px'+frame[6:]


def encode_paq(data,version,options):
    binary=paq_binary(version)
    with tempfile.TemporaryDirectory(prefix='cix-paq-') as folder:
        source=Path(folder)/'source.bin';archive=Path(folder)/('stream.paq8px'+version[1:])
        source.write_bytes(data)
        subprocess.run([binary,options,'-simd','AVX2',str(source),str(archive)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        return wrap_paq(archive.read_bytes(),version)


def decode(frame):
    magic=frame[:5]
    if magic==RAW:
        n,pos=vdecode(frame,5)
        if pos+4+n!=len(frame):raise ValueError('raw frame length mismatch')
        raw=frame[pos+4:]
        if zlib.crc32(raw)!=int.from_bytes(frame[pos:pos+4],'big'):raise ValueError('raw checksum mismatch')
        return raw
    if magic==spatial.MAGIC:return spatial.decode(frame)
    if magic==volume.MAGIC:return volume.decode(frame)
    if magic==b'CIXG\x01':
        from benchmarks.sdf_geometry_probe import decode as geometry
        return geometry(frame)
    if magic==b'CIXQ\x01':
        from benchmarks.sdf_hydrogen_probe import decode as hydrogen
        return hydrogen(frame)
    if magic==b'CIXT\x01':
        from benchmarks.legacy_mixer_native import enable
        from benchmarks.native_ppm_decode import enable as enable_ppm
        from benchmarks.joint_bounded import decode as legacy
        enable();enable_ppm()
        return legacy(frame)
    if magic==PAQ:
        version,blob=unwrap_paq(frame);binary=paq_binary(version)
        with tempfile.TemporaryDirectory(prefix='cix-paq-') as folder:
            archive=Path(folder)/('stream.paq8px'+version[1:]);restored=Path(folder)/'decoded.bin'
            archive.write_bytes(blob)
            subprocess.run([binary,'-d','-simd','AVX2',str(archive),str(restored)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            return restored.read_bytes()
    raise ValueError('unsupported competitive frame')


def encode(data,*,legacy_cache=None,paq=None,paq_cache=None):
    """Caches are optional acceleration; the benchmark runner validates identity.

    Return the actual selected physical frame and all measured candidate costs.
    The uncached path computes the same fixed candidate policy from source bytes.
    """
    best=RAW+vencode(len(data))+zlib.crc32(data).to_bytes(4,'big')+data
    selected='raw';trials=[dict(name=selected,size=len(best),encode_seconds=0)]

    def consider(name,build,cached=False):
        nonlocal best,selected
        t=time.perf_counter();candidate=build();elapsed=time.perf_counter()-t
        trials.append(dict(name=name,size=len(candidate),encode_seconds=elapsed,cache_used=cached))
        if len(candidate)<len(best):best,selected=candidate,name

    def legacy():
        if legacy_cache is not None:return legacy_cache
        from benchmarks.native_ppm import enable
        from benchmarks import rounded_mixer,mixer_rounded_bounded
        from benchmarks.joint_bounded import encode as original
        enable();mixer_rounded_bounded.encode_mixer=rounded_mixer.native_encoder()
        return original(data)

    consider('joint-ppm-mixer',legacy,legacy_cache is not None)
    for index,region in enumerate(spatial.regions(data)):
        for backend,effort in (('jxl',7),('jxl',10),('jls',0),('j2k',0)):
            consider(f'image-{index}-{backend}-{effort}',lambda:spatial.encode_region(data,region,backend,effort))
        if region['height']>region['slice_height']:
            for mode,effort in [(m,9) for m in range(6)]+[(3,10)]:
                consider(f'volume-{index}-{mode}-{effort}',lambda:volume.encode(data,region,mode,effort))
    if paq is not None:
        version,options=paq
        consider(f'paq-{version}-{options}',lambda:wrap_paq(paq_cache,version) if paq_cache is not None else encode_paq(data,version,options),paq_cache is not None)
    elif paq_cache is not None:raise ValueError('PAQ cache requires a configured version and options')
    return best,dict(selected=selected,trials=trials)
