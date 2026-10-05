# Exact reconstructible ARM64 Rust sysroot retirement

This operation follows preservation review e284cbd4 and admission a372f068. It removes only the 61 named regular files and six empty directories bound by the independently verified manifest. The retained archive, metadata, restoration source, parent receipts and smoke results remain unchanged. Future ARM64 Rust use requires a separately admitted 164 MB restore and new smoke. No distribution capability is waived.

All unlinks use no-follow directory file descriptors and fixed relative path components. Current whole-tree metadata, archive equality, protected hashes and no-reader evidence are checked before the first removal. Any mismatch or syscall failure stops; partial completion is retained and requires a separate narrowly specified recovery action.
