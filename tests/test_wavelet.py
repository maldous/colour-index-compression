import os
import random

from cix.multinomial import StreamConfig, compress, decompress
from cix.wavelet import decode_wavelet, encode_wavelet, estimate_wavelet_bits


def test_wavelet_round_trip():
    rng=random.Random(20260927)
    for n,alpha in ((1,2),(17,5),(1024,256),(4096,16)):
        data=bytes(rng.randrange(alpha) for _ in range(n))
        blob=encode_wavelet(data)
        assert decode_wavelet(blob,len(data))==data
        assert estimate_wavelet_bits(data)>=0


def test_wavelet_integrates_without_harming_random_fallback():
    data=os.urandom(4096)
    cfg=StreamConfig(
        min_block=2048,
        max_block=4096,
        chunk_mode="fixed",
        enable_lz=False,
        enable_bwt=False,
        enable_transforms=False,
        enable_bitplanes=False,
        enable_chains=False,
        enable_numeric=False,
        enable_dedup=False,
        enable_adaptive=False,
        enable_sparse=False,
        enable_runs=False,
        enable_persistent_adaptive=False,
        enable_record=False,
        enable_periodic=False,
        enable_ppm=False,
        enable_expert_mix=False,
        enable_wavelet=True,
        context_models=(),
    )
    blob=compress(data,cfg)
    assert decompress(blob)==data
    assert len(blob)<=len(data)+64
