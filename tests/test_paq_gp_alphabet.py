import subprocess
from benchmarks.build_paq_gp_alphabet import HEADER


def test_causal_alphabet_probability_and_rescaling(tmp_path):
    (tmp_path/'CixGpAlphabet.hpp').write_text(HEADER)
    (tmp_path/'test.cpp').write_text(r'''
#include "CixGpAlphabet.hpp"
#include <memory>
int main() {
  auto p=std::make_unique<CixGpAlphabet>();
  assert(p->probability(0,0,false)==2048);
  assert(p->probability(0,0,true)==2048);
  p->observe(0); p->observe(65535);
  for(int i=0;i<14;i++) p->observe(0);
  // frequency masses 15/1 plus uniform escape 8/8 -> 9/32
  assert(p->probability(0,0,false)==1152);
  assert(p->probability(0,0,true)==2048);
  // Empty prefix remains supported, at exactly 1/2.
  assert(p->probability(1,2,false)==2048);
  int occupied=p->probability(0,15,true);
  for(int i=0;i<(1<<20);i++) p->observe(0);
  assert(p->probability(0,15,true)==occupied);
  for(unsigned depth=0;depth<16;depth++) {
    for(unsigned prefix=0;prefix<(1u<<depth);prefix++) {
      int a=p->probability(prefix,depth,false), b=p->probability(prefix,depth,true);
      assert(a>=1 && a<=4095 && b>=1 && b<=4095);
    }
  }
  p->reset(); assert(p->probability(0,0,false)==2048);
  assert(p->probability(0,0,true)==2048);
}
''')
    subprocess.run(['g++','-std=c++17','-O2',str(tmp_path/'test.cpp'),'-o',str(tmp_path/'test')],check=True)
    subprocess.run([str(tmp_path/'test')],check=True)


import pytest
from benchmarks import paq_gp_alphabet_probe as codec
from tests.test_paq_gp_feedback import instruction_fixture


@pytest.mark.skipif(not codec.FORK.exists(),reason='isolated alphabet build required')
def test_native_control_and_every_feedback_mode_restore():
    data=instruction_fixture(); hashes={}
    for mode in (4,0,1,2,3):
        frame,stats=codec.encode(data,mode,'-4')
        assert codec.decode(frame)==data
        hashes[mode]=stats['paq_sha256']
    assert hashes[0]==hashes[4]
    assert all(hashes[m]!=hashes[0] for m in (1,2,3))
