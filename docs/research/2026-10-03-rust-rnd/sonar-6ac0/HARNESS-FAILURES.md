# Retained harness failures

`run-v4` reached and passed the live role-specific cgroup checks, then the
SonarQube server failed during CE plugin extraction before token creation. Its
captured server log reports `No space left on device` below
`/opt/sonarqube/temp/ce-exploded-plugins`; no scanner invocation or scan result
was produced. The failure is unqualified evidence, retained by the root-run
output directory.

The next unique run uses the same 4 GiB server cgroup, zero swap, CPU quota and
CPU set, with the server tempfs raised from 256 MiB to 1536 MiB. Data and logs
remain 1 GiB and 128 MiB respectively. Docker inspect and live mount receipts
are retained before and after each run, so the configured tmpfs caps can be
read back with the live cgroup limits.

`run-v5` passed the server tempfs stage but received HTTP 400 from the initial
password-change endpoint before token creation or scanner launch. `run-v6`
uses a URL-encoded password with guaranteed upper-case, lower-case, digit, and
special characters. Any repeat HTTP diagnostic records only its status and a
scrubbed response body; administrator, generated-password, and token values
are replaced before the file is written.

`run-v6` completed server setup, token generation, and token revocation. Its
scanner receipt captured the requested 1 GiB, zero-swap, two-CPU limits, but
the scanner image does not provide a `hostname` executable, leaving the receipt
hostname empty and correctly holding the pre-scan barrier closed. `run-v7`
reads `/proc/sys/kernel/hostname` instead. The barrier releases a scan only
after this concrete setup cause is fixed and all identity and resource checks
pass; it is not a retry mechanism. Guarded scanner failures now retain scanner
logs before cleanup.

`run-v7` passed the receipt gate and launched the scanner, but scanner-managed
JRE provisioning failed before analysis because its bounded `/tmp` mount was
`noexec`. `run-v8` retains the 512 MiB tmpfs cap and adds the explicit `exec`
mount option. Docker inspect must match that option and the captured live mount
information must not contain `noexec` for `/tmp` before the scan is released.
