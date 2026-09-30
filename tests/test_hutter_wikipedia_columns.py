import pytest
from benchmarks import hutter_wikipedia_columns as codec


def fixture():
    return b'head\0<page>' + b''.join((b'<page><title>T&amp;%d</title><id>00007</id><revision><id>09</id><timestamp>2006-03-01T00:00:00Z</timestamp><contributor><id>07</id><username>X</username></contributor><text xml:space="preserve">same words &lt;b&gt;\n\0</text></revision></page>\n' % (i%3)) for i in range(1100)) + b'<page><title>partial'


@pytest.mark.parametrize('mode',codec.MODES)
def test_independent_frame_blocks_and_exact_reconstruction(mode):
    data=fixture();frame,stats=codec.encode(data,mode)
    assert codec.decode(frame)==data
    assert stats['physical_bytes']==len(frame)==sum(stats[k] for k in ('descriptor_bytes','dictionary_bytes','literal_bytes','column_stream_bytes','framing_bytes'))
    with pytest.raises((ValueError,IndexError)):codec.decode(frame[:-1])


def test_profile_cost_conservation_and_prose_exclusion():
    data=fixture();report=codec.profile(data)
    assert sum(r['original_value_bytes'] for r in report['field_classes'])+report['shared_structure_and_literal_original_bytes']==len(data)
    for mode in codec.MODES:
        assert sum(r['complete_column_bytes'][mode] for r in report['field_classes'])+report['shared_structure_and_literal_encoded_bytes'][mode]==len(codec.encode(data,mode)[0])
    for col in report['columns']:
        if col['field_class']=='articletext':
            assert not col['eligible_short_field']
            assert all(b['actual_mode']=='raw' for b in col['candidates']['rank']['blocks'])
