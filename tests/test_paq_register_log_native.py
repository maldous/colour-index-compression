import math
import random
import subprocess
import pytest
from benchmarks import paq_register_log_probe as codec, register_log_math as oracle
from benchmarks.ecoff_register_ranks import register_fields
from benchmarks.paq_register_screen import Prior
from benchmarks import paq_register_prior_probe as old
from tests.test_paq_memory_feedback import memory_fixture


def test_integer_tables_cover_extremes_and_approximate_log_weights():
    logs,exps=oracle.tables()
    assert (logs[0],logs[-1],exps[0],exps[-1])==(0,1<<30,1<<48,1<<47)
    assert all(a<b for a,b in zip(logs,logs[1:]))
    assert all(a>b for a,b in zip(exps,exps[1:]))
    rng=random.Random(73)
    for p in [1,1<<31,(1<<31)-1,*[rng.randrange(1,1<<31) for _ in range(10000)]]:
        assert abs(oracle.log_probability(p)-math.log2(p/(1<<31))*oracle.SCALE)<=1
    for deficit in [0,48*oracle.SCALE,49*oracle.SCALE,64*oracle.SCALE,*[rng.randrange(64*oracle.SCALE) for _ in range(10000)]]:
        exact=2**(-deficit/oracle.SCALE)*(1<<48)
        assert abs(oracle.coding_weight(deficit)-exact)<=exact*1e-8+1


def test_cpp_helper_matches_independent_integer_oracle(tmp_path):
    source=tmp_path/'main.cpp';binary=tmp_path/'prior';header=codec.ROOT/'benchmarks/native/CixLogRegisterPrior.hpp'
    source.write_text('#include "'+str(header)+'"\n#include <iostream>\n'
        'int main(){ CixRegisterPrior p; unsigned b,pos,pred,y; '
        'while(std::cin>>b>>pos>>pred>>y){std::cout<<p.mix(pred,true,b,pos)<<"\\n";p.observe(y);}}\n')
    subprocess.run(['g++','-O2','-std=c++17',str(source),'-o',str(binary)],check=True)
    rng=random.Random(903);inputs=[];expected={m:[] for m in range(4)}
    for block in range(2):
        prior=Prior(0);models={m:{} for m in (1,2)}
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
                        if mode==3:result=(7*p+q+4)//8
                        else:
                            key=(word>>26,start)
                            if key not in models[mode]:models[mode][key]=oracle.TablePosterior(native_bias=8 if mode==2 else 1)
                            model=models[mode][key];experts=[p]+[((d-1)*p+q+d//2)//d for d in (128,32,8,2)]
                            result=model.mix(experts);model.observe(experts,y)
                    expected[mode].append(result)
                if active and position==active[0]+4:
                    _,shift,ns,_=active;prior.observe((ns,),(word>>shift)&31);active=None
    for mode in range(4):
        actual=subprocess.check_output([str(binary)],input=''.join(inputs),text=True,env=codec.environment(mode))
        assert list(map(int,actual.split()))==expected[mode]


def test_integer_log_state_retains_long_evidence():
    model=oracle.TablePosterior();p=int(0.9*(1<<31));q=int(0.1*(1<<31));experts=[p,q,q,q,q]
    losses=[0.,0.];mixed=0.
    for y in [0]*300+[1]*600:
        prediction=model.mix(experts);mixed-=math.log2((prediction if y else (1<<31)-prediction)/(1<<31))
        for i,r in enumerate((p,q)):losses[i]-=math.log2((r if y else (1<<31)-r)/(1<<31))
        model.observe(experts,y)
    assert mixed<=min(losses)+math.log2(5)+0.01


@pytest.fixture(scope='module')
def streams():
    if not codec.FORK.exists():pytest.skip('isolated native log-prior build required')
    data=memory_fixture();return data,{m:codec.encode(data,m,'-4') for m in (4,0,1,2,3)}


@pytest.mark.parametrize('mode',(4,0,1,2,3))
def test_native_modes_restore(streams,mode):
    data,frames=streams;assert codec.decode(frames[mode][0])==data


def test_disabled_and_fixed_controls_match_prior_codecs(streams):
    data,frames=streams;assert frames[0][1]['paq_sha256']==frames[4][1]['paq_sha256']
    _,control=old.encode(data,1,'-4');assert frames[3][1]['paq_sha256']==control['paq_sha256']
