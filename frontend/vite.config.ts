import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    host: '0.0.0.0',
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',  // EVE Backend (MCP Tools)
        changeOrigin: true,
      },
      // Proxy only Agent API endpoints, not the /agent frontend route
      '^/agent/(session|chat|execute|reject)': {
        target: 'http://localhost:8001',  // Copilot Agent Backend
        changeOrigin: true,
      },
      '/agent/stream': {
        target: 'http://localhost:8001',  // Copilot Agent Backend WebSocket
        changeOrigin: true,
        ws: true,  // Enable WebSocket proxying
      },
    },
  },
})
