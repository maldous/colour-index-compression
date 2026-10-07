import json
from pathlib import Path
import pytest
from benchmarks import competitive_filtered as profile, ecoff_filtered_probe as probe
from tests.test_ecoff_section_pointers import object_file


def test_filter_qualification_requires_complete_identity_and_real_decode(tmp_path):
    data=object_file();source=tmp_path/'fixture.tar';source.write_bytes(data)
    assert profile.eligible(data)
    row=probe.worker((str(source),1,str(tmp_path),False));folder=tmp_path/'fixture-1'
    assert profile.additions(b'plain input')==[]
    with pytest.raises(ValueError,match='evidence mismatch'):profile.qualify(data,folder)
    frame,proof=profile.qualify(data,folder,False)
    assert proof['fresh_full_decode'] and profile.decode(frame)==data
    with pytest.raises(ValueError,match='evidence mismatch'):profile.qualify(data+b'x',folder,False)
    with pytest.raises(ValueError,match='all three'):profile.additions(data,tmp_path)
    (folder/'stream.cixb').write_bytes(frame+b'broken')
    with pytest.raises(ValueError,match='artifact mismatch'):profile.qualify(data,folder,False)
