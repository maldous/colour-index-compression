# Correct unified-cgroup readback

The performance wrapper used `awk -F::` and read field 3. For the real unified record `0::/path`, that separator produces two fields and therefore an empty path. The corrected single-colon separator preserves the empty controller field and reads the actual cgroup path.

Sixteen local receipt/scaling/identity unit tests passed, including actual shell parsing of unified-only and mixed-controller fixtures. An actual root system unit preflight invoked the wrapper around `/bin/true`: exit zero, process affinity 8, cpuset 8, memory.max 1 GiB, memory.swap.max zero, all read back and matched by the existing qualifier. This is harness validation, not compression performance evidence.

Launch: `sudo -n systemd-run --wait --pipe --unit=cix-cgroup-readback-preflight --property=User=user --property=MemoryMax=1G --property=MemorySwapMax=0 --property=CPUAffinity=8 --property=AllowedCPUs=8 /usr/bin/python3 benchmark-work/rust-performance-audit/cgroup-readback-preflight.py`. The copied script binds the actual helper digest. Any future frozen benchmark plan must use the new helper identity. Existing historical measurements are not retrospectively qualified or rewritten.
