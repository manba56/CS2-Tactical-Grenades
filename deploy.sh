#!/usr/bin/env bash
set -Eeuo pipefail

# Webhook-friendly deployment script for CS2 Tactics Suite.
# Expected server layout:
#   /www/wwwroot/cs2-tactics
#
# Optional environment variables:
#   PROJECT_DIR=/www/wwwroot/cs2-tactics
#   DEPLOY_BRANCH=main
#   API_SERVICE=cs2-api
#   API_HEALTH_URL=http://127.0.0.1:8008/api/health
#   INSTALL_BACKEND_DEPS=1
#   INSTALL_FRONTEND_DEPS=1

PROJECT_DIR="${PROJECT_DIR:-/www/wwwroot/cs2-tactics}"
DEPLOY_BRANCH="${DEPLOY_BRANCH:-main}"
API_SERVICE="${API_SERVICE:-cs2-api}"
API_HEALTH_URL="${API_HEALTH_URL:-http://127.0.0.1:8008/api/health}"
INSTALL_BACKEND_DEPS="${INSTALL_BACKEND_DEPS:-1}"
INSTALL_FRONTEND_DEPS="${INSTALL_FRONTEND_DEPS:-1}"
LOCK_DIR="${DEPLOY_LOCK_DIR:-/tmp/cs2-tactics-deploy.lock}"

API_DIR="$PROJECT_DIR/cs2-api"
WEB_DIR="$PROJECT_DIR/cs2-web"
ADMIN_DIR="$PROJECT_DIR/cs2-admin"

log() {
  printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

fail() {
  log "ERROR: $*"
  exit 1
}

run() {
  log "$*"
  "$@"
}

acquire_lock() {
  if ! mkdir "$LOCK_DIR" 2>/dev/null; then
    log "Another deployment is already running. Skipping this request."
    exit 0
  fi
  trap 'rmdir "$LOCK_DIR" 2>/dev/null || true' EXIT
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "Missing command: $1"
}

update_code() {
  [[ -d "$PROJECT_DIR/.git" ]] || fail "$PROJECT_DIR is not a git repository"
  cd "$PROJECT_DIR"

  git config --global --add safe.directory "$PROJECT_DIR" >/dev/null 2>&1 || true
  run git fetch origin "$DEPLOY_BRANCH"
  run git checkout "$DEPLOY_BRANCH"
  run git pull --ff-only origin "$DEPLOY_BRANCH"
}

install_backend_deps() {
  [[ "$INSTALL_BACKEND_DEPS" == "1" ]] || return 0
  [[ -f "$API_DIR/requirements.txt" ]] || return 0

  cd "$API_DIR"
  run python3 -m pip install -r requirements.txt
}

build_frontend() {
  local app_dir="$1"
  local app_name="$2"

  [[ -d "$app_dir" ]] || fail "$app_name directory not found: $app_dir"
  cd "$app_dir"

  if [[ "$INSTALL_FRONTEND_DEPS" == "1" ]]; then
    if [[ -f package-lock.json ]]; then
      run npm ci
    else
      run npm install
    fi
  fi

  if npm run | grep -q "typecheck"; then
    run npm run typecheck
  fi
  run npm run build
}

restart_api() {
  if command -v systemctl >/dev/null 2>&1 && systemctl list-unit-files "$API_SERVICE.service" >/dev/null 2>&1; then
    if [[ "$(id -u)" -eq 0 ]]; then
      run systemctl restart "$API_SERVICE"
    elif command -v sudo >/dev/null 2>&1; then
      run sudo -n systemctl restart "$API_SERVICE"
    else
      fail "Need root or passwordless sudo to restart $API_SERVICE"
    fi
    return 0
  fi

  if command -v supervisorctl >/dev/null 2>&1 && supervisorctl status "$API_SERVICE" >/dev/null 2>&1; then
    run supervisorctl restart "$API_SERVICE"
    return 0
  fi

  fail "Could not find systemd or supervisor service named $API_SERVICE"
}

check_health() {
  for _ in 1 2 3 4 5; do
    if curl -fsS "$API_HEALTH_URL" >/dev/null; then
      log "API health check passed: $API_HEALTH_URL"
      return 0
    fi
    sleep 2
  done

  fail "API health check failed: $API_HEALTH_URL"
}

main() {
  acquire_lock
  require_command git
  require_command python3
  require_command npm
  require_command curl

  log "Starting deploy: project=$PROJECT_DIR branch=$DEPLOY_BRANCH"
  update_code
  install_backend_deps
  build_frontend "$WEB_DIR" "cs2-web"
  build_frontend "$ADMIN_DIR" "cs2-admin"
  restart_api
  check_health
  log "Deployment completed successfully"
}

main "$@"
