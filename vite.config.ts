import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: "dist/client",
    emptyOutDir: true,
    rollupOptions: { input: "src/client/main.tsx", output: { entryFileNames: "assets/app.js", format: "es" } },
  },
});
