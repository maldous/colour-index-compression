#!/bin/bash
# Preparation only. Final workflow and supported secure owner binding must exist first.
set -eu
set +x
# The activation workflow is deliberately absent until lifecycle acceptance is complete.
test -r /home/user/src/cix-approved-migration/config/WORKFLOW.active.md
: "${CREDENTIALS_DIRECTORY:?Secure systemd credential binding required}"
test -r "$CREDENTIALS_DIRECTORY/linear-api-key"
LINEAR_API_KEY=$(cat "$CREDENTIALS_DIRECTORY/linear-api-key")
test -n "$LINEAR_API_KEY"
export LINEAR_API_KEY
exec /home/user/src/cix-approved-migration/runtime-cix243-v1/launch.sh \
  --i-understand-that-this-will-be-running-without-the-usual-guardrails \
  --logs-root /home/user/src/cix-approved-migration/runtime-logs \
  /home/user/src/cix-approved-migration/config/WORKFLOW.active.md
