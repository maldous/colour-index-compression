import os
from pathlib import Path
import random
import subprocess
import pytest
from benchmarks import paq_register_prior_probe as codec
from benchmarks.ecoff_register_ranks import register_fields
from benchmarks.paq_register_screen import Prior
from tests.test_paq_memory_feedback import memory_fixture


def test_cpp_prior_matches_causal_oracle_all_opcodes_and_block_resets(tmp_path):
    header = codec.ROOT/'benchmarks/native/CixRegisterPrior.hpp'
    source = tmp_path/'main.cpp';binary = tmp_path/'prior'
    source.write_text('#include "'+str(header)+'"\n#include <iostream>\n'
        'int main(){ CixRegisterPrior p; unsigned b,pos,pred,y; '
        'while(std::cin>>b>>pos>>pred>>y){std::cout<<p.mix(pred,true,b,pos)<<"\\n";p.observe(y);}}\n')
    subprocess.run(['g++','-O2','-std=c++17',str(source),'-o',str(binary)],check=True)
    rng=random.Random(971);inputs=[];expected={m:[] for m in range(4)}
    for block in range(2):
        prior=Prior(0)
        words=[(op<<26)|rng.getrandbits(26) for _ in range(8) for op in range(64)]
        for wi,word in enumerate(words):
            fields={27-shift:(shift,ns) for shift,_,_,ns in register_fields(word)}
            active=None
            for position in range(32):
                if position in fields:
                    shift,ns=fields[position];active=(position,shift,ns,prior.weights((ns,)))
                y=(word>>(31-position))&1;p=rng.choice([1,1<<26,31*(1<<26),0x7fffffff,rng.randrange(1,1<<31)])
                inputs.append(f'{wi*4+position//8} {position%8} {p} {y}\n')
                for mode in range(4):
                    result=p
                    if active and mode and (mode==3 or 1/32<=p/(1<<31)<=31/32):
                        start,shift,ns,weights=active;bits=position-start
                        value=(word>>shift)&31;prefix=value>>(5-bits)
                        lo=prefix<<(5-bits);mid=lo+(1<<(4-bits));hi=lo+(1<<(5-bits))
                        q=(sum(weights[mid:hi])<<31)//sum(weights[lo:hi]);d=32 if mode==2 else 8
                        result=max(1,min(0x7fffffff,((d-1)*p+q+d//2)//d))
                    expected[mode].append(result)
                if active and position==active[0]+4:
                    _,shift,ns,_=active;prior.observe((ns,),(word>>shift)&31);active=None
    for mode in range(4):
        env=codec.environment(mode)
        actual=subprocess.check_output([str(binary)],input=''.join(inputs),text=True,env=env)
        assert list(map(int,actual.split()))==expected[mode]


@pytest.mark.skipif(not codec.FORK.exists(),reason='isolated register-prior build required')
def test_native_control_and_all_register_modes_restore():
    data=memory_fixture();hashes={}
    for mode in (4,0,1,2,3):
        frame,stats=codec.encode(data,mode,'-4');assert codec.decode(frame)==data
        hashes[mode]=stats['paq_sha256']
    assert hashes[0]==hashes[4]
    assert all(hashes[m]!=hashes[0] for m in (1,2,3))
