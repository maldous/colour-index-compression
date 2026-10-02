# Commands

The following outer command produced `systemd-run.raw.log`:

```sh
sudo -n systemd-run --unit=cix-bounded-reader-cleanup-20261003b --property=User=user --property=CPUAccounting=yes --property=AllowedCPUs=18 --property=MemoryAccounting=yes --property=MemoryMax=1G --property=MemorySwapMax=0 --wait --pipe --collect /bin/bash /home/user/src/cix-bounded-reader-cleanup-a628/docs/research/2026-10-03-bounded-reader-cleanup-a628/run-evidence.sh
```

`run-evidence.sh` retains the exact build, test, archive, decode, hash, and
comparison commands, with explicit stable `cargo`, `RUSTC`, and `RUSTDOC`.

The assembled-source qualification used:

```sh
sudo -n systemd-run --unit=cix-bounded-reader-assembled-20261003c --property=User=user --property=CPUAccounting=yes --property=AllowedCPUs=18 --property=MemoryAccounting=yes --property=MemoryMax=1G --property=MemorySwapMax=0 --wait --pipe --collect /bin/bash /home/user/src/cix-bounded-reader-cleanup-a628/docs/research/2026-10-03-bounded-reader-cleanup-a628/run-assembled-evidence.sh
```
