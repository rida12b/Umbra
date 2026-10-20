import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The engine serves the built app from its own package, on the same origin as the API.
// In development, `npm run dev` proxies the API to a running `umbra-engine serve`.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  build: {
    outDir: "../engine/src/umbra_engine/web",
    emptyOutDir: true,
    chunkSizeWarningLimit: 2500, // elkjs is one large file, loaded once from the local disk
  },
  server: {
    host: "127.0.0.1",
    proxy: { "/v1": `http://127.0.0.1:${process.env.UMBRA_PORT ?? "7811"}` },
  },
});
