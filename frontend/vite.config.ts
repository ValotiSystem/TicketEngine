import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // CRITIQUE: in production this proxy does not exist; the frontend
      // calls the API directly or through a reverse proxy (nginx). This
      // is dev-only.
      "/api": {
        target: "http://localhost:5000",
        changeOrigin: true,
      },
    },
  },
});
