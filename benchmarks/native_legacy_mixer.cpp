// Independent native decoder/encoder qualification for legacy Q2/Q3/Q5.
// Internal modes 16=Q2, 17=Q3. No changes to legacy sources or representations.
// Mode zero preserves Q5 payloads exactly; standalone source for live-run isolation.
#include "native_ppm.cpp"
namespace {
struct Counts { int zero=0,one=0; };
int64_t floor_div(int64_t n,int64_t d) { return n>=0?n/d:-((-n+d-1)/d); }
int64_t round_div(int64_t n,int64_t d) { return n>=0?(n+d/2)/d:-((-n+d/2)/d); }
int clip(int64_t v,int lo,int hi) { return int(std::max(int64_t(lo),std::min(int64_t(hi),v))); }
void observe_count(Counts& c,int bit) {
    if(bit)++c.one;else ++c.zero;
    if(c.zero+c.one>2048) {c.zero=(c.zero+1)/2;c.one=(c.one+1)/2;}
}
int squash_fixed(int value,const int32_t* stretch) {
    if(value<=stretch[1])return 1;
    if(value>=stretch[4095])return 4095;
    int i=int(std::lower_bound(stretch+1,stretch+4096,value)-stretch);
    return std::abs(stretch[i]-value)<std::abs(stretch[i-1]-value)?i:i-1;
}
struct MixerBank {
    int weights[8][26];int bias[8]{};
    MixerBank(){for(auto& row:weights)for(int& w:row)w=44;}
};
struct FixedModel {
    std::unordered_map<uint64_t,Counts> tables[15];
    std::unordered_map<uint32_t,uint8_t> matches;
    MixerBank banks[16];
    Model byte_model{6};
    Counts lag[6][8],match[8];
    uint16_t successors[256]{};
    std::unordered_map<uint64_t,Counts> relations[2];
    Model delta_model{1};
    FixedModel(){for(auto& r:lag)for(auto& c:r)c={1,1};for(auto& c:match)c={1,1};}
};
int reliability(int predicted,const Counts& c,int bitpos) {
    if(predicted<0)return 2048;
    int confidence=clip((int64_t(2*c.zero+1)*4096)/(2*(c.zero+c.one+1)),2048,4095);
    return ((predicted>>(7-bitpos))&1)?confidence:4096-confidence;
}
}
namespace {
// Independently implemented arithmetic reader; qualified against Python streams.
struct BitDecoder {
    const Byte* bytes;size_t count=0,index=0;uint64_t bit_count=0;
    uint64_t low=0,high=0xffffffffULL,value=0;
    BitDecoder(const Byte* p,size_t n,bool enabled):bytes(p) {
        if(!enabled)return;
        if(n<3 || p[0]!=1 || p[1]!=1)throw std::runtime_error("bad payload");
        size_t at=2;unsigned shift=0;
        for(;;){if(at>=n || shift>=64)throw std::runtime_error("bad length");unsigned b=p[at++];bit_count|=uint64_t(b&127)<<shift;if(!(b&128))break;shift+=7;}
        if(bit_count>uint64_t(n-at)*8 || (bit_count+7)/8!=n-at)throw std::runtime_error("payload length");
        bytes=p+at;count=n-at;
        if(bit_count%8 && count && (bytes[count-1]&((1u<<(8-bit_count%8))-1)))throw std::runtime_error("padding");
        for(int i=0;i<32;++i)value=(value<<1)|read();
    }
    unsigned read(){unsigned result=index<bit_count?((bytes[index/8]>>(7-index%8))&1):0;++index;return result;}
    unsigned next(unsigned zero) {
        uint64_t interval=high-low+1;
        uint64_t scaled=((value-low+1)*4096-1)/interval;
        unsigned bit=scaled>=zero;
        unsigned a=bit?zero:0,b=bit?4096:zero;
        high=low+interval*b/4096-1;low+=interval*a/4096;
        for(;;) {
            if(high<0x80000000ULL){}
            else if(low>=0x80000000ULL){low-=0x80000000ULL;high-=0x80000000ULL;value-=0x80000000ULL;}
            else if(low>=0x40000000ULL && high<0xc0000000ULL){low-=0x40000000ULL;high-=0x40000000ULL;value-=0x40000000ULL;}
            else break;
            low<<=1;high=(high<<1)+1;value=(value<<1)|read();
        }
        return bit;
    }
};
}
template<bool Decoding>
int process_relational(const uint8_t* input,size_t input_size,size_t size,unsigned context_bits,unsigned mode,
 const int32_t* stretch,void** result,size_t* result_size) {
 const bool byte_expert=mode<16;
 const int pattern_count=mode==16?13:15;
 if(mode>=16 && mode<=17)mode=0;
 if(!result || !result_size || !stretch || (context_bits!=0 && context_bits!=2 && context_bits!=4) || mode>3)return -1;
 *result=nullptr;*result_size=0;
 try {
    FixedModel model;Arithmetic coder;
    std::vector<Byte> restored(Decoding?size:0);
    const Byte* data=Decoding?restored.data():input;
    BitDecoder decoder(input,input_size,Decoding);
    const int experts=pattern_count+7+(byte_expert?1:0)+((mode&1)?2:0)+((mode&2)?1:0);
    if(mode || !byte_expert)for(auto& bank:model.banks)for(auto& row:bank.weights)for(int& w:row)w=1024/experts;
    static const int patterns[15][6]={{0,0,0,0},{1,0,0,0},{1,2,0,0},{1,2,3,0},{1,2,3,4},{1,3,0,0},{1,4,0,0},{1,5,0,0},{2,3,0,0},{2,4,0,0},{3,6,0,0},{4,8,0,0},{1,4,8,0},{1,2,3,4,5,0},{1,2,3,4,5,6}};
    static const int lags[6]={1,2,4,8,16,32};
    for(size_t pos=0;pos<size;++pos) {
        uint64_t contexts[15]{};bool valid[15]{};
        for(int i=0;i<pattern_count;++i) {
            valid[i]=true;
            for(int lag:patterns[i])if(lag) {
                if(pos<size_t(lag)){valid[i]=false;break;}
                contexts[i]=(contexts[i]<<8)|data[pos-lag];
            }
        }
        uint32_t match_key=0;int match_byte=-1;
        if(pos>=4) {
            for(size_t j=pos-4;j<pos;++j)match_key=(match_key<<8)|data[j];
            auto it=model.matches.find(match_key);if(it!=model.matches.end())match_byte=it->second;
        }
        unsigned context=pos?data[pos-1]&((1u<<context_bits)-1):0;
        auto& bank=model.banks[context];int prefix=0;
        uint64_t weights[256]{};bool excluded[256]{};uint64_t remaining=uint64_t(1)<<24;
        for(int order=byte_expert?int(model.byte_model.length):-1;order>=0;--order) {
            auto node=model.byte_model.node(order);if(!node)continue;
            unsigned mass=0,distinct=0;
            for(auto pair:node->counts)if(!excluded[pair.first]) {mass+=pair.second;++distinct;}
            if(!distinct)continue;
            for(auto pair:node->counts)if(!excluded[pair.first]) {
                weights[pair.first]+=remaining*pair.second/(mass+distinct);excluded[pair.first]=true;
            }
            remaining=remaining*distinct/(mass+distinct);
        }
        unsigned unseen=0;for(bool value:excluded)if(!value)++unseen;
        uint64_t cumulative[257]{};
        for(unsigned i=0;i<256;++i) {
            if(!excluded[i] && unseen)weights[i]+=remaining/unseen;
            cumulative[i+1]=cumulative[i]+weights[i]+1;
        }

        uint64_t delta_cumulative[257]{};
        if(mode&2) {
            uint64_t dw[256]{};bool dx[256]{};uint64_t rem=uint64_t(1)<<24;
            for(int order=int(model.delta_model.length);order>=0;--order) {
                auto node=model.delta_model.node(order);if(!node)continue;
                unsigned mass=0,distinct=0;
                for(auto pair:node->counts)if(!dx[pair.first]){mass+=pair.second;++distinct;}
                if(!distinct)continue;
                for(auto pair:node->counts)if(!dx[pair.first]){dw[pair.first]+=rem*pair.second/(mass+distinct);dx[pair.first]=true;}
                rem=rem*distinct/(mass+distinct);
            }
            unsigned unseen=0;for(bool v:dx)if(!v)++unseen;
            for(unsigned d=0;d<256;++d)if(!dx[d] && unseen)dw[d]+=rem/unseen;
            for(unsigned b=0;b<256;++b)delta_cumulative[b+1]=delta_cumulative[b]+dw[(b-(pos?data[pos-1]:0))&255]+1;
        }
        unsigned prev=pos?data[pos-1]:0;
        uint64_t relation_contexts[2]={model.successors[prev], (uint64_t(prev)<<16)|model.successors[prev]};
        for(int bitpos=0;bitpos<8;++bitpos) {
            uint64_t keys[15]{},relation_keys[2]{};int values[26]{};
            for(int i=0;i<pattern_count;++i) {
                int probability=2048;
                if(valid[i]) {
                    keys[i]=(contexts[i]<<8)|uint64_t((1<<bitpos)+prefix);
                    auto it=model.tables[i].find(keys[i]);
                    if(it!=model.tables[i].end()) {
                        auto c=it->second;
                        probability=clip(int64_t(2*c.one+1)*4096/(2*(c.zero+c.one+1)),1,4095);
                    }
                }
                values[i]=stretch[probability];
            }
            for(int i=0;i<6;++i)values[pattern_count+i]=stretch[reliability(pos>=size_t(lags[i])?data[pos-lags[i]]:-1,model.lag[i][bitpos],bitpos)];
            values[pattern_count+6]=stretch[reliability(match_byte,model.match[bitpos],bitpos)];
            unsigned lo=unsigned(prefix)<<(8-bitpos),hi=lo+(1u<<(8-bitpos)),mid=(lo+hi)/2;
            int byte_probability=clip(4096*(cumulative[hi]-cumulative[mid])/(cumulative[hi]-cumulative[lo]),1,4095);
            if(byte_expert)values[pattern_count+7]=stretch[byte_probability];
            int count=pattern_count+7+(byte_expert?1:0);
            if(mode&1)for(int r=0;r<2;++r) {
                int p=2048;
                relation_keys[r]=(relation_contexts[r]<<8)|uint64_t((1<<bitpos)+prefix);
                if(pos){auto it=model.relations[r].find(relation_keys[r]);if(it!=model.relations[r].end()){
                    auto c=it->second;p=clip(int64_t(2*c.one+1)*4096/(2*(c.zero+c.one+1)),1,4095);}}
                values[count++]=stretch[p];
            }
            if(mode&2)values[count++]=stretch[clip(4096*(delta_cumulative[hi]-delta_cumulative[mid])/(delta_cumulative[hi]-delta_cumulative[lo]),1,4095)];
            int64_t sum=0;for(int i=0;i<experts;++i)sum+=int64_t(bank.weights[bitpos][i])*values[i];
            int probability=squash_fixed(bank.bias[bitpos]+int(floor_div(sum,1024)),stretch);
            int zero=4096-probability;
            int bit;
            if constexpr(Decoding) {
                bit=decoder.next(unsigned(zero));
                restored[pos]=Byte((restored[pos]<<1)|bit);
            } else {
                bit=(data[pos]>>(7-bitpos))&1;
                if(bit)coder.encode(zero,4096,4096);else coder.encode(0,zero,4096);
            }
            int error=bit?4096-probability:-probability;
            bank.bias[bitpos]=clip(bank.bias[bitpos]+round_div(int64_t(error)*4096,4096*64),-49152,49152);
            for(int i=0;i<experts;++i)bank.weights[bitpos][i]=clip(bank.weights[bitpos][i]+round_div(int64_t(error)*values[i]*1024,int64_t(4096)*4096*64),-4096,4096);
            for(int i=0;i<pattern_count;++i)if(valid[i])observe_count(model.tables[i][keys[i]],bit);
            for(int i=0;i<6;++i)if(pos>=size_t(lags[i]))observe_count(model.lag[i][bitpos],((data[pos-lags[i]]>>(7-bitpos))&1)!=bit);
            if(match_byte>=0)observe_count(model.match[bitpos],((match_byte>>(7-bitpos))&1)!=bit);
            if((mode&1) && pos)for(int r=0;r<2;++r)observe_count(model.relations[r][relation_keys[r]],bit);
            prefix=(prefix<<1)|bit;
        }
        if(pos>=4)model.matches[match_key]=data[pos];
        if(byte_expert)model.byte_model.observe(data[pos],0);
        if(mode&2)model.delta_model.observe((unsigned(data[pos])-(pos?data[pos-1]:0))&255,0);
        if((mode&1) && pos)model.successors[prev]=uint16_t((model.successors[prev]<<8)|data[pos]);
    }
    std::vector<Byte> out;
    if constexpr(Decoding)out=std::move(restored);
    else {coder.finish();out={1,1};varint(out,coder.bits);out.insert(out.end(),coder.payload.begin(),coder.payload.end());}
    void* memory=std::malloc(std::max(size_t(1),out.size()));if(!memory)return -1;
    std::memcpy(memory,out.data(),out.size());*result=memory;*result_size=out.size();return 0;
 }catch(...){return -1;}
}

extern "C" int cix_relation_encode(const Byte* data,size_t size,unsigned bits,unsigned mode,const int32_t* table,void** out,size_t* n) {
    return process_relational<false>(data,size,size,bits,mode,table,out,n);
}
extern "C" int cix_relation_decode(const Byte* data,size_t size,size_t original,unsigned bits,unsigned mode,const int32_t* table,void** out,size_t* n) {
    return process_relational<true>(data,size,original,bits,mode,table,out,n);
}
