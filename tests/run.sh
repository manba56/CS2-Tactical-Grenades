#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# CS2 Tactics Suite — Automated Test Runner (Baota / Linux)
# ═══════════════════════════════════════════════════════════════
#
# Usage:
#   ./run.sh                  # Full test suite (API only)
#   ./run.sh --smoke          # Smoke tests only (< 30s)
#   ./run.sh --e2e            # Include Playwright E2E tests
#   ./run.sh --allure         # Run + serve Allure report at :8880
#   ./run.sh --api-only       # API tests only
#
# Env vars:
#   TEST_API_BASE   — API base URL (default http://127.0.0.1:8008)
#   TEST_WEB_BASE   — Frontend URL (default http://127.0.0.1:5174)
#   TEST_ADMIN_BASE — Admin URL   (default http://127.0.0.1:5175)
#   ZENTAO_URL/PW   — ZenTao connection (optional)
# ═══════════════════════════════════════════════════════════════

set -euo pipefail
cd "$(dirname "$0")"

# ── Colors ────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
log()  { echo -e "${GREEN}[TEST]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
err()  { echo -e "${RED}[FAIL]${NC} $*"; }

# ── Defaults ──────────────────────────────────────────────
API_BASE="${TEST_API_BASE:-http://127.0.0.1:8008}"
WEB_BASE="${TEST_WEB_BASE:-http://127.0.0.1:5174}"
ADMIN_BASE="${TEST_ADMIN_BASE:-http://127.0.0.1:5175}"
ALLURE_DIR="./allure-results"
PYTEST_ARGS=()

# ── Parse flags ───────────────────────────────────────────
E2E=false; SMOKE=false; SERVE_ALLURE=false; API_ONLY=false
for arg in "$@"; do
  case "$arg" in
    --e2e)       E2E=true ;;
    --smoke)     SMOKE=true ;;
    --allure)    SERVE_ALLURE=true ;;
    --api-only)  API_ONLY=true ;;
    *)           PYTEST_ARGS+=("$arg") ;;
  esac
done

# ── Check API alive ───────────────────────────────────────
log "Checking API health at ${API_BASE}..."
if ! curl -sf "${API_BASE}/api/health" > /dev/null 2>&1; then
  err "API is not reachable at ${API_BASE}"
  echo "   Start it first: cd cs2-api && uvicorn app.main:app --host 0.0.0.0 --port 8008"
  exit 1
fi
log "API OK"

# ── Install deps ──────────────────────────────────────────
if ! python3 -c "import pytest" 2>/dev/null; then
  warn "Installing test dependencies..."
  pip3 install -r requirements-test.txt
fi

# Install Playwright browsers if E2E
if $E2E; then
  if ! python3 -c "import playwright" 2>/dev/null; then
    pip3 install playwright
  fi
  if ! python3 -m playwright install chromium --with-deps 2>/dev/null; then
    warn "Playwright browser install may need sudo. Try: sudo python3 -m playwright install chromium --with-deps"
  fi

  # Check frontend
  if ! curl -sf "${WEB_BASE}" > /dev/null 2>&1; then
    warn "Frontend ${WEB_BASE} not reachable — E2E tests will likely fail"
  fi
fi

# ── Build pytest command ──────────────────────────────────
CMD=("python3" "-m" "pytest")

if $SMOKE; then
  CMD+=("-m" "smoke")
  log "Mode: SMOKE only"
fi

if $API_ONLY; then
  CMD+=("api/")
  log "Mode: API only"
elif ! $E2E; then
  CMD+=("api/")
  log "Mode: API only (use --e2e for browser tests)"
else
  CMD+=("api/" "e2e/")
  log "Mode: API + E2E"
fi

CMD+=(
  "-v"
  "--tb=short"
  "--color=yes"
  "--alluredir=${ALLURE_DIR}"
  "--clean-alluredir"
  "${PYTEST_ARGS[@]}"
)

log "Running: ${CMD[*]}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── Run ───────────────────────────────────────────────────
set +e
"${CMD[@]}"
EXIT_CODE=$?
set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ $EXIT_CODE -eq 0 ]; then
  log "All tests PASSED"
else
  err "Tests FAILED (exit code: ${EXIT_CODE})"
  # ZenTao auto-reporting is handled by conftest.py hook
fi

# ── Allure report ─────────────────────────────────────────
if $SERVE_ALLURE; then
  if command -v allure &> /dev/null; then
    log "Generating Allure HTML report..."
    allure generate "${ALLURE_DIR}" -o ./allure-report --clean
    log "Serving Allure at http://0.0.0.0:8880"
    allure open ./allure-report -p 8880 &
    sleep 1
    echo "   → Open http://$(hostname -I 2>/dev/null | awk '{print $1}' || echo '127.0.0.1'):8880"
  else
    warn "allure CLI not installed. Install: https://docs.qameta.io/allure-report/"
    warn "Results saved to ${ALLURE_DIR}"
  fi
fi

exit $EXIT_CODE
