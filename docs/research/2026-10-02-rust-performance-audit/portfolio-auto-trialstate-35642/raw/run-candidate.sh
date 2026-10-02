#!/bin/sh
set -eu
/tmp/cix-portfolioauto-target-candidate/release/cix --best --explain -f -o /tmp/cix-portfolioauto-receipts/candidate.cix /tmp/cix-portfolioauto-receipts/input.bin > /tmp/cix-portfolioauto-receipts/candidate.stdout 2> /tmp/cix-portfolioauto-receipts/candidate.trace
rc=$?
sleep 20
exit "$rc"
