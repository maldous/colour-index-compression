// Experimental bridge around unchanged PAQ v215 predictions and model updates.
// No upstream probability, transform, context or update is changed.
#pragma once
#include <cstdio>
#include <cstdlib>
#include <cstdint>
#include <vector>
#include <stdexcept>

inline bool cix_bridge_enabled() { return std::getenv("CIX_RESIDUAL_IN")!=nullptr; }

struct CixPredictionBridge {
    FILE* trace=nullptr;
    unsigned subbits=0;
    std::vector<std::vector<uint8_t>> errors;
    std::vector<size_t> positions;
    CixPredictionBridge() {
        const char* path=std::getenv("CIX_TRACE_OUT");
        if(path) {trace=std::fopen(path,"wb");if(!trace)throw std::runtime_error("cannot open CIX trace");}
        path=std::getenv("CIX_RESIDUAL_IN");
        if(!path)return;
        FILE* f=std::fopen(path,"rb");if(!f)throw std::runtime_error("cannot open CIX residual");
        const char magic[]="CIXE1";
        for(unsigned i=0;i<5;++i)if(std::fgetc(f)!=magic[i])throw std::runtime_error("bad residual magic");
        int b=std::fgetc(f);if(b<0 || b>3)throw std::runtime_error("bad residual precision");subbits=b;
        errors.resize(31u<<subbits);positions.resize(errors.size());
        for(auto& stream:errors) {
            uint64_t n=0;
            for(unsigned j=0;j<8;++j) {int x=std::fgetc(f);if(x<0)throw std::runtime_error("truncated residual");n|=uint64_t(x)<<(8*j);}
            if(n>1u<<28)throw std::runtime_error("oversized diagnostic residual");
            stream.resize(size_t(n));
            if(n && std::fread(stream.data(),1,size_t(n),f)!=n)throw std::runtime_error("truncated residual data");
        }
        if(std::fgetc(f)!=EOF)throw std::runtime_error("trailing residual bytes");std::fclose(f);
    }
    ~CixPredictionBridge(){if(trace)std::fclose(trace);}
    void record(uint32_t p,int y) {
        if(!trace)return;
        uint32_t value=p|(uint32_t(y)<<31);
        uint8_t bytes[4]={uint8_t(value),uint8_t(value>>8),uint8_t(value>>16),uint8_t(value>>24)};
        if(std::fwrite(bytes,1,4,trace)!=4)throw std::runtime_error("CIX trace write failed");
    }
    int decode(uint32_t p) {
        uint32_t q=p<(1u<<30)?p:(1u<<31)-p;
        if(!q)throw std::runtime_error("invalid PAQ probability");
        unsigned exponent=0;for(uint32_t v=q;v>1;v>>=1)++exponent;
        uint32_t base=1u<<exponent;
        unsigned bucket=(exponent<<subbits)+unsigned((uint64_t(q-base)<<subbits)/base);
        if(bucket>=errors.size() || positions[bucket]>=errors[bucket].size())throw std::runtime_error("CIX residual exhausted");
        unsigned error=errors[bucket][positions[bucket]++];
        if(error>1)throw std::runtime_error("invalid CIX error symbol");
        return int(error^(p>>30));
    }
    void finish() {
        for(size_t i=0;i<errors.size();++i)if(positions[i]!=errors[i].size())throw std::runtime_error("unused CIX residual");
    }
};

inline CixPredictionBridge& cix_bridge(){static CixPredictionBridge bridge;return bridge;}
