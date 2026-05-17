#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# CS2 Tactics Suite — JMeter Performance Test Runner
# ═══════════════════════════════════════════════════════════════
#
# Usage:
#   ./run_perf.sh load        # 50 concurrent users, 5 min
#   ./run_perf.sh stress      # 10→200 step ramp, find limit
#   ./run_perf.sh stability   # 100 concurrent users, 30 min
#
# Prerequisites:
#   sudo apt-get install jmeter
# ═══════════════════════════════════════════════════════════════

set -euo pipefail
cd "$(dirname "$0")"

API_BASE="${2:-127.0.0.1:8008}"
TEST_TYPE="${1:-load}"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
log()  { echo -e "${GREEN}[PERF]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
err()  { echo -e "${RED}[FAIL]${NC} $*"; }

# Validate JMeter installed
if ! command -v jmeter &> /dev/null; then
  err "JMeter not found. Install: sudo apt-get install jmeter"
  exit 1
fi

# Map test type to JMX file
case "$TEST_TYPE" in
  load)      JMX="load_test.jmx" ;;
  stress)    JMX="stress_test.jmx" ;;
  stability) JMX="stability_test.jmx" ;;
  *)
    err "Unknown test type: $TEST_TYPE (use: load | stress | stability)"
    exit 1
    ;;
esac

if [ ! -f "$JMX" ]; then
  err "JMX file not found: $JMX"
  exit 1
fi

# Create results directory
mkdir -p results

TIMESTAMP=$(date +%Y%m%d-%H%M%S)
RESULT_FILE="results/${TEST_TYPE}_${TIMESTAMP}.jtl"
REPORT_DIR="results/${TEST_TYPE}_report_${TIMESTAMP}"

log "Running: $TEST_TYPE test"
log "Target:  $API_BASE"
log "Results: $RESULT_FILE"

# Check API is reachable
if ! curl -sf "http://${API_BASE}/api/health" > /dev/null 2>&1; then
  warn "API not reachable at http://${API_BASE}/api/health — tests may fail"
fi

# Run JMeter non-GUI
jmeter -n \
  -t "$JMX" \
  -Japi_base="$API_BASE" \
  -l "$RESULT_FILE" \
  -e \
  -o "$REPORT_DIR" \
  || true  # Don't fail on perf thresholds, collect results

# Print quick summary
if [ -f "$RESULT_FILE" ]; then
  LINE_COUNT=$(wc -l < "$RESULT_FILE")
  log "Collected $LINE_COUNT sample lines"
  log "HTML report: $REPORT_DIR/index.html"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Report: $REPORT_DIR/index.html"
echo "  Open:   xdg-open $REPORT_DIR/index.html"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
