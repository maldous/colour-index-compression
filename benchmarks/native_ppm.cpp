// Exact experimental accelerator for cix.ppm; no model-policy changes.
#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <stdexcept>
#include <unordered_map>
#include <utility>
#include <vector>

namespace {
using Byte = unsigned char;
struct Arithmetic {
    uint64_t low=0, high=0xffffffffULL, pending=0, bits=0;
    std::vector<Byte> payload;
    Byte current=0;
    unsigned used=0;
    void bit(unsigned b) {
        current=Byte((current<<1)|b); ++bits;
        if (++used==8) { payload.push_back(current); current=0; used=0; }
    }
    void emit(unsigned b) { bit(b); while(pending) { bit(b^1); --pending; } }
    void encode(unsigned a,unsigned b,unsigned total) {
        if (!(a<b && b<=total)) throw std::runtime_error("bad interval");
        uint64_t interval=high-low+1;
        high=low+interval*b/total-1; low+=interval*a/total;
        for (;;) {
            if(high<0x80000000ULL) emit(0);
            else if(low>=0x80000000ULL) { emit(1); low-=0x80000000ULL; high-=0x80000000ULL; }
            else if(low>=0x40000000ULL && high<0xc0000000ULL) {
                ++pending; low-=0x40000000ULL; high-=0x40000000ULL;
            } else break;
            low<<=1; high=(high<<1)+1;
        }
    }
    void finish() { ++pending; emit(low<0x40000000ULL?0:1); if(used) payload.push_back(Byte(current<<(8-used))); }
};
struct Node {
    std::vector<std::pair<unsigned,unsigned>> counts;
    unsigned total=0;
    void observe(unsigned s) {
        auto it=std::lower_bound(counts.begin(),counts.end(),s,
            [](const auto& p,unsigned v){return p.first<v;});
        if(it==counts.end() || it->first!=s) counts.insert(it,{s,1}); else ++it->second;
        if(++total>16384) {
            total=0; for(auto& p:counts) { p.second=(p.second+1)/2; total+=p.second; }
        }
    }
    bool contains(unsigned s) const {
        auto it=std::lower_bound(counts.begin(),counts.end(),s,
            [](const auto& p,unsigned v){return p.first<v;});
        return it!=counts.end() && it->first==s;
    }
};
struct State { unsigned escapes=1,hits=2; };
struct Model {
    std::array<std::unordered_map<uint64_t,Node>,9> tables;
    std::array<State,9*8*16> see;
    uint64_t history=0;
    unsigned length=0, max_order;
    explicit Model(unsigned order):max_order(order) {}
    uint64_t key(unsigned order) const {
        if(order==8) return history;
        return history & ((uint64_t(1)<<(8*order))-1);
    }
    Node* node(unsigned order) {
        auto& t=tables[order]; auto it=t.find(key(order));
        return it==t.end()?nullptr:&it->second;
    }
    void seed(unsigned s) { history=(history<<8)|s; length=std::min(length+1,max_order); }
    void observe(unsigned s,unsigned floor) {
        floor=std::min(floor,length);
        for(int order=int(length);order>=int(floor);--order) tables[order][key(order)].observe(s);
        seed(s);
    }
    unsigned floor(unsigned s) {
        for(int order=int(length);order>=0;--order) { auto n=node(order); if(n && n->contains(s)) return order; }
        return 0;
    }
};
unsigned bucket(unsigned x,unsigned cap) {
    unsigned b=0; while(x>1) { x>>=1; ++b; } return std::min(b,cap);
}
void update(State& s,bool escaped) {
    if(escaped) ++s.escapes; else ++s.hits;
    if(s.escapes+s.hits>256) { s.escapes=(s.escapes+1)/2; s.hits=(s.hits+1)/2; }
}
// With a null coder this follows the identical SEE history-training path.
unsigned process(Model& m,unsigned symbol,int method,bool secondary,Arithmetic* coder) {
    std::array<bool,256> excluded{};
    for(int order=int(m.length);order>=0;--order) {
        Node* node=m.node(order); if(!node) continue;
        unsigned mass=0,distinct=0,singletons=0,lo=0,count=0;
        for(const auto& p:node->counts) if(!excluded[p.first]) {
            mass+=p.second; ++distinct; if(p.second==1) ++singletons;
            if(p.first<symbol) lo+=p.second;
            if(p.first==symbol) count=p.second;
        }
        if(!distinct) continue;
        if(secondary) {
            State& state=m.see[(order*8+bucket(distinct,7))*16+bucket(mass,15)];
            unsigned total=state.escapes+state.hits;
            if(coder) {
                if(count) { coder->encode(0,state.hits,total); coder->encode(lo,lo+count,mass); }
                else coder->encode(state.hits,total,total);
            }
            update(state,!count);
        } else if(coder) {
            unsigned escape=method==0?1:method==1?distinct:method==2?(distinct+1)/2:std::max(1u,singletons);
            if(count) coder->encode(lo,lo+count,mass+escape);
            else coder->encode(mass,mass+escape,mass+escape);
        }
        if(count) return order;
        for(const auto& p:node->counts) excluded[p.first]=true;
    }
    if(coder) {
        unsigned rank=0,total=0;
        for(unsigned s=0;s<256;++s) if(!excluded[s]) { ++total; if(s<symbol) ++rank; }
        coder->encode(rank,rank+1,total);
    }
    return 0;
}
void varint(std::vector<Byte>& out,uint64_t value) {
    while(value>=128) { out.push_back(Byte(value)|128); value>>=7; }
    out.push_back(Byte(value));
}
}

// Returns 0 on success, 1 on exact lower-bound pruning, -1 on invalid input/error.
extern "C" int cix_ppm_encode(const Byte* data,size_t size,const Byte* prefix,size_t prefix_size,
                             unsigned order,unsigned method,unsigned exclusion,unsigned secondary,
                             size_t max_bytes,void** result,size_t* result_size) {
    if(!result || !result_size || order>8 || method>3 || exclusion>1 || secondary>1) return -1;
    *result=nullptr; *result_size=0;
    try {
        Model model(order);
        size_t training=std::min(prefix_size,std::min(size_t(65536),std::max(size_t(4096),size>32768?size_t(65536):size*2)));
        size_t start=prefix_size-training;
        if(order && start) for(size_t i=start>order?start-order:0;i<start;++i) model.seed(prefix[i]);
        for(size_t i=start;i<prefix_size;++i) {
            unsigned floor=secondary?process(model,prefix[i],method,true,nullptr):exclusion?model.floor(prefix[i]):0;
            model.observe(prefix[i],exclusion?floor:0);
        }
        Arithmetic coder;
        for(size_t i=0;i<size;++i) {
            if(max_bytes && i%256==0) {
                unsigned n=1; for(uint64_t b=coder.bits;b>=128;b>>=7) ++n;
                if(3+n+(coder.bits+7)/8>=max_bytes) return 1;
            }
            unsigned floor=process(model,data[i],method,secondary,&coder);
            model.observe(data[i],exclusion?floor:0);
        }
        coder.finish();
        std::vector<Byte> out{Byte(secondary?5:exclusion?4:3),Byte(order),Byte(secondary?exclusion:method)};
        varint(out,coder.bits); out.insert(out.end(),coder.payload.begin(),coder.payload.end());
        void* memory=std::malloc(out.size()); if(!memory) return -1;
        std::memcpy(memory,out.data(),out.size()); *result=memory; *result_size=out.size(); return 0;
    } catch(...) { return -1; }
}
extern "C" void cix_ppm_free(void* result) { std::free(result); }
