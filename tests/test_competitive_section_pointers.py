import json
from pathlib import Path
import pytest
from benchmarks import competitive_section_pointers as profile
from tests.test_ecoff_relocated_pointers import archive


def test_uncached_pointer_choices_and_full_qualification(tmp_path):
    data=archive();candidates=profile.additions(data)
    assert len(candidates)==7 and profile.additions(b'plain bytes')==[]
    for frame,_,_ in candidates:assert profile.decode(frame)==data
    frame,stats=profile.framed.encode(data,4,'brotli')
    sha=profile.sha;row=dict(stats,round_trip=True,complete_silesia_member=False,input_sha256=sha(data),restored_sha256=sha(data),
        physical_bytes=len(frame),frame_sha256=sha(frame),source_hashes={str(Path(profile.framed.codec.__file__)):sha(Path(profile.framed.codec.__file__).read_bytes())},
        backend='brotli',backend_sha256=sha(Path(profile._brotli.__file__).read_bytes()),brotli_version=profile.brotli.__version__,decode_seconds=.01)
    (tmp_path/'complete.json').write_text(json.dumps(row));(tmp_path/'stream.cixb').write_bytes(frame)
    with pytest.raises(ValueError,match='evidence mismatch'):profile.qualify(data,tmp_path)
    qualified,proof=profile.qualify(data,tmp_path,require_complete=False)
    assert qualified==frame and proof['fresh_full_decode']
    with pytest.raises(ValueError,match='evidence mismatch'):profile.qualify(data+b'wrong',tmp_path,False)
    with pytest.raises(ValueError,match='all seven'):profile.additions(data,tmp_path)
    (tmp_path/'stream.cixb').write_bytes(frame+b'bad')
    with pytest.raises(ValueError,match='artifact mismatch'):profile.qualify(data,tmp_path,False)
