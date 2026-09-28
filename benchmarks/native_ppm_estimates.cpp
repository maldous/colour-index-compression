// Experimental exact floating-point estimator acceleration. Compile without fast-math.
#include "native_ppm.cpp"
#include <cmath>

extern "C" int cix_ppm_estimate(const Byte* data,size_t size,const Byte* prefix,size_t prefix_size,
                               unsigned order,unsigned method,unsigned exclusion,unsigned portfolio,
                               size_t sample_size,const double* logs,double* result) {
    if(!result || !logs || order>8 || method>3 || exclusion>1 || portfolio>1 || sample_size>size) return -1;
    *result=0;
    if(!sample_size) return 0;
    try {
        Model model(order);
        size_t training=std::min(prefix_size,std::min(size_t(65536),std::max(size_t(4096),size>32768?size_t(65536):size*2)));
        size_t start=prefix_size-training;
        if(order && start) for(size_t i=start>order?start-order:0;i<start;++i) model.seed(prefix[i]);
        for(size_t i=start;i<prefix_size;++i) {
            unsigned floor=portfolio?process(model,prefix[i],method,true,nullptr):exclusion?model.floor(prefix[i]):0;
            model.observe(prefix[i],exclusion?floor:0);
        }
        std::array<double,4> fixed{};
        double see=0;
        for(size_t i=0;i<sample_size;++i) {
            unsigned symbol=data[i],matched=0;
            bool coded=false;
            std::array<bool,256> excluded{};
            for(int o=int(model.length);o>=0;--o) {
                Node* node=model.node(o); if(!node) continue;
                unsigned mass=0,distinct=0,singletons=0,count=0;
                for(const auto& p:node->counts) if(!excluded[p.first]) {
                    mass+=p.second; ++distinct; if(p.second==1) ++singletons;
                    if(p.first==symbol) count=p.second;
                }
                if(!distinct) continue;
                std::array<unsigned,4> escapes{1,distinct,(distinct+1)/2,std::max(1u,singletons)};
                for(unsigned m=portfolio?0:method;m<(portfolio?4:method+1);++m) {
                    fixed[m]+=logs[mass+escapes[m]]-logs[count?count:escapes[m]];
                }
                if(portfolio) {
                    State& state=model.see[(o*8+bucket(distinct,7))*16+bucket(mass,15)];
                    see+=logs[state.escapes+state.hits]-logs[count?state.hits:state.escapes];
                    if(count) see+=logs[mass]-logs[count];
                    update(state,!count);
                }
                if(count) { coded=true; matched=o; break; }
                for(const auto& p:node->counts) excluded[p.first]=true;
            }
            if(!coded) {
                unsigned remaining=0; for(bool e:excluded) if(!e) ++remaining;
                double fallback=logs[std::max(1u,remaining)];
                for(unsigned m=portfolio?0:method;m<(portfolio?4:method+1);++m) fixed[m]+=fallback;
                if(portfolio) see+=fallback;
            }
            model.observe(symbol,exclusion?matched:0);
        }
        double value=portfolio?std::min(*std::min_element(fixed.begin(),fixed.end()),see):fixed[method];
        *result=value*(double(size)/double(sample_size));
        return 0;
    } catch(...) { return -1; }
}
