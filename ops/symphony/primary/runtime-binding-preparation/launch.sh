#!/bin/sh
set -eu
runtime=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd -P)
export ROOTDIR="$runtime" BINDIR="$runtime/erts-16.4/bin" EMU=beam PROGNAME=erl
export RELEASE_DISTRIBUTION=none RELEASE_COOKIE=unused_local_no_distribution
export RELEASE_VM_ARGS="$runtime/launch.vm.args"
export CIX_BINDING_BOOTSTRAP="$runtime/bootstrap.exs"
exec "$runtime/bin/symphony" eval 'Code.require_file(System.fetch_env!("CIX_BINDING_BOOTSTRAP"))' "$@"
