import random
from benchmarks.paq_field_composition_screen import labels,rank_bytes
from benchmarks.paq_cix_residual import rank_binary


def test_labels_do_not_consume_current_or_future_bits():
    rng=random.Random(1307)
    for op in range(64):
        for _ in range(5):
            word=(op<<26)|rng.getrandbits(26)
            for pos in range(32):
                prefix=word&((0xffffffff<<(32-pos))&0xffffffff)
                assert labels(word,pos)==labels(prefix,pos)


def test_exact_width_matches_existing_type_class_encoder():
    rng=random.Random(17)
    for n in (0,1,2,17,128,1000):
        for rate in (0,0.03,0.5,1):
            bits=bytes(int(rng.random()<rate) for _ in range(n))
            assert rank_bytes(n,sum(bits))==len(rank_binary(bits))
