#!/bin/bash
# OWNER ONLY, in their already configured server shell. Do not paste secret values.
set -eu
set +x
: "${LINEAR_API_KEY:?Existing authorized provider environment required}"
printf '%s' "$LINEAR_API_KEY" | sudo -n /usr/bin/python3 /home/user/src/cix-approved-migration/config/owner-provision.py
