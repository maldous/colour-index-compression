#!/bin/bash
# Owner-only: select the existing positively read-qualified variable explicitly.
set -eu
set +x
if [[ $# != 1 || "$1" != LINEAR_API_KEY ]]; then
  echo 'Explicit selected variable LINEAR_API_KEY required' >&2
  exit 1
fi
selected_variable=$1
: "${!selected_variable:?Existing owner provider environment required}"
printf '%s' "${!selected_variable}" | sudo -n /usr/bin/python3 /home/user/src/cix-approved-migration/successor-preparation/service/owner-provision.py "$selected_variable"
