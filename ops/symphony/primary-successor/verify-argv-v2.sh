#!/bin/sh
# Run only in the admitted artifact helper, after derivation. No CLI/service call.
set -eu
runtime=/home/user/src/cix-approved-migration/runtime-cix243-v2
export ROOTDIR="$runtime" BINDIR="$runtime/erts-16.4/bin" EMU=beam PROGNAME=erl
export RELEASE_DISTRIBUTION=none RELEASE_COOKIE=unused_local_no_distribution
export RELEASE_VM_ARGS="$runtime/launch.vm.args"
exec "$runtime/bin/symphony" eval '
expected = ["CIX244_ARGV_PROBE", "--i-understand-that-this-will-be-running-without-the-usual-guardrails", "workflow path with spaces.md", "--logs-root", "logs path with spaces", "--port", "0"]
if System.argv() != expected, do: raise("official eval argument forwarding mismatch")
if List.keymember?(Application.started_applications(), :symphony_elixir, 0), do: raise("unexpected Symphony startup during probe")
IO.puts("CIX244_OFFICIAL_EVAL_ARGV_FORWARDING_PASS_NO_SYMPHONY_START")
' CIX244_ARGV_PROBE --i-understand-that-this-will-be-running-without-the-usual-guardrails 'workflow path with spaces.md' --logs-root 'logs path with spaces' --port 0
