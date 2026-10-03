# Focused rank and footer qualification

Source f579d8ac582ba2907cf6b5326c6892e7c96eb205. Portable release-lto build passed.
One targeted rank test passed with six boundary/degenerate fixtures and malformed
mode checks, proving exact pre-change bytes for the tested configurations.
Eight focused CLI footer/override cases passed; see cli-result.json.

Clippy exited zero but reported 241 dead-code, 16 unused-variable and eight
instances of one too-many-arguments rule across targets. The latter two issues
were fixed at 6ac05f8e9; dead-code notices remain. Later release evidence is in
release-6ac0/. This packet does not claim current full-suite or Sonar completion.

Live cgroup receipts prove CPU affinity, memory and no swap. The launcher
requested two CPU quota, but cpu.max/path were not read back in this older
packet. Toolchain hashes were not pre-bound here. A stale template success
message in stdout describes chain cache; actual executed cases are the rank
and footer/override cases recorded in receipts. Preserve the original log.
