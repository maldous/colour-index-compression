from benchmarks.paq_register_screen import Prior


def test_unseen_symbols_remain_possible_and_updates_use_only_completed_values():
    for mode in range(4):
        p=Prior(mode);key=p.key(0,'Mem','Ra',0x29);before=p.weights(key)
        assert before==[1]*32 and p.weights(key)==before
        p.observe(key,27);after=p.weights(key)
        assert min(after)>0 and after[27]>after[0]
        p.observe(key,3)
        if mode<2:assert p.weights(key)[3]>p.weights(key)[27]
        else:
            for _ in range(600):p.observe(key,3)
            assert min(p.weights(key))>0
