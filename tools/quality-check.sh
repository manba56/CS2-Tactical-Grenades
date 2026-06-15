#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKIP_BACKEND=0
SKIP_FRONTEND=0
SKIP_BUILD=0
MODE="full"

for arg in "$@"; do
  case "$arg" in
    --mode=*) MODE="${arg#*=}" ;;
    --quick) MODE="quick" ;;
    --full) MODE="full" ;;
    --release) MODE="release" ;;
    --smoke) MODE="smoke" ;;
    --skip-backend) SKIP_BACKEND=1 ;;
    --skip-frontend) SKIP_FRONTEND=1 ;;
    --skip-build) SKIP_BUILD=1 ;;
    *)
      echo "Unknown option: $arg" >&2
      echo "Usage: tools/quality-check.sh [--quick|--full|--release|--smoke|--mode=MODE] [--skip-backend] [--skip-frontend] [--skip-build]" >&2
      exit 2
      ;;
  esac
done

case "$MODE" in
  quick|full|release|smoke) ;;
  *)
    echo "Unknown mode: $MODE" >&2
    exit 2
    ;;
esac

if [[ "$MODE" == "quick" || "$MODE" == "smoke" ]]; then
  SKIP_BUILD=1
fi

step() {
  echo
  echo "[quality] $*"
}

pytest_timeout_args=()
if python3 -c "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('pytest_timeout') else 1)" >/dev/null 2>&1; then
  pytest_timeout_args=(--timeout=60)
else
  echo "[quality] pytest-timeout not installed; running without --timeout"
fi

echo "[quality] Repo: $REPO_ROOT"
echo "[quality] Mode: $MODE"

if [[ "$SKIP_BACKEND" -eq 0 ]]; then
  backend_target="unit"
  if [[ "$MODE" == "smoke" ]]; then
    backend_target="unit/test_schemas_unit.py"
  fi
  step "backend tests ($backend_target)"
  (cd "$REPO_ROOT/tests" && python3 -m pytest "$backend_target" -q "${pytest_timeout_args[@]}")
fi

run_node_app_checks() {
  local app_dir="$1"
  if [[ -d "$REPO_ROOT/$app_dir/tests" ]]; then
    step "$app_dir unit tests"
    (cd "$REPO_ROOT/$app_dir" && npm run test:unit)
  fi

  step "$app_dir typecheck"
  (cd "$REPO_ROOT/$app_dir" && npm run typecheck)

  if [[ "$SKIP_BUILD" -eq 0 ]]; then
    step "$app_dir build"
    (cd "$REPO_ROOT/$app_dir" && npm run build)
  fi
}

if [[ "$SKIP_FRONTEND" -eq 0 ]]; then
  run_node_app_checks "cs2-web"
  run_node_app_checks "cs2-admin"
fi

step "git whitespace check"
(cd "$REPO_ROOT" && git diff --check)

echo
echo "[quality] All checks passed"
