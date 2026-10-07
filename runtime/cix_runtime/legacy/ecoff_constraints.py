"""Predict ECOFF hash and msym tables from transmitted symbols and relocations.

Tables are replaced by zeros only after exact equality with the reconstruction.
Unrecognized/noncanonical data remains literal. File positions and executable
headers remain intact, preserving the backend's instruction-model detection.
Layout reference: Tru64 UNIX Object File and Symbol Table Specification, ch.14.
"""
import struct
import tarfile
from .multinomial import vencode,vdecode

TRAILER=b'ECFX1'


def _valid_header(count, optional, flags, end, length):
    return optional == 80 and 1 <= count <= 256 and end <= length and flags in (0x2005, 0x2007, 0x3007)


def _header(data):
    if len(data) < 104 or data[:2] != b'\x83\x01':
        raise ValueError('not Alpha ECOFF')
    _, count, _, _, _, optional, flags = struct.unpack_from('<HHIQIHH', data)
    end = 24 + optional + count * 64
    if not _valid_header(count, optional, flags, end, len(data)):
        raise ValueError('unsupported ECOFF header')
    return count, end


def _section_descriptor(data, position, end):
    name, _, _, size, offset, _, _, _, _, _ = struct.unpack_from('<8sQQQQQQHHI', data, position)
    if offset and (offset < end or offset + size > len(data)):
        raise ValueError('ECOFF section outside input')
    return name.rstrip(b'\0'), offset, size


def sections(data):
    count, end = _header(data)
    out = {}
    ranges = []
    for index in range(count):
        name, offset, size = _section_descriptor(data, 104 + index * 64, end)
        if name in out:
            raise ValueError('duplicate ECOFF section')
        if offset and size:
            ranges.append((offset, offset + size))
        if offset:
            out[name] = (offset, size)
    ranges.sort()
    if any(left[1] > right[0] for left, right in zip(ranges, ranges[1:])):
        raise ValueError('overlapping ECOFF sections')
    return out


def _standalone_object(data):
    try:
        sections(data)
    except (ValueError, struct.error):
        return None
    return [(0, len(data))]


