import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// The backend's own default (see application/backend/app/__main__.py). Override with
// VITE_API_TARGET when the API is served somewhere else.
const API_TARGET = process.env.VITE_API_TARGET ?? 'http://127.0.0.1:8001'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: API_TARGET,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
        // Without this, a backend that isn't listening on API_TARGET surfaces in the browser as a
        // bare "Failed to fetch" with no hint of *why* — which reads as "chat history is broken"
        // rather than "the API is on a different port". Answer with the actual diagnosis instead.
        configure: (proxy) => {
          proxy.on('error', (err, _req, res) => {
            const message =
              `Backend not reachable at ${API_TARGET} (${err.message}). Start it with ` +
              '`python -m app --reload` from application/backend, or point VITE_API_TARGET at ' +
              'the port it is actually running on.'
            console.error(`[vite proxy] ${message}`)
            if ('writeHead' in res && !res.headersSent) {
              res.writeHead(502, { 'Content-Type': 'application/json' })
              res.end(JSON.stringify({ detail: message }))
            } else {
              res.end()
            }
          })
        },
      },
    },
  },
})
