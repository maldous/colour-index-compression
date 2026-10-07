# RC20 native C buffer foundation

`rust/cix-native/include/cix.h` defines ABI v1.  It provides opaque contexts,
versioned and sized options, complete-buffer encode/decode, caller-owned output
storage, required-size reporting, and a bounded context-owned diagnostic. The
options pointer must provide a readable prefix through `struct_size`; v1 needs
the complete `cix_options_v1` layout. A writable creation output is set null on
failure.

Each context snapshots options at creation. Calls on one context serialize;
distinct contexts may operate concurrently. Destroy only after all calls using
that context return: concurrent destruction is invalid. The API starts no
program, changes no signals, environment, or process limits. Ordinary status
errors emit no diagnostics; a contained Rust panic may still invoke the host's
global panic hook before returning `CIX_STATUS_PANIC`, so embedding hosts that
require silent panic reporting must set their own process-wide policy.

This is deliberately not RC21 streaming: there are no process, flush, finish,
reset, callback, or chunk functions.  It also has no C cancellation-handle
transfer.  The native core's cooperative cancellation facility is not exposed
by this ABI revision, and `memory_limit` is an option passed to the native
codec rather than a caller-process RSS hard cap.

For both buffer functions, null input is valid only with zero length and null
output only with zero capacity. `needed` is always required and must not
overlap either buffer. A too-small caller buffer returns
`CIX_STATUS_OUTPUT_TOO_SMALL`, reports the complete required size, and leaves
that output buffer untouched. If the context's `output_limit` is reached before
a complete result is available, the call returns `CIX_STATUS_RESOURCE_LIMIT`
with `needed=0`; this is not a retry-with-more-caller-buffer condition. CIX
never returns an allocated output pointer, so no CIX buffer-free API is needed.

The focused Rust contract test is `rust/cix-native/tests/c_api_contract.rs`;
unit coverage also includes a short options prefix, invalid ranges, overlap,
and UTF-8 diagnostic truncation. `rust/cix-native/tests/c_api_consumer.c` and
`tests/c_api_installed_consumer.sh` form the independent installed-C consumer:
after staging the freshly built cdylib as `PREFIX/lib/libcix_native.so` and the
provided header as `PREFIX/include/cix.h`, invoke the script with that prefix
and an empty work directory.
