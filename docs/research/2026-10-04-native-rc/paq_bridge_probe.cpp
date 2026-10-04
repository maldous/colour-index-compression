// Research-only C ABI client. Not a shipping CIX executable or runtime fallback.
#include "paq_v215_bridge.h"
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

int main(int argc, char **argv) {
    if (argc < 4) return 90;
    const bool twice = std::strcmp(argv[1], "twice") == 0;
    std::vector<const char *> args;
    args.push_back("paq-v215-probe");
    for (int i = 3; i < argc; ++i) args.push_back(argv[i]);
    char error[512] = {};
    const int status = cix_paq_v215_process(static_cast<int>(args.size()), args.data(), argv[2], error, sizeof(error));
    if (status != CIX_PAQ_V215_OK) {
        std::fprintf(stderr, "CIX_BRIDGE_STATUS=%d %s\n", status, error);
        return status;
    }
    if (twice) {
        const std::string fresh = std::string(argv[2]) + ".repeat";
        const int second = cix_paq_v215_process(static_cast<int>(args.size()), args.data(), fresh.c_str(), error, sizeof(error));
        if (second != CIX_PAQ_V215_ALREADY_USED) return 91;
    }
    std::fprintf(stderr, "CIX_BRIDGE_OK %s\n", cix_paq_v215_bridge_version());
    return 0;
}
