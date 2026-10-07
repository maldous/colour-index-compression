import pytest
from cix_runtime import backends


def test_rejects_unknown_backend():
    with pytest.raises(ValueError):
        backends.paq_binary('unknown')


def test_rejects_malformed_cixp():
    with pytest.raises(ValueError):
        backends.decode_paq(b'broken', 1, backends.PAQ_DECODE_MINIMUM_MEMORY)


def test_rejects_unknown_native_profile_before_execution():
    with pytest.raises(ValueError):
        backends.native_encode(b'x', profile='unknown')


def test_paq_pre_admission_precedes_backend_execution():
    frame = backends._wrap(b'paq8pxpayload', 'v215')
    with pytest.raises(ValueError, match='conservative'):
        backends.decode_paq(frame, 1, backends.PAQ_DECODE_MINIMUM_MEMORY - 1)


def test_frame_roundtrip_contract():
    raw=b'paq8pxpayload'
    assert backends._unwrap(backends._wrap(raw,'v215')) == ('v215',raw)


def test_legacy_paq_pre_admission_precedes_backend_execution():
    from cix_runtime.legacy import executable

    with pytest.raises(ValueError, match='conservative'):
        executable._run_paq(
            b'not-an-archive',
            'store-state',
            '',
            decode=True,
            max_output_bytes=1,
            memory_bytes=backends.PAQ_DECODE_MINIMUM_MEMORY - 1,
        )