def _tar_member(data, position):
    block = data[position:position + 512]
    if not any(block):
        return None
    try:
        header = tarfile.TarInfo.frombuf(block, 'utf-8', 'surrogateescape')
    except (tarfile.HeaderError, ValueError):
        return None
    payload_start = position + 512
    end = payload_start + header.size
    if header.size < 0 or end > len(data):
        return None
    next_position = payload_start + ((header.size + 511) // 512) * 512
    return header, payload_start, end, next_position


def _tar_objects(data):
    out = []; position = 0
    while position + 512 <= len(data):
        member = _tar_member(data, position)
        if member is None:
            break
        header, payload_start, end, position = member
        if header.isfile():
            try:
                sections(data[payload_start:end])
            except (ValueError, struct.error):
                continue
            out.append((payload_start, header.size))
    return out


def objects(data):
    standalone = _standalone_object(data)
    return standalone if standalone is not None else _tar_objects(data)


def name_hash(name):
    value=0
    for byte in name:
        value=(value<<4)+byte;high=value&0xf0000000
        value^=high>>24;value&=~high
    return value


def _hash_names(data, soff, tsize, toff, n):
    hashes = []
    for index in range(n):
        offset = struct.unpack_from('<I', data, soff + index * 24)[0]
        if offset >= tsize:
            return None
        end = data.find(b'\0', toff + offset, toff + tsize)
        if end < 0:
            return None
        hashes.append(name_hash(data[toff + offset:end]))
    return hashes


def _hash_table(hashes, buckets):
    heads = [0] * buckets; chains = [0] * len(hashes)
    for index in range(len(hashes) - 1, 0, -1):
        bucket = hashes[index] % buckets; chains[index] = heads[bucket]; heads[bucket] = index
    return struct.pack('<' + 'I' * (buckets + len(hashes)), *heads, *chains)


def _msym_prediction(data, sec, hashes, n):
    if b'.msym' not in sec or b'.rel.dyn' not in sec:
        return None
    moff, msize = sec[b'.msym']; roff, rsize = sec[b'.rel.dyn']
    if msize < n * 8 or rsize % 16:
        return None
    first = [0] * n
    for index in range(1, rsize // 16):
        info = struct.unpack_from('<I', data, roff + 16 * index + 8)[0]; symbol = info >> 8
        if info and symbol < n and not first[symbol]:
            first[symbol] = index
    if max(first, default=0) >= 1 << 24:
        return None
    return moff, b''.join(struct.pack('<II', hashes[index], first[index] << 8) for index in range(n))


def predicted(data):
    sec = sections(data)
    if not all(key in sec for key in (b'.hash', b'.dynsym', b'.dynstr')):
        return []
    hoff, hsize = sec[b'.hash']; soff, ssize = sec[b'.dynsym']; toff, tsize = sec[b'.dynstr']
    if hsize < 8:
        return []
    buckets, n = struct.unpack_from('<II', data, hoff)
    if not buckets or not n or 8 + 4 * (buckets + n) > hsize or n * 24 > ssize:
        return []
    hashes = _hash_names(data, soff, tsize, toff, n)
    if hashes is None:
        return []
    result = [(1, hoff + 8, _hash_table(hashes, buckets))]
    msym = _msym_prediction(data, sec, hashes, n)
    if msym is not None:
        result.append((2, *msym))
    return result


def transform(data,mode=3):
    if mode not in range(4):raise ValueError('invalid ECOFF constraint policy')
    transformed=bytearray(data);changes=[];stats={'objects':0,'hash_tables':0,'msym_tables':0,'derived_bytes':0}
    for offset,size in objects(data):
        stats['objects']+=1;mask=0;original=data[offset:offset+size]
        for bit,start,expected in predicted(original):
            if mode&bit and original[start:start+len(expected)]==expected:
                transformed[offset+start:offset+start+len(expected)]=bytes(len(expected));mask|=bit
                stats['hash_tables' if bit==1 else 'msym_tables']+=1;stats['derived_bytes']+=len(expected)
        if mask:changes.append((offset,size,mask))
    metadata=bytearray(vencode(len(changes)));previous_end=0
    for offset,size,mask in changes:
        metadata.extend(vencode(offset-previous_end));metadata.extend(vencode(size));metadata.append(mask);previous_end=offset+size
    raw=bytes(transformed)+metadata+len(metadata).to_bytes(8,'little')+TRAILER
    return raw,dict(**stats,mode=mode,original_bytes=len(data),transformed_bytes=len(raw),constraint_metadata_bytes=len(metadata)+13)


def _restore_object(data, offset, size, mask):
    candidates = predicted(bytes(data[offset:offset + size])); seen = 0
    for bit, where, expected in candidates:
        if mask & bit:
            field = data[offset + where:offset + where + len(expected)]
            if any(field):
                raise ValueError('derived ECOFF field is not zero')
            data[offset + where:offset + where + len(expected)] = expected; seen |= bit
    if seen != mask:
        raise ValueError('ECOFF dependencies missing')


def _descriptor(meta, pos, previous_end, data_length):
    delta, pos = vdecode(meta, pos); size, pos = vdecode(meta, pos); offset = previous_end + delta
    if pos >= len(meta):
        raise ValueError('missing ECOFF constraint mask')
    mask = meta[pos]; pos += 1
    if mask not in (1, 2, 3) or offset + size > data_length:
        raise ValueError('invalid ECOFF constraint descriptor')
    return offset, size, mask, pos


def inverse(raw):
    if len(raw) < 14 or raw[-5:] != TRAILER:
        raise ValueError('invalid ECOFF constraint trailer')
    length = int.from_bytes(raw[-13:-5], 'little'); start = len(raw) - 13 - length
    if start < 0:
        raise ValueError('ECOFF metadata outside frame')
    data = bytearray(raw[:start]); meta = raw[start:-13]; n, pos = vdecode(meta, 0); previous_end = 0
    if n > len(data) // 104:
        raise ValueError('excessive ECOFF object count')
    for _ in range(n):
        offset, size, mask, pos = _descriptor(meta, pos, previous_end, len(data))
        _restore_object(data, offset, size, mask); previous_end = offset + size
    if pos != len(meta):
        raise ValueError('unused ECOFF metadata')
    return bytes(data)
