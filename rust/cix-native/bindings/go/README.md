# CIX native Go binding

This optional cgo consumer wraps the installed `cix-native` C ABI. It uses
`pkg-config cix-native`, `cix.h`, and `cix_stream.h`; it neither builds CIX nor
invokes the CIX CLI.

Its module path is the deliberately non-public development identity
`example.invalid/cix/native`. It requires Go 1.20 or later and has no Go module
dependencies outside the standard library.

`Context` provides complete-buffer CIX operations. `Encoder` and `Decoder`
provide the independent native CIXG1 block stream only. They do not expose
full-engine routes, retained-history streams, CIXM6, or a native cancellation
handle because those capabilities are absent from `cix_stream.h`.

Every wrapper serializes calls and `Close` on its own native handle. A handle
must not be copied after first use. `Cancel` is a local gate: it stops later Go
calls before entering C, but cannot interrupt a call already in the native
ABI. `Reset` clears that local gate and resets the native stream.

`Options.OutputLimit` and `Options.MemoryLimit` are passed to the C ABI.
`OutputLimit` is also enforced before Go allocates buffer output and across a
stream's produced bytes. Complete-buffer calls first make the ABI's required-
size probe and then make the actual codec call, so they can double codec work;
they are not a static upper-bound calculation. Go input/output slices and the
wrapper's temporary output allocation add to native live memory. The ABI
documents no process-RSS hard cap.

Run the focused installed-SDK consumer test after installing the qualified
library and its `cix-native.pc` metadata:

```sh
PKG_CONFIG_PATH=/qualified/prefix/lib/pkgconfig go test ./...
```
