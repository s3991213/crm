import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// `npm run dev` serves the UI with hot reload on :5173 and passes /api to the staff server (./run.sh frontend).
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: { "/api": `http://localhost:${process.env.FRONTEND_PORT ?? 8080}` },
  },
});
