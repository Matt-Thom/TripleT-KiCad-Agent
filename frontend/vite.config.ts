import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  // Load env file from the project root (one level up)
  const env = loadEnv(mode, path.resolve(__dirname, '..'), '')
  const port = env.PORT || '8080'
  
  return {
    plugins: [react()],
    server: {
      proxy: {
        '/api': {
          target: `http://localhost:${port}`,
          changeOrigin: true,
        },
      },
    },
  }
})
