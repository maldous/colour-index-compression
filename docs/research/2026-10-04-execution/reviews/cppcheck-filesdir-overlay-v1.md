# Cppcheck FILESDIR overlay v1

The private Cppcheck binary is compiled with `FILESDIR` set to
`/usr/lib/x86_64-linux-gnu/cppcheck`. It loads `std.cfg` from
`FILESDIR/cfg` before explicit `--library` arguments can help. The staged v2
runtime contains that complete configuration directory; its manifest is
`31d1547d1e2073eb0c8a846f50afab56b66f6fcf0f897c738c5ac358d7b8a1c7` and
its `std.cfg` is
`f8fb548544a04903c5195890d3461ff4c9a5605d5299dcee146bfe73796625de`.

## Retained failed approach

The direct leaf bind was tested by `cppcheck-header-canary-v3` and failed
before Cppcheck ran: Bubblewrap could not create the absent
`/usr/lib/x86_64-linux-gnu/cppcheck` destination below the already readonly
root mount (`Can't mkdir … Read-only file system`). The v3 receipt is
`212470a5fe38ce0fc9f0416a6a5a7a4117b650956694c2c522b41a2d22c4915d`.

Bubblewrap can create missing destination parents in general, but that does
not override a readonly parent introduced earlier by `--ro-bind / /`.
Consequently, direct leaf binding is not a workable setup here and must not be
used as current advice.

## Proven working setup

`cppcheck-header-canary-v4` established a readonly architecture-directory
mirror, and v9 completed the same setup successfully after compiler
preprocessing. The mirror is made in the job work directory as symlinks for
every existing child of `/usr/lib/x86_64-linux-gnu`, each pointing to the host
directory rebound at `/mnt`; it adds only one `cppcheck` symlink to the staged
configuration directory. Bubblewrap then applies these readonly mounts in
order:

```text
--ro-bind / /
--ro-bind /usr/lib/x86_64-linux-gnu /mnt
--ro-bind <work>/arch-overlay /usr/lib/x86_64-linux-gnu
-- <runtime>/usr/lib/x86_64-linux-gnu/ld-linux-x86-64.so.2 \
   --library-path <runtime>/usr/lib/x86_64-linux-gnu \
   <runtime>/usr/bin/cppcheck ...
```

This replaces the architecture mount only inside the sandbox. The mirror makes
all original children available through `/mnt` and adds the required private
`cppcheck` leaf, while the staged loader and explicit library path keep the
Cppcheck ELF closure private. It does not mutate, copy, or omit host library
children. V4 verified the host `glibconfig.h` hash was visible in the sandbox;
its receipt is `cedf8f05bcf9431d11f0f7f95854fe1a354faaf7716b731cc755599347ca97e9`.

## Header handling and acceptance

The mirror alone bootstrapped Cppcheck but v4 retained preprocessing/parser
errors from macro-heavy GIO and 7-Zip inputs. V9 runs each selected compiler
command with `-E`, preserves source line markers, normalizes GNU line markers
to standard `#line`, and removes only analyzer-copy GCC diagnostic pragmas and
pedantic `__extension__` markers. Production and vendor sources are untouched.
The v9 receipt
(`54d60ffd670f105f52d44a3ad51d3158cfec3bf5866391d641ceaf5b9eb265de`)
has return code zero, no fatal configuration diagnostics, and the preserved
host `glibconfig.h` hash. Its preprocessing receipt is
`d6433372c863768a8c2bd8a6404173b0d83d69eb2ecedaaa1208d02ff3fe23a2`.

Use the v9 mirror and preprocessing/projection pattern for a later scanner
job. Keep explicit `--library` arguments only as ordinary configuration after
the binary has loaded its mandatory stock `std.cfg`. The job receipt should
record the runtime, overlay-child count, host-header visibility, preprocessing
hashes and absence of bootstrap/fatal-configuration diagnostics. No tool,
host library tree, source, or scan input was changed by this review.
