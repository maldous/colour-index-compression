# Inspect-snapshot redaction

Docker inspect snapshots preserve image identity, tmpfs mounts, networking, CPU,
and memory controls. They can also contain environment-file values. The future
harness serializes inspect JSON after replacing the value of every `Env` entry
whose name contains `token`, `password`, `secret`, `credential`, or `api_key`
with `[REDACTED]`.

This preserves the environment-variable name and all noncredential Docker
configuration needed for review. The v7 and v8 evidence copies were redacted
separately after token revocation; their frozen harness copies remain historical
execution inputs. The current harness performs the redaction before a future
snapshot is written. It already accepts later frozen source revisions through
`--expected-revision`, including main and chain helper changes.
