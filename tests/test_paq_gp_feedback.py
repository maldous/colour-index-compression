import struct
import pytest
from benchmarks import paq_gp_feedback_probe as codec
from tests.test_ecoff_symbol_loads import object_file


def instruction_fixture():
    source = object_file(); sections = []
    for i in range(struct.unpack_from('<H',source,2)[0]):
        name, _, virtual, size, offset, _, _, _, _, flags = struct.unpack_from('<8sQQQQQQHHI',source,104+64*i)
        raw = source[offset:offset+size]
        if name.rstrip(b'\0') == b'.text':
            words = []
            for i in range(768):
                displacement = [-32752,-32744,-32736,-32752][i%4]
                words += [(0x29<<26)|(27<<21)|(29<<16)|(displacement&65535), 0x47ff041f]
            raw = struct.pack('<'+'I'*len(words),*words)
        sections.append((name,virtual,raw,flags))
    _, virtual, raw, _ = sections[-1]
    sections.extend([(b'.init',virtual+len(raw),struct.pack('<I',0x47ff041f),0),
                     (b'.fini',virtual+len(raw)+4,struct.pack('<I',0x47ff041f),0)])
    out = bytearray(source[:104]+bytes(64*len(sections)));struct.pack_into('<H',out,2,len(sections))
    for i,(name,virtual,raw,flags) in enumerate(sections):
        start=len(out);out.extend(raw)
        struct.pack_into('<8sQQQQQQHHI',out,104+64*i,name,virtual,virtual,len(raw),start,0,0,0,0,flags)
    return bytes(out)


@pytest.mark.skipif(not codec.FORK.exists(),reason='isolated experimental PAQ build required')
def test_disabled_control_is_exact_and_causal_modes_restore():
    data=instruction_fixture();payloads={}
    for mode in [4,0,1,2,3]:
        frame,stats=codec.encode(data,mode,'-4');assert codec.decode(frame)==data
        payloads[mode]=stats['paq_sha256']
    assert payloads[0]==payloads[4]
    assert all(payloads[mode]!=payloads[0] for mode in (1,2,3))


def test_invalid_mode_rejected_before_execution():
    with pytest.raises(ValueError):codec.encode(b'',9)
    with pytest.raises(ValueError):codec.decode(codec.MAGIC+b'\x09'+bytes(10))
