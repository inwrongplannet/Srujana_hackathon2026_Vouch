#!/usr/bin/env bash
# Regenerates frontend types from the backend OpenAPI spec so the two sides never drift.
#
# Env: OPENAPI_SRC  URL or file of the OpenAPI JSON (default http://localhost:8000/openapi.json)
#      TYPES_OUT    output file (default frontend/src/types/api.d.ts)
# Needs Node (uses `npx openapi-typescript`). Adjust the defaults once the stack is chosen,
# and log the generator dependency with /decide.
set -euo pipefail
cd "$(dirname "$0")/.."

SRC="${OPENAPI_SRC:-http://localhost:8000/openapi.json}"
OUT="${TYPES_OUT:-frontend/src/types/api.d.ts}"

if [ ! -f frontend/package.json ]; then
  echo "types: frontend/ is not scaffolded yet (no package.json), nothing to do" >&2
  exit 0
fi
if ! command -v npx >/dev/null 2>&1; then
  echo "types: npx not found; install Node.js" >&2
  exit 1
fi

mkdir -p "$(dirname "$OUT")"
echo "types: $SRC -> $OUT"
npx --yes openapi-typescript "$SRC" -o "$OUT"
