# Source-reviewed Sonar refactor qualification

Native source d3a2cd416e49f93403d1dbd348a3e9a45db66ec6, portable all-feature
release-lto build passed. Seven chain library tests passed in one execution,
including exact cache selection/admission and transform restoration. Eight
focused CLI footer/override checks passed; kept-open input SIGINT exits2 without
SIGKILL. Clippy all-target/all-feature exited0: zero Clippy rule or unused-variable
findings;241 dead-code compiler-warning target instances remain.

A separate fresh latest-Docker Sonar scan indexed82 files and reported zero
current Rust issues; see sonar-d3a2/. VendorC/C++ and experimental files outside
scan scope were not analysed. This is not all compiler warnings resolved.

The refactor was adversarially reviewed: it preserves candidate order/ties,
cache memory/ownership, model/history updates, framing/checksum order and footer
allocation/cancellation/EOF grammar. A slice-capacity compile defect was caught
and fixed before build. No unsafe code, new dependency or model-policy change.

Sealed current-host binaries and SHA hashes are in native-release.json, under
benchmark-work/release-d3a2/final/. This is focused qualification, not the full
current suite, large-pipe replay or final performance/build/PGO closure. Earlier
6ac large-pipe evidence retains its exact source scope. No corpus benchmark,
PTT5 run, Hutter run, Actions or publication was restarted.

Live cgroups: CPUs8,10/quota2/no swap,2GiB build/test/Clippy or256MiB CLI;
active build temporary cap1.5GiB. Sampled cgroup peaks are lower bounds. Native
source/runner hashes are frozen; historical toolchain/hardware evidence is reused,
not described as a new pre-bound toolchain capture. Stale template success text
mentions chain cache/idle pipeline; actual executed cases are in receipts.
