import { defineConfig, devices } from "@playwright/test";
import os from "node:os";
import path from "node:path";

// The browser test: the built UI and the real staff server, in front of the keyword mock backend.
// Logins, state.db and writes.log are throwaway files in E2E_DIR. Run with ./run.sh e2e.
export const E2E_DIR = path.join(os.tmpdir(), "crm-e2e");
const PY = process.env.PYTHON ?? "python";
const MOCK_PORT = 8791;
const FRONTEND_PORT = 8792;

export default defineConfig({
  testDir: "e2e",
  testMatch: "*.e2e.ts",
  workers: 1, // one mock backend whose records the tests change
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  use: { baseURL: `http://127.0.0.1:${FRONTEND_PORT}`, trace: "retain-on-failure", ...devices["Desktop Chrome"] },
  webServer: [
    { command: `${PY} -m uvicorn main:app --host 127.0.0.1 --port ${MOCK_PORT}`, cwd: "../../mock_backend", port: MOCK_PORT },
    {
      command: "bash e2e/serve.sh",
      port: FRONTEND_PORT,
      env: {
        PYTHON: PY, E2E_DIR, FRONTEND_PORT: String(FRONTEND_PORT),
        STAFF_FILE: path.join(E2E_DIR, "staff.json"),
        CRM_STATE_DB: path.join(E2E_DIR, "state.db"),
        CRM_WRITES_LOG: path.join(E2E_DIR, "writes.log"),
        CRM_API_BASE_URL: `http://127.0.0.1:${MOCK_PORT}`,
        CRM_SESSION_SECRET: "e2e-only-secret-not-for-real-use-0123456789",
        CRM_HTTPS: "0",
      },
    },
  ],
});
