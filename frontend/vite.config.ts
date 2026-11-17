import react from "@vitejs/plugin-react";
import { defaultExclude, defineConfig } from "vitest/config";

// В Docker прокси смотрит на сервис backend, локально — на localhost.
// Переменная без префикса VITE_, чтобы внутренний URL не попадал в браузерный бандл.
const apiTarget = process.env.API_PROXY_TARGET ?? "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    strictPort: true,
    proxy: {
      "/api": { target: apiTarget, changeOrigin: true },
    },
  },
  preview: {
    host: "0.0.0.0",
    port: 5173,
    strictPort: true,
    proxy: {
      "/api": { target: apiTarget, changeOrigin: true },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    css: true,
    exclude: [...defaultExclude, "e2e/**"],
  },
});
