#!/usr/bin/env bash
# Starts the staff server for the browser test, with throwaway logins, state and logs in $E2E_DIR.
# Two logins: "newbie" still has a temporary password, "tester" has chosen their own.
set -euo pipefail
PY="${PYTHON:-python}"
rm -rf "$E2E_DIR" && mkdir -p "$E2E_DIR"
cd "$(dirname "$0")/../.."
"$PY" -c "
import staff_auth
staff_auth.set_staff('newbie', 'New Starter', 'temp-pass-123')
staff_auth.set_staff('tester', 'Test Staff', 'temp-pass-123')
staff_auth.change_password('tester', None, 'tester-pass-456', 'tester-pass-456')
"
exec "$PY" -m uvicorn server:app --host 127.0.0.1 --port "$FRONTEND_PORT"
