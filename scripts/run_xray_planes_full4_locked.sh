#!/usr/bin/env bash
# One finite PAQ v215 image-plane gate.  The lock covers the pause and every
# child process, so it cannot overlap controlled evidence measurements.
set -euo pipefail

exec flock -w 21600 /home/user/src/cix-evidence-baseline-20260929/evidence/baseline-20260929/raw/measurement.lock /bin/bash -c '
  sleep 15
  exec timeout --signal=TERM --kill-after=60s 1200 /home/user/src/colour-index-compression/.venv/bin/python -m benchmarks.paq_image_planes --output /home/user/src/colour-index-compression/results/leaderboard/paq-image-planes-full4-v215-boundary-20260929 --cpu 2 --version v215 --options -4 --whole --shifts 4
'
