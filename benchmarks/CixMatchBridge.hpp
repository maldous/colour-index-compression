// CIX match elimination around the unchanged PAQ v215 model.
#pragma once
#include <cstdio>
#include <cstdlib>
#include <cstdint>
#include <vector>
#include <stdexcept>

struct CixMatchBridge {
    FILE* records=nullptr;
    FILE* trace=nullptr;
    bool reading=false,active=false;
    unsigned predicted=0,failure=0;
    uint64_t byteIndex=0;
    std::vector<uint8_t> tokens[4];
    size_t positions[4]={0,0,0,0};
    CixMatchBridge() {
        const char* path=std::getenv("CIX_TRACE_OUT");
        if(path) {trace=std::fopen(path,"wb");if(!trace)throw std::runtime_error("cannot open trace");}
        path=std::getenv("CIX_MATCH_ENCODE");
        if(path) {records=std::fopen(path,"wb");if(!records)throw std::runtime_error("cannot open match records");std::fwrite("CIXJ1",1,5,records);}
        path=std::getenv("CIX_MATCH_DECODE");
        if(!path)return;
        if(records)throw std::runtime_error("conflicting match bridge modes");
        reading=true;FILE* f=std::fopen(path,"rb");if(!f)throw std::runtime_error("cannot open match tokens");
        for(char c:std::vector<char>{'C','I','X','M','1'})if(std::fgetc(f)!=c)throw std::runtime_error("invalid match protocol");
        for(auto& stream:tokens) {
            uint64_t n=0;
            for(unsigned i=0;i<8;++i) {int b=std::fgetc(f);if(b<0)throw std::runtime_error("truncated match header");n|=uint64_t(b)<<(i*8);}
            if(n>1u<<27)throw std::runtime_error("oversized diagnostic match sequence");
            stream.resize(size_t(n));if(n && std::fread(stream.data(),1,n,f)!=n)throw std::runtime_error("truncated match tokens");
        }
        if(std::fgetc(f)!=EOF)throw std::runtime_error("unused match data");std::fclose(f);
    }
    ~CixMatchBridge(){if(records)std::fclose(records);if(trace)std::fclose(trace);}
    void start(unsigned candidate,unsigned mode,unsigned actual=0) {
        uint64_t at=byteIndex++;
        active=(records || reading) && candidate<256 && mode>=4 && mode<=7;
        if(!active)return;
        predicted=candidate;unsigned group=mode-4;
        if(records) {
            unsigned difference=actual^candidate;failure=0;
            while(failure<8 && !(difference&(128u>>failure)))++failure;
            if(at>UINT32_MAX)throw std::runtime_error("diagnostic match index overflow");
            for(unsigned i=0;i<4;++i)if(std::fputc(uint8_t(at>>(8*i)),records)==EOF)throw std::runtime_error("match index write failed");
            if(std::fputc(group,records)==EOF || std::fputc(failure,records)==EOF)throw std::runtime_error("match record write failed");
        } else {
            if(positions[group]>=tokens[group].size())throw std::runtime_error("match token sequence exhausted");
            failure=tokens[group][positions[group]++];if(failure>8)throw std::runtime_error("invalid first-failure rank");
        }
    }
    bool forced(unsigned bit)const{return active && bit<=failure;}
    int value(unsigned bit)const{return ((predicted>>(7-bit))&1)^int(bit==failure);}
    void record(uint32_t p,int y) {
        if(!trace)return;
        uint32_t v=p|(uint32_t(y)<<31);uint8_t b[4]={uint8_t(v),uint8_t(v>>8),uint8_t(v>>16),uint8_t(v>>24)};
        if(std::fwrite(b,1,4,trace)!=4)throw std::runtime_error("prediction trace write failed");
    }
    void finish() {
        if(reading)for(unsigned i=0;i<4;++i)if(positions[i]!=tokens[i].size())throw std::runtime_error("unused match tokens");
    }
};
inline CixMatchBridge& cix_match(){static CixMatchBridge bridge;return bridge;}
