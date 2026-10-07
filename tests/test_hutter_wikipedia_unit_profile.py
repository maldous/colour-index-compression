from benchmarks.hutter_wikipedia_unit_profile import lexical_windows, newline4096, paragraphs16384, profile, sentence_clauses


def _data(body):
    return b"<page><text xml:space=\"preserve\">"+body+b"</text></page>"


def test_generators_preserve_raw_unit_spans_and_nonoverlap():
    raw=(b"This is a sufficiently long sentence with [[Town-A]] and 101 people in its record. "
         b"Another long clause mentions https://example.test/a and 202 houses.\n\n"
         b"This is another sufficiently long sentence with [[Town-B]] and 303 people.\n")
    data=_data(raw)
    for generator in (newline4096,paragraphs16384,sentence_clauses):
        units=list(generator(data)); assert units
        assert all(data[start:stop]==value for start,stop,_bid,value in units)
    units=list(lexical_windows(data,32))
    assert all(data[start:stop]==value for start,stop,_bid,value in units)
    assert all(left[1]<=right[0] for left,right in zip(units,units[1:]))


def test_profile_labels_estimates_as_preencoding_not_gain():
    line=b"This is a long enough repeated literal relation with [[Town-X]] and number 101 in the source.\n"
    data=b''.join(_data(line.replace(b'101',str(n).encode())) for n in (101,202,303))
    result=profile(data)
    assert result['newline_4096']['metadata_and_payload']=='NOT_MEASURED_PREENCODING_NOT_GAIN'
    assert result['newline_4096']['selected_families']==1
    assert result['lexical_window_32']['overlap_policy'].startswith('units are non-overlapping')
