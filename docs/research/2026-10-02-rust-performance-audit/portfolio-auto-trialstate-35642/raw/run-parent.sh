#!/bin/sh
set -eu
/tmp/cix-portfolioauto-target-parent/release/cix --best --explain -f -o /tmp/cix-portfolioauto-receipts/parent.cix /tmp/cix-portfolioauto-receipts/input.bin > /tmp/cix-portfolioauto-receipts/parent.stdout 2> /tmp/cix-portfolioauto-receipts/parent.trace
rc=$?
sleep 20
exit "$rc"
