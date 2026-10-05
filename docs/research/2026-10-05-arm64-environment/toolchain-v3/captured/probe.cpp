#include <iostream>
#include <vector>
#include <numeric>
int main(){std::vector<int> v{1,2,3,4};if(std::accumulate(v.begin(),v.end(),0)!=10)return 1;std::cout<<"CIX_ARM64_TOOLCHAIN_PASS\n";}
