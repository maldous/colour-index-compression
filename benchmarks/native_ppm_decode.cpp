// Exact decoder for existing PPM v3/v4/v5. Includes the unchanged model code.
#include "native_ppm.cpp"

namespace {
struct Reader {
    uint64_t low=0, high=0xffffffffULL, code=0, pos=0, bits;
    const Byte* payload;
    Reader(const Byte* data, uint64_t length):bits(length),payload(data) {
        for(unsigned i=0;i<32;++i) code=(code<<1)|bit();
    }
    unsigned bit() {
        const uint64_t at=pos++;
        return at<bits ? (payload[at>>3]>>(7-(at&7)))&1 : 0;
    }
    unsigned target(unsigned total) const {
        if(!total || code<low || code>high) throw std::runtime_error("invalid arithmetic state");
        return ((code-low+1)*total-1)/(high-low+1);
    }
    void update(unsigned a,unsigned b,unsigned total) {
        if(!(a<b && b<=total)) throw std::runtime_error("invalid interval");
        uint64_t span=high-low+1;
        high=low+span*b/total-1;low+=span*a/total;
        for(;;) {
            if(high<0x80000000ULL) {}
            else if(low>=0x80000000ULL) {low-=0x80000000ULL;high-=0x80000000ULL;code-=0x80000000ULL;}
            else if(low>=0x40000000ULL && high<0xc0000000ULL) {low-=0x40000000ULL;high-=0x40000000ULL;code-=0x40000000ULL;}
            else break;
            low<<=1;high=(high<<1)+1;code=(code<<1)|bit();
        }
    }
};

unsigned decode_symbol(Model& m, Reader& coder, unsigned method, bool secondary, unsigned& floor) {
    std::array<bool,256> excluded{};
    for(int order=int(m.length);order>=0;--order) {
        Node* node=m.node(order);if(!node)continue;
        unsigned mass=0,distinct=0,singletons=0;
        for(const auto& p:node->counts) if(!excluded[p.first]) {mass+=p.second;++distinct;singletons+=p.second==1;}
        if(!distinct)continue;
        unsigned total,target;
        if(secondary) {
            State& state=m.see[(order*8+bucket(distinct,7))*16+bucket(mass,15)];
            total=state.hits+state.escapes;target=coder.target(total);
            bool escaped=target>=state.hits;
            if(escaped) coder.update(state.hits,total,total);
            else coder.update(0,state.hits,total);
            update(state,escaped);
            if(escaped) {for(const auto& p:node->counts)excluded[p.first]=true;continue;}
            total=mass;target=coder.target(total);
        } else {
            unsigned escape=method==0?1:method==1?distinct:method==2?(distinct+1)/2:std::max(1u,singletons);
            total=mass+escape;target=coder.target(total);
            if(target>=mass) {coder.update(mass,total,total);for(const auto& p:node->counts)excluded[p.first]=true;continue;}
        }
        unsigned lo=0;
        for(const auto& p:node->counts) if(!excluded[p.first]) {
            if(target<lo+p.second) {coder.update(lo,lo+p.second,total);floor=order;return p.first;}
            lo+=p.second;
        }
        throw std::runtime_error("missing symbol interval");
    }
    unsigned total=0;for(unsigned s=0;s<256;++s)total+=!excluded[s];
    unsigned target=coder.target(total),rank=0;
    for(unsigned s=0;s<256;++s) if(!excluded[s]) {
        if(rank==target) {coder.update(rank,rank+1,total);floor=0;return s;}
        ++rank;
    }
    throw std::runtime_error("invalid fallback");
}
}

extern "C" int cix_ppm_decode(const Byte* payload,size_t payload_size,uint64_t bits,
    const Byte* prefix,size_t prefix_size,size_t output_size,unsigned order,unsigned method,
    unsigned exclusion,unsigned secondary,void** result,size_t* result_size) {
    if(!result || !result_size || order>8 || method>3 || exclusion>1 || secondary>1 ||
       bits>uint64_t(payload_size)*8 || (bits+7)/8!=payload_size || output_size>(1u<<26))return -1;
    *result=nullptr;*result_size=0;
    try {
        Model model(order);
        size_t training=std::min(prefix_size,std::min(size_t(65536),std::max(size_t(4096),output_size*2)));
        size_t start=prefix_size-training;
        if(order && start)for(size_t i=start>order?start-order:0;i<start;++i)model.seed(prefix[i]);
        for(size_t i=start;i<prefix_size;++i) {
            unsigned floor=secondary?process(model,prefix[i],method,true,nullptr):exclusion?model.floor(prefix[i]):0;
            model.observe(prefix[i],exclusion?floor:0);
        }
        Reader coder(payload,bits);std::vector<Byte> out(output_size);
        for(size_t i=0;i<output_size;++i) {
            unsigned floor=0,s=decode_symbol(model,coder,method,secondary,floor);
            out[i]=s;model.observe(s,exclusion?floor:0);
        }
        void* memory=std::malloc(std::max(size_t(1),out.size()));if(!memory)return -1;
        if(!out.empty())std::memcpy(memory,out.data(),out.size());
        *result=memory;*result_size=out.size();return 0;
    }catch(...){return -1;}
}
