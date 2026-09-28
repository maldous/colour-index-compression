import struct
from benchmarks import competitive_grid_refresh as codec
from tests.test_competitive_codec import legacy_raw


def test_additive_portfolio_round_trip_and_actual_selection():
    for data in (b'plain bytes'*80,struct.pack('<7i',0,1,80,0,1,1,28)+bytes(28*80)):
        frame,selection=codec.encode(data,legacy_cache=legacy_raw(data))
        assert len(frame)==min(row['size'] for row in selection['trials'])
        assert codec.decode(frame)==data
