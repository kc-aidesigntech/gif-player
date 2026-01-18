import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    // Dev convenience: let the UI call `/api/*` without worrying about CORS/ports.
    proxy: {
      "/api": {
        // Override if your backend is on a different port:
        //   VITE_API_TARGET=http://127.0.0.1:8001 npm run dev
        target: process.env.VITE_API_TARGET ?? "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});

