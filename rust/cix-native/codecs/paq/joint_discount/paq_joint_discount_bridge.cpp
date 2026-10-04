#include "paq_joint_discount_bridge.h"

#include <atomic>
#include <cstdio>
#include <cstring>
#include <exception>
#include <sys/stat.h>
#include <vector>

/* Defined by unchanged upstream src/paq8px.cpp. */
int processCommandLine(int argc, char **argv);

namespace {
std::atomic_flag used = ATOMIC_FLAG_INIT;

void message(char *buffer, size_t size, const char *text) {
    if (buffer != nullptr && size != 0) {
        std::snprintf(buffer, size, "%s", text);
    }
}

bool regular_output_missing(const char *path) {
    struct stat state {};
    return stat(path, &state) != 0;
}

bool regular_output_present(const char *path) {
    struct stat state {};
    return stat(path, &state) == 0 && S_ISREG(state.st_mode);
}
}  // namespace

extern "C" int cix_paq_joint_discount_process(
    int argc,
    const char *const argv[],
    const char *expected_output,
    char *error_buffer,
    size_t error_buffer_size
) {
    message(error_buffer, error_buffer_size, "");
    if (argc < 2 || argv == nullptr || expected_output == nullptr || expected_output[0] == '\0') {
        message(error_buffer, error_buffer_size, "invalid PAQ joint_discount worker arguments");
        return CIX_PAQ_JOINT_DISCOUNT_INVALID_ARGUMENT;
    }
    for (int index = 0; index < argc; ++index) {
        if (argv[index] == nullptr) {
            message(error_buffer, error_buffer_size, "PAQ joint_discount argument vector contains null");
            return CIX_PAQ_JOINT_DISCOUNT_INVALID_ARGUMENT;
        }
    }
    if (!regular_output_missing(expected_output)) {
        message(error_buffer, error_buffer_size, "PAQ joint_discount output must not exist before invocation");
        return CIX_PAQ_JOINT_DISCOUNT_INVALID_ARGUMENT;
    }
    if (used.test_and_set(std::memory_order_acq_rel)) {
        message(error_buffer, error_buffer_size, "PAQ joint_discount bridge permits one invocation per worker process");
        return CIX_PAQ_JOINT_DISCOUNT_ALREADY_USED;
    }

    std::vector<char *> mutable_argv;
    mutable_argv.reserve(static_cast<size_t>(argc));
    for (int index = 0; index < argc; ++index) {
        mutable_argv.push_back(const_cast<char *>(argv[index]));
    }
    try {
        const int status = processCommandLine(argc, mutable_argv.data());
        if (status != 0) {
            message(error_buffer, error_buffer_size, "PAQ joint_discount returned a non-zero status");
            return CIX_PAQ_JOINT_DISCOUNT_UPSTREAM_FAILURE;
        }
    } catch (const std::exception &error) {
        message(error_buffer, error_buffer_size, error.what());
        return CIX_PAQ_JOINT_DISCOUNT_EXCEPTION;
    } catch (...) {
        message(error_buffer, error_buffer_size, "PAQ joint_discount raised an unknown exception");
        return CIX_PAQ_JOINT_DISCOUNT_EXCEPTION;
    }

    if (!regular_output_present(expected_output)) {
        message(error_buffer, error_buffer_size, "PAQ joint_discount completed without the requested output");
        return CIX_PAQ_JOINT_DISCOUNT_UPSTREAM_FAILURE;
    }
    return CIX_PAQ_JOINT_DISCOUNT_OK;
}

extern "C" const char *cix_paq_joint_discount_bridge_version(void) {
    return "cix-paq-joint_discount-bridge/1";
}
