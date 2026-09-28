from pathlib import Path
import pytest
from benchmarks import ecoff_filtered as codec
from tests.test_ecoff_section_pointers import object_file


@pytest.mark.parametrize('mode', range(3))
def test_fresh_native_filter_frames_restore_empty_literal_and_structural_inputs(mode):
    if not codec.FORK.exists(): pytest.skip('isolated stored-state decoder not built')
    for data in [b'',bytes(range(256))*3,object_file()]:
        frame,_=codec.encode(data,mode)
        assert codec.decode(frame)==data
        corrupted=bytearray(frame);corrupted[7]^=1
        with pytest.raises((ValueError,RuntimeError)):codec.decode(bytes(corrupted))
