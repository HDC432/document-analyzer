import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,   // binds to 0.0.0.0 inside the container
    port: 3000,
    // No proxy — browser talks directly to VITE_API_URL (http://localhost:8000)
  },
})
