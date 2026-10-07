// Research-only ABI client for the CIX-owned PAQ v215 bridge boundary.
#include "paq_v215_bridge.h"
#include <cstdio>
#include <vector>

int main(int argc, char **argv) {
    if (argc < 4) return 90;  // probe EXPECTED_OUTPUT PAQ_ARGUMENT...
    std::vector<const char *> args;
    args.push_back("paq-v215-arm64-probe");
    for (int index = 2; index < argc; ++index) args.push_back(argv[index]);
    char error[512] = {};
    const int status = cix_paq_v215_process(static_cast<int>(args.size()), args.data(),
                                             argv[1], error, sizeof(error));
    if (status != CIX_PAQ_V215_OK) {
        std::fprintf(stderr, "CIX_BRIDGE_STATUS=%d %s\n", status, error);
        return status;
    }
    std::fprintf(stderr, "CIX_BRIDGE_OK %s\n", cix_paq_v215_bridge_version());
    return 0;
}
