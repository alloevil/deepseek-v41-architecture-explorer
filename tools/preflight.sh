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

step "browser smoke (?smoke=1: module must evaluate to the end)"
CHROME="$(command -v google-chrome || command -v chromium || command -v /opt/google/chrome/chrome || true)"
if [ -z "$CHROME" ]; then
  echo "no chrome/chromium found — skipping (CI does not run this step)"
else
  # start the no-cache server if it is not already up, then load the page without rendering
  if ! curl -sf -o /dev/null "http://127.0.0.1:8741/"; then
    python3 serve.py 8741 >/dev/null 2>&1 &
    SRV=$!
    sleep 1
  fi
  SMOKE_ERR="$(mktemp)"
  timeout 75 "$CHROME" --headless=new --disable-gpu --no-sandbox --disable-dev-shm-usage \
    --window-size=420,320 --virtual-time-budget=5000 --enable-logging=stderr --v=0 \
    --dump-dom "http://127.0.0.1:8741/?smoke=1" 2>"$SMOKE_ERR" >/dev/null || true
  if grep -qiE "uncaught" "$SMOKE_ERR"; then
    echo "FAILED — module threw while evaluating:"
    grep -iE "uncaught" "$SMOKE_ERR" | head -3
    status=1
  else
    echo "ok — module evaluated with no uncaught error"
  fi
  rm -f "$SMOKE_ERR"
  [ -n "${SRV:-}" ] && kill "$SRV" 2>/dev/null
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
