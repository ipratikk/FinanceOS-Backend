#!/usr/bin/env bash
# bootstrap.sh — first-time project setup
#
# Usage:
#   ./bootstrap.sh           # full Docker mode (all services in containers)
#   ./bootstrap.sh --local   # local dev mode (infra in Docker, node/python run locally)
#   ./bootstrap.sh --help

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODE="docker"

# ── colours ────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

info()    { echo -e "${CYAN}▶ $*${RESET}"; }
success() { echo -e "${GREEN}✔ $*${RESET}"; }
warn()    { echo -e "${YELLOW}⚠ $*${RESET}"; }
error()   { echo -e "${RED}✖ $*${RESET}" >&2; }
header()  { echo -e "\n${BOLD}${CYAN}═══ $* ═══${RESET}"; }
die()     { error "$*"; exit 1; }

# ── args ───────────────────────────────────────────────────────────────────
for arg in "$@"; do
  case "$arg" in
    --local) MODE="local" ;;
    --help|-h)
      echo "Usage: ./bootstrap.sh [--local]"
      echo ""
      echo "  (default)  Full Docker: all services run in containers."
      echo "  --local    Local dev: postgres/redis in Docker; node and python run on host."
      exit 0
      ;;
    *) die "Unknown argument: $arg. Run ./bootstrap.sh --help" ;;
  esac
done

# ── docker compose command ──────────────────────────────────────────────────
if docker compose version &>/dev/null; then
  DC="docker compose"
elif docker-compose version &>/dev/null; then
  DC="docker-compose"
else
  DC=""
fi

# ── prerequisites ───────────────────────────────────────────────────────────
header "Checking prerequisites"

MISSING=()

if ! command -v docker &>/dev/null; then
  MISSING+=("docker  →  https://docs.docker.com/get-docker/")
fi
if [[ -z "$DC" ]]; then
  MISSING+=("docker compose (v2) or docker-compose (v1)  →  https://docs.docker.com/compose/install/")
fi
if [[ "$MODE" == "local" ]]; then
  if ! command -v node &>/dev/null; then
    MISSING+=("node  →  https://nodejs.org/ (v18+)")
  fi
  if ! command -v npm &>/dev/null; then
    MISSING+=("npm")
  fi
  if ! command -v python3 &>/dev/null; then
    MISSING+=("python3  →  https://www.python.org/ (3.11+)")
  fi
fi

if [[ ${#MISSING[@]} -gt 0 ]]; then
  error "Missing prerequisites:"
  for dep in "${MISSING[@]}"; do
    error "  • $dep"
  done
  exit 1
fi

success "All prerequisites satisfied"

# ── .env files ──────────────────────────────────────────────────────────────
header "Environment files"

if [[ ! -f "$REPO_ROOT/.env" ]]; then
  cp "$REPO_ROOT/.env.example" "$REPO_ROOT/.env"
  success "Created .env from .env.example"
else
  success ".env already exists — skipping"
fi

# node_api/.env is needed for local prisma commands
NODE_ENV_FILE="$REPO_ROOT/node_api/.env"
if [[ ! -f "$NODE_ENV_FILE" ]]; then
  grep "DATABASE_URL" "$REPO_ROOT/.env.example" > "$NODE_ENV_FILE"
  success "Created node_api/.env"
else
  success "node_api/.env already exists — skipping"
fi

# ── git hooks ───────────────────────────────────────────────────────────────
header "Git hooks"

git -C "$REPO_ROOT" config core.hooksPath .githooks
success "core.hooksPath set to .githooks"
success "Pre-commit hook: auto-generates docs/API.md from GraphQL schema"

# ── docker setup ─────────────────────────────────────────────────────────────
wait_healthy() {
  local service="$1"
  local max=30
  info "Waiting for $service to be healthy..."
  for i in $(seq 1 $max); do
    status=$($DC -f "$REPO_ROOT/docker-compose.yml" ps --format json "$service" 2>/dev/null \
      | python3 -c "import sys,json; d=json.load(sys.stdin); print(d[0].get('Health','') if isinstance(d,list) else d.get('Health',''))" 2>/dev/null || echo "")
    if [[ "$status" == "healthy" ]]; then
      success "$service is healthy"
      return 0
    fi
    sleep 2
  done
  warn "$service health check timed out — it may still be starting"
}

if [[ "$MODE" == "docker" ]]; then
  header "Docker (full)"

  info "Building and starting all services..."
  $DC -f "$REPO_ROOT/docker-compose.yml" up --build -d

  wait_healthy postgres
  wait_healthy redis

  info "Waiting for node-api (runs DB migrations on startup)..."
  sleep 5  # node-api waits for postgres then migrates; give it a moment

  success "All services started"
  echo ""
  echo -e "${BOLD}Services:${RESET}"
  echo "  GraphQL API   →  http://localhost:4000/graphql"
  echo "  Health check  →  http://localhost:4000/health"
  echo "  Python parser →  http://localhost:8000 (internal)"
  echo "  Postgres      →  localhost:5432"
  echo "  Redis         →  localhost:6379"

else
  # ── local dev mode ──────────────────────────────────────────────────────
  header "Docker (infra only)"

  info "Starting postgres and redis..."
  $DC -f "$REPO_ROOT/docker-compose.yml" up -d postgres redis

  wait_healthy postgres
  wait_healthy redis

  # ── Node.js ─────────────────────────────────────────────────────────────
  header "Node.js"

  if [[ ! -d "$REPO_ROOT/node_api/node_modules" ]]; then
    info "Installing npm dependencies..."
    npm --prefix "$REPO_ROOT/node_api" ci
    success "npm ci done"
  else
    success "node_modules already present — skipping npm ci"
  fi

  info "Generating Prisma client..."
  (cd "$REPO_ROOT/node_api" && npx prisma generate)
  success "Prisma client generated"

  info "Running database migrations..."
  (cd "$REPO_ROOT/node_api" && npx prisma migrate deploy)
  success "Migrations applied"

  # ── Python ──────────────────────────────────────────────────────────────
  header "Python"

  VENV="$REPO_ROOT/python_service/.venv"
  if [[ ! -d "$VENV" ]]; then
    info "Creating virtual environment..."
    python3 -m venv "$VENV"
    success "venv created at python_service/.venv"
  else
    success "venv already exists — skipping"
  fi

  info "Installing Python dependencies..."
  "$VENV/bin/pip" install --quiet --upgrade pip
  "$VENV/bin/pip" install --quiet -r "$REPO_ROOT/python_service/requirements.txt"
  success "Python dependencies installed"

  echo ""
  echo -e "${BOLD}To start services:${RESET}"
  echo ""
  echo "  # Terminal 1 — Node.js API"
  echo "  cd node_api && npm run dev"
  echo ""
  echo "  # Terminal 2 — Python parser"
  echo "  cd python_service && source .venv/bin/activate && uvicorn main:app --reload --port 8000"
  echo ""
  echo -e "${BOLD}Endpoints:${RESET}"
  echo "  GraphQL API   →  http://localhost:4000/graphql"
  echo "  Python parser →  http://localhost:8000 (internal)"
fi

# ── done ─────────────────────────────────────────────────────────────────────
header "Done"
success "Bootstrap complete"
if [[ "$MODE" == "local" ]]; then
  echo ""
  echo -e "  API reference: ${CYAN}docs/API.md${RESET}"
fi
