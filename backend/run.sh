#!/usr/bin/env bash
set -euo pipefail

# Run this from the repo root or from backend/ to start the app using the
# backend virtualenv if present.
cd "$(dirname "$0")"

if [ -f env/bin/activate ]; then
  # shellcheck source=/dev/null
  source env/bin/activate
fi

if [ -x env/bin/uvicorn ]; then
  exec env/bin/uvicorn app.main:app --reload --app-dir . "$@"
else
  exec uvicorn app.main:app --reload --app-dir . "$@"
fi
