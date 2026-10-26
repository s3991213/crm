#!/usr/bin/env bash
# Start the CRM Assistant.
#
#   ./run.sh              backend + frontend
#   ./run.sh backend      backend only
#   ./run.sh frontend     frontend only (point CRM_API_BASE_URL in frontend/.env at your backend)
#   ./run.sh add-staff <username> "<Full Name>"
#   ./run.sh test         run the test suite (extra args go to pytest; with none, the UI tests run too)
#   ./run.sh e2e          browser test of the staff app against the mock backend (extra args go to Playwright)
#   ./run.sh make-data    synthetic college database (600 students; --students N) and an assistant database from it
#   ./run.sh train-risk   train the at-risk model on the make-data college database and write its validation report
#   ./run.sh evals        run the LLM evals (needs LM Studio; extra args go to evals/run.py)
#   ./run.sh ui-dev       hot-reloading UI on :5173 while working on frontend/ui (run `frontend` alongside)
#
# The staff app (frontend/ui, React) is built automatically when its source changes; that needs Node.js.
# The backend is the LLM one in backend/ (model set in backend/.env). BACKEND=mock uses the keyword mock instead.
# Ports can be changed with BACKEND_PORT=8000 FRONTEND_PORT=8080 ./run.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-8080}"
HOST="${HOST:-127.0.0.1}"   # use HOST=0.0.0.0 to open the frontend to the office network
BACKEND="${BACKEND:-llm}"

# Find the crmenv conda environment
CONDA_BASE="$(conda info --base 2>/dev/null || echo "$HOME/miniconda3")"
ENV_BIN="$CONDA_BASE/envs/crmenv/bin"
if [[ ! -x "$ENV_BIN/python" ]]; then
  echo "Can't find the 'crmenv' conda environment at $ENV_BIN."
  echo "Create it with:  conda create -n crmenv python=3.12 -y"
  exit 1
fi

run_backend() {
  echo "Backend ($BACKEND) → http://localhost:$BACKEND_PORT"
  if [[ "$BACKEND" == "mock" ]]; then
    cd "$ROOT/mock_backend"
    exec "$ENV_BIN/uvicorn" main:app --port "$BACKEND_PORT"
  fi
  cd "$ROOT"
  if [[ ! -f backend/.env ]]; then
    echo "backend/.env is missing. Copy backend/.env.example to backend/.env and set LLM_MODEL."
    exit 1
  fi
  exec "$ENV_BIN/uvicorn" --factory backend.app:default_app --port "$BACKEND_PORT"
}

check_frontend() {
  cd "$ROOT/frontend"
  if [[ ! -f .env ]]; then
    echo "frontend/.env is missing. Copy frontend/.env.example to frontend/.env and fill it in."
    exit 1
  fi
  if [[ ! -s staff.json ]] || [[ "$(tr -d '[:space:]' < staff.json)" == "{}" ]]; then
    echo "No staff logins yet. Let's create the first one."
    if [[ ! -t 0 ]]; then
      echo "Run:  ./run.sh add-staff <username> \"<Full Name>\""
      exit 1
    fi
    read -rp "Username (e.g. priya): " username
    read -rp "Full name (e.g. Priya Shah): " fullname
    if [[ -z "$username" || -z "$fullname" ]]; then
      echo "Both are needed. Nothing was created."
      exit 1
    fi
    "$ENV_BIN/python" add_staff.py "$username" "$fullname" || exit 1
    echo
  fi
}

build_ui() {
  # Rebuild the React app when it's missing or older than its source.
  cd "$ROOT/frontend/ui"
  if [[ -f dist/index.html ]] && [[ -z "$(find src index.html package.json -newer dist/index.html | head -1)" ]]; then
    return
  fi
  if ! command -v npm >/dev/null; then
    echo "The staff app needs building, which needs Node.js (https://nodejs.org)."
    exit 1
  fi
  echo "Building the staff app…"
  [[ -d node_modules ]] || npm ci --no-audit --no-fund
  npm run build --silent
}

run_frontend() {
  build_ui
  cd "$ROOT/frontend"
  echo "Frontend → http://localhost:$FRONTEND_PORT"
  exec "$ENV_BIN/uvicorn" server:app --host "$HOST" --port "$FRONTEND_PORT"
}

case "${1:-all}" in
  backend)
    run_backend
    ;;
  frontend)
    check_frontend
    run_frontend
    ;;
  all)
    check_frontend
    (run_backend) &
    BACKEND_PID=$!
    # Stop the backend and wait for it, so its shutdown messages don't land after the prompt
    trap 'kill $BACKEND_PID 2>/dev/null; wait $BACKEND_PID 2>/dev/null' EXIT INT TERM
    sleep 1
    if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
      echo "Backend failed to start (is port $BACKEND_PORT already in use?)."
      exit 1
    fi
    (run_frontend)
    ;;
  add-staff)
    shift
    cd "$ROOT/frontend"
    exec "$ENV_BIN/python" add_staff.py "$@"
    ;;
  test)
    shift
    cd "$ROOT"
    "$ENV_BIN/python" -m pytest "$@"
    # With no arguments, the UI's own tests run too
    if [[ $# -eq 0 && -d frontend/ui/node_modules ]]; then
      cd frontend/ui && npm test --silent
    fi
    ;;
  e2e)
    shift
    build_ui
    # Downloads the headless browser the first time only
    npx playwright install --only-shell chromium >/dev/null
    PYTHON="$ENV_BIN/python" exec npx playwright test "$@"
    ;;
  ui-dev)
    # Hot-reloading UI on :5173; start the staff server in another terminal with ./run.sh frontend
    cd "$ROOT/frontend/ui"
    [[ -d node_modules ]] || npm ci --no-audit --no-fund
    exec npm run dev
    ;;
  make-data)
    shift
    cd "$ROOT"
    exec "$ENV_BIN/python" -m college_db.generate --crm-db backend/data/crm-synthetic.db "$@"
    ;;
  train-risk)
    shift
    cd "$ROOT"
    exec "$ENV_BIN/python" -m backend.train_risk "$@"
    ;;
  evals)
    shift
    cd "$ROOT"
    exec "$ENV_BIN/python" -m evals.run "$@"
    ;;
  *)
    sed -n '2,16p' "$0" | sed 's/^# \{0,1\}//'
    exit 1
    ;;
esac
