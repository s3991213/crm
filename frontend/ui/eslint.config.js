// Lints the UI and its tests: `npm run lint` (CI runs it too).
import js from "@eslint/js";
import reactHooks from "eslint-plugin-react-hooks";
import globals from "globals";
import tseslint from "typescript-eslint";

export default tseslint.config(
  { ignores: ["dist", "playwright-report", "test-results"] },
  {
    files: ["**/*.{ts,tsx}"],
    extends: [js.configs.recommended, tseslint.configs.recommended],
    languageOptions: { globals: globals.browser },
  },
  // Only the app: Playwright fixtures call a function named `use`, which the hooks rules mistake for a hook.
  { files: ["src/**/*.{ts,tsx}"], extends: [reactHooks.configs.flat.recommended] },
);
