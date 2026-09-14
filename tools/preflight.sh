#!/usr/bin/env bash
# Pre-push preflight: run BOTH gates before touching main.
#
#   1. verify.py          — the repo's own three-layer check (paper / derived / visualization)
#   2. verify_claims run  — the CI gate (.github/workflows/claims.yml -> alloevil/verify-claims)
#
# The second one is what turns CI red if a claim's shape or its machine check is wrong, so it
# is not optional: a claim that cannot be executed is a receipt that cannot run.
#
# Usage:  tools/preflight.sh            # both gates
#         tools/preflight.sh --fast     # skip executing claim commands (shape check only)
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

status=0
step() { printf '\n\033[1m== %s\033[0m\n' "$1"; }

step "verify.py (three provenance layers)"
python3 verify.py | tail -3 || status=1

# verify_claims: installed package, or a checkout passed via VERIFY_CLAIMS_DIR
VC_PY=""
if python3 -c "import verify_claims" 2>/dev/null; then
  VC_PY="python3"
elif [ -n "${VERIFY_CLAIMS_DIR:-}" ] && [ -d "${VERIFY_CLAIMS_DIR}/verify_claims" ]; then
  VC_PY="PYTHONPATH=${VERIFY_CLAIMS_DIR} python3"
fi

if [ -z "$VC_PY" ]; then
  step "verify_claims — SKIPPED"
  echo "not installed. CI still runs it, so install it locally:"
  echo "  git clone https://github.com/alloevil/verify-claims /tmp/verify-claims"
  echo "  VERIFY_CLAIMS_DIR=/tmp/verify-claims tools/preflight.sh"
  exit $status
fi

step "verify_claims check (claim shape)"
eval "$VC_PY -m verify_claims --root . check" || status=1

if [ "${1:-}" != "--fast" ]; then
  step "verify_claims run (executes every machine check)"
  eval "$VC_PY -m verify_claims --root . run" | tail -4 || status=1
fi

printf '\n'
if [ $status -eq 0 ]; then echo "preflight OK — safe to push"; else echo "preflight FAILED — fix before pushing"; fi
exit $status
