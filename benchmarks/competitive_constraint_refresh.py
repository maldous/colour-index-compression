"""Add completed textual geometry and PAQ-backed database constraints."""
import json
import subprocess
import sys
import tempfile
import time
import zlib
from pathlib import Path
from cix.multinomial import vencode, vdecode
from benchmarks import competitive_small_paq as parent
from benchmarks import competitive_chemical as chemical
from benchmarks import competitive_database_portfolio as database
from benchmarks import mysql_record_constraints as records, mysql_record_probe as record_probe
from benchmarks import sdf_geometry as geometry, sdf_geometry_probe as framed
from benchmarks.competitive_codec import sha, paq_binary, unwrap_paq

NAME = 'CIX competitive PAQ/structural constraint portfolio 8'
SOURCES = [__file__, record_probe.__file__]


def encode_geometry(data, options='-8'):
    transformed, _ = geometry.encode(data, 2, 1)
    with tempfile.TemporaryDirectory(prefix='cix-coordinate-text-') as folder:
        source = Path(folder)/'input.sdfg'
        archive = Path(folder)/'stream.paq8px215'
        source.write_bytes(transformed)
        subprocess.run([paq_binary('v215'), options, '-simd', 'AVX2', str(source), str(archive)],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return framed.MAGIC+vencode(len(data))+zlib.crc32(data).to_bytes(4, 'big')+archive.read_bytes()


def qualify(data, folder, kind, options='-8', require_complete=True):
    folder = Path(folder)
    record = folder/'complete.json'
    row = json.loads(record.read_text())
    if not row.get('round_trip') or (require_complete and not row.get('complete_silesia_member')):
        raise ValueError('incomplete constraint trial')
    if row['offset'] != 0 or row['original_bytes'] != len(data) or row['input_sha256'] != sha(data):
        raise ValueError('constraint input mismatch')
    binary_hash = sha(Path(paq_binary('v215')).read_bytes())
    if kind == 'geometry':
        if (row['mode'], row['representation'], row['options']) != (2, 1, options):
            raise ValueError('geometry policy mismatch')
        if row['codec_source_sha256'] != sha(Path(geometry.__file__).read_bytes()) or row['backend_sha256'] != binary_hash:
            raise ValueError('geometry implementation changed')
        frame = (folder/'stream.cixg').read_bytes()
        if frame[:5] != framed.MAGIC:
            raise ValueError('geometry magic mismatch')
        n, pos = vdecode(frame, 5)
        if frame[pos+4:] != (folder/'stream.paq8px215').read_bytes():
            raise ValueError('geometry archive mismatch')
        raw, _ = geometry.encode(data, 2, 1)
        if sha(raw) != row['transformed_sha256'] or raw != (folder/'input.sdfg').read_bytes() or geometry.decode(raw) != data:
            raise ValueError('geometry transform mismatch')
        decoder_source = framed.__file__
    elif kind == 'database':
        if (row['mode'], row['backend'], row['paq_options']) != (3, 1, options):
            raise ValueError('database policy mismatch')
        if row['paq_binary_sha256'] != binary_hash or row['restored_sha256'] != sha(data):
            raise ValueError('database backend or restoration mismatch')
        for path, digest in row['source_hashes'].items():
            if sha(Path(path).read_bytes()) != digest:
                raise ValueError('database codec changed')
        # The original verifier checked these source hashes before and after its
        # independent extraction. Also require its exact committed implementation.
        relative = str(Path(record_probe.__file__).resolve().relative_to(Path.cwd()))
        historical = subprocess.check_output(['git', 'show', row['revision']+':'+relative])
        if historical != Path(record_probe.__file__).read_bytes():
            raise ValueError('database verifier changed')
        frame = (folder/'stream.cixd').read_bytes()
        if frame[:6] != records.MAGIC+b'\x01':
            raise ValueError('database magic mismatch')
        n, pos = vdecode(frame, 6)
        if unwrap_paq(frame[pos+4:])[0] != 'v215':
            raise ValueError('database archive version mismatch')
        raw, _ = records.transform(data, 3)
        if len(raw) != row['transformed_bytes'] or records.inverse(raw) != data:
            raise ValueError('database structural inversion failed')
        decoder_source = records.__file__
    else:
        raise ValueError('unknown constraint kind')
    if n != len(data) or int.from_bytes(frame[pos:pos+4], 'big') != zlib.crc32(data):
        raise ValueError('constraint source framing mismatch')
    if len(frame) != row['physical_bytes'] or sha(frame) != row['frame_sha256']:
        raise ValueError('constraint physical artifact changed')
    proof = dict(kind='completed independent full-frame decode reused', measurement=row,
        measurement_path=str(record.resolve()), measurement_sha256=sha(record.read_bytes()),
        decoder_source_sha256=sha(Path(decoder_source).read_bytes()),
        structural_stage_recomputed_and_inverted=True, transformed_sha256=sha(raw),
        frame_sha256=sha(frame), input_sha256=sha(data))
    return frame, proof


def additions(data, cache=None):
    start = time.perf_counter()
    proof = None
    if chemical.recognizes(data):
        kind, subdir = 'geometry', 'sdf-geometry-paq-full8/2-1'
        if cache: frame, proof = qualify(data, Path(cache)/subdir, kind)
        else: frame = encode_geometry(data)
        name = 'bonded-coordinate-text-paq-v215-8'
    elif database.recognizes(data):
        kind, subdir = 'database', 'mysql-record-paq-full8/0-3-1'
        if cache: frame, proof = qualify(data, Path(cache)/subdir, kind)
        else: frame, _ = records.encode(data, 3, 1, '-8')
        name = 'database-remaining-count-paq-v215-8'
    else:
        return []
    return [(frame, dict(name=name, size=len(frame), encode_seconds=time.perf_counter()-start), proof)]


def encode(data, **kwargs):
    frame, selection = parent.encode(data, **kwargs)
    for candidate, row, _ in additions(data):
        selection['trials'].append(row)
        if len(candidate) < len(frame):
            frame = candidate
            selection['selected'] = row['name']
    return frame, selection


def decode(frame):
    return parent.decode(frame)


if __name__ == '__main__':
    from benchmarks.competitive_certified import main
    main(sys.modules[__name__])
