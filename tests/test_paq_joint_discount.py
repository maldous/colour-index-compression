import math
import random
import subprocess
import pytest
from benchmarks import paq_joint_discount_probe as codec, register_discount_math as oracle
from benchmarks.ecoff_register_ranks import register_fields
from benchmarks.paq_register_screen import Prior
from benchmarks import paq_joint_log_probe as previous
from tests.test_paq_memory_feedback import memory_fixture


def test_cpp_helper_matches_independent_integer_oracle(tmp_path):
    source=tmp_path/'main.cpp';binary=tmp_path/'prior';header=codec.ROOT/'benchmarks/native/CixDiscountRegisterPrior.hpp'
    source.write_text('#include "'+str(header)+'"\n#include <iostream>\n'
        'int main(){ CixRegisterPrior p; unsigned b,pos,pred,y; '
        'while(std::cin>>b>>pos>>pred>>y){std::cout<<p.mix(pred,true,b,pos)<<"\\n";p.observe(y);}}\n')
    subprocess.run(['g++','-O2','-std=c++17',str(source),'-o',str(binary)],check=True)
    rng=random.Random(903);inputs=[];expected={m:[] for m in range(4)}
    for block in range(2):
        prior=Prior(0);models={m:{} for m in (1,2,3)}
        words=[(op<<26)|rng.getrandbits(26) for _ in range(6) for op in range(64)]
        for wi,word in enumerate(words):
            fields={27-shift:(shift,ns) for shift,_,_,ns in register_fields(word)};active=None
            for position in range(32):
                if position in fields:
                    shift,ns=fields[position];active=(position,shift,ns,prior.weights((ns,)))
                y=(word>>(31-position))&1;p=rng.choice([1,1<<26,31*(1<<26),0x7fffffff,rng.randrange(1,1<<31)])
                inputs.append(f'{wi*4+position//8} {position%8} {p} {y}\n')
                for mode in range(4):
                    result=p
                    if active and mode and (1<<26)<=p<=31*(1<<26):
                        start,shift,ns,weights=active;bits=position-start;value=(word>>shift)&31
                        prefix=value>>(5-bits);lo=prefix<<(5-bits);mid=lo+(1<<(4-bits));hi=lo+(1<<(5-bits))
                        q=(sum(weights[mid:hi])<<31)//sum(weights[lo:hi])
                        key=(word>>26,start)
                        if key not in models[mode]:models[mode][key]=oracle.DiscountPosterior({1:0,2:5,3:7}[mode])
                        model=models[mode][key];experts=[p]+[((d-1)*p+q+d//2)//d for d in (128,32,8,2)]
                        result=model.mix(experts);model.observe(experts,y)
                    expected[mode].append(result)
                if active and position==active[0]+4:
                    _,shift,ns,_=active;prior.observe((ns,),(word>>shift)&31);active=None
    for mode in range(4):
        actual=subprocess.check_output([str(binary)],input=''.join(inputs),text=True,env=codec.environment(mode))
        assert list(map(int,actual.split()))==expected[mode]


@pytest.mark.parametrize('shift',(5,7))
def test_discounts_bound_evidence_and_adapt_to_a_reversed_regime(shift):
    model=oracle.DiscountPosterior(shift);persistent=oracle.DiscountPosterior(0)
    p=int(0.9*(1<<31));q=int(0.1*(1<<31));experts=[p,q,q,q,q]
    costs=[0.,0.]
    for i,y in enumerate([0]*2000+[1]*2000):
        for j,m in enumerate((model,persistent)):
            r=m.mix(experts)
            assert 0<r<(1<<31)
            if i>=2000:costs[j]-=math.log2((r if y else (1<<31)-r)/(1<<31))
            m.observe(experts,y)
        assert max(model.scores)==0
        assert min(model.scores)>=-31*(1<<shift)*(1<<20)
    assert costs[0]<costs[1]
    before=model.scores[:];model.observe([p]*5,1);assert model.scores==before


@pytest.fixture(scope='module')
def streams():
    if not codec.FORK.exists():pytest.skip('isolated joint discount build required')
    data=memory_fixture();return data,{m:codec.encode(data,m,'-4') for m in (4,0,1,2,3)}


@pytest.mark.parametrize('mode',(4,0,1,2,3))
def test_native_modes_restore(streams,mode):
    data,frames=streams;assert codec.decode(frames[mode][0])==data


def test_disabled_and_persistent_modes_preserve_exact_prior_payloads(streams):
    data,frames=streams
    assert frames[0][1]['paq_sha256']==frames[4][1]['paq_sha256']
    _,stats=previous.encode(data,3,'-4')
    assert frames[1][1]['paq_sha256']==stats['paq_sha256']
