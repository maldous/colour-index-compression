// Exact four-byte-key hash-chain parser; no source-format knowledge.
#include <algorithm>
#include <cstdint>
#include <vector>
#include <unordered_map>
#include <utility>
static unsigned bits(uint32_t x) { return x ? 32U-__builtin_clz(x) : 0; }
extern "C" int cix_lz_parse(const uint8_t* b, uint32_t end, uint32_t history,
 uint32_t window, uint32_t chain, uint32_t minimum, uint32_t maximum,
 int lazy, uint32_t* output, uint32_t* count) {
 try {
  if (!chain || minimum<4 || maximum<4 || history>end) return 1;
  std::unordered_map<uint32_t,std::vector<uint32_t>> table;
  auto key=[&](uint32_t p) { return uint32_t(b[p]) | uint32_t(b[p+1])<<8 |
    uint32_t(b[p+2])<<16 | uint32_t(b[p+3])<<24; };
  auto add=[&](uint32_t p) { auto &v=table[key(p)];v.push_back(p);if(v.size()>chain)v.erase(v.begin()); };
  if(history>=4) for(uint32_t p=0;p<history-3;++p) add(p);
  auto match=[&](uint32_t at) {
   uint32_t best=0,dist=0;int64_t score=-1;
   if(uint64_t(at)+4>end) return std::make_pair(best,dist);
   auto it=table.find(key(at));if(it==table.end()) return std::make_pair(best,dist);
   for(auto pos=it->second.rbegin();pos!=it->second.rend();++pos) {
    uint32_t d=at-*pos;if(!d || d>window || *pos>=at)continue;
    uint32_t n=4,limit=std::min(maximum,end-at);
    while(n<limit && b[at-d+n]==b[at+n])++n;
    if(n<minimum)continue;
    int64_t s=int64_t(n)*8-bits(d)-bits(n)-3;
    if(s>score || (s==score && n>best)) {score=s;best=n;dist=d;}
   }
   return std::make_pair(best,dist);
  };
  uint32_t p=history,t=0;
  while(p<end) {
   auto m=match(p);
   if(m.first>=minimum && lazy && p+1<end) {
    if(uint64_t(p)+4<=end)add(p);
    if(match(p+1).first>m.first+1) {
     output[t++]=0;output[t++]=b[p];output[t++]=0;++p;continue;
    }
   }
   if(m.first>=minimum) {
    output[t++]=1;output[t++]=m.second;output[t++]=m.first;
    uint32_t stop=std::min(end,p+m.first);
    for(uint32_t q=p;q<stop;++q)if(uint64_t(q)+4<=end)add(q);
    p+=m.first;
   } else {
    output[t++]=0;output[t++]=b[p];output[t++]=0;
    if(uint64_t(p)+4<=end)add(p);
    ++p;
   }
  }
  *count=t/3;return 0;
 } catch(...) {return 2;}
}
