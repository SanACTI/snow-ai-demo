import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/analyze': 'http://localhost:8000',
      '/result': 'http://localhost:8000',
      '/batch': 'http://localhost:8000',
      '/pending': 'http://localhost:8000',
      '/decide': 'http://localhost:8000',
      '/logs': 'http://localhost:8000',
    }
  }
})