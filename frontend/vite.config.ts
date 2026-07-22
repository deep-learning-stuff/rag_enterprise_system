import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// En docker-compose, BACKEND_URL apunta al servicio backend por su nombre de red.
// En local (fuera de docker), cae a localhost:8000.
const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    // Docker Desktop en Windows no propaga inotify a través del bind mount, así que
    // el watcher de Vite no se entera de los cambios sin polling.
    watch: { usePolling: true },
    // El navegador pide /health y /documents al dev server y Vite los reenvía al
    // backend: así el fetch funciona sin CORS ni URLs hardcodeadas.
    proxy: {
      "/health": backendUrl,
      "/documents": backendUrl,
      "/search": backendUrl,
      "/answer": backendUrl,
      "/gaps": backendUrl,
    },
  },
});
