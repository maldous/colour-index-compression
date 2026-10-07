// Experimental symmetric-rounded eta=6 learning; separate CIXQ3 representation.
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
    int weights[8][22];int bias[8]{};
    MixerBank(){for(auto& row:weights)for(int& w:row)w=46;}
};
struct FixedModel {
    std::unordered_map<uint64_t,Counts> tables[15];
    std::unordered_map<uint32_t,uint8_t> matches;
    MixerBank banks[16];
    Counts lag[6][8],match[8];
    FixedModel(){for(auto& r:lag)for(auto& c:r)c={1,1};for(auto& c:match)c={1,1};}
};
int reliability(int predicted,const Counts& c,int bitpos) {
    if(predicted<0)return 2048;
    int confidence=clip((int64_t(2*c.zero+1)*4096)/(2*(c.zero+c.one+1)),2048,4095);
    return ((predicted>>(7-bitpos))&1)?confidence:4096-confidence;
}
}
extern "C" int cix_fixed_encode(const uint8_t* data,size_t size,unsigned context_bits,
 const int32_t* stretch,void** result,size_t* result_size) {
 if(!result || !result_size || !stretch || (context_bits!=0 && context_bits!=2 && context_bits!=4))return -1;
 *result=nullptr;*result_size=0;
 try {
    FixedModel model;Arithmetic coder;
    static const int patterns[15][6]={{0,0,0,0},{1,0,0,0},{1,2,0,0},{1,2,3,0},{1,2,3,4},{1,3,0,0},{1,4,0,0},{1,5,0,0},{2,3,0,0},{2,4,0,0},{3,6,0,0},{4,8,0,0},{1,4,8,0},{1,2,3,4,5,0},{1,2,3,4,5,6}};
    static const int lags[6]={1,2,4,8,16,32};
    for(size_t pos=0;pos<size;++pos) {
        uint64_t contexts[15]{};bool valid[15]{};
        for(int i=0;i<15;++i) {
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
        for(int bitpos=0;bitpos<8;++bitpos) {
            uint64_t keys[15]{};int values[22]{};
            for(int i=0;i<15;++i) {
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
            for(int i=0;i<6;++i)values[15+i]=stretch[reliability(pos>=size_t(lags[i])?data[pos-lags[i]]:-1,model.lag[i][bitpos],bitpos)];
            values[21]=stretch[reliability(match_byte,model.match[bitpos],bitpos)];
            int64_t sum=0;for(int i=0;i<22;++i)sum+=int64_t(bank.weights[bitpos][i])*values[i];
            int probability=squash_fixed(bank.bias[bitpos]+int(floor_div(sum,1024)),stretch);
            int bit=(data[pos]>>(7-bitpos))&1,zero=4096-probability;
            if(bit)coder.encode(zero,4096,4096);else coder.encode(0,zero,4096);
            int error=bit?4096-probability:-probability;
            bank.bias[bitpos]=clip(bank.bias[bitpos]+round_div(int64_t(error)*4096,4096*64),-49152,49152);
            for(int i=0;i<22;++i)bank.weights[bitpos][i]=clip(bank.weights[bitpos][i]+round_div(int64_t(error)*values[i]*1024,int64_t(4096)*4096*64),-4096,4096);
            for(int i=0;i<15;++i)if(valid[i])observe_count(model.tables[i][keys[i]],bit);
            for(int i=0;i<6;++i)if(pos>=size_t(lags[i]))observe_count(model.lag[i][bitpos],((data[pos-lags[i]]>>(7-bitpos))&1)!=bit);
            if(match_byte>=0)observe_count(model.match[bitpos],((match_byte>>(7-bitpos))&1)!=bit);
            prefix=(prefix<<1)|bit;
        }
        if(pos>=4)model.matches[match_key]=data[pos];
    }
    coder.finish();std::vector<Byte> out{1,1};varint(out,coder.bits);
    out.insert(out.end(),coder.payload.begin(),coder.payload.end());
    void* memory=std::malloc(out.size());if(!memory)return -1;
    std::memcpy(memory,out.data(),out.size());*result=memory;*result_size=out.size();return 0;
 }catch(...){return -1;}
}
