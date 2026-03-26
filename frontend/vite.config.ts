import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  // Electron 需要相对路径 (file:// 协议)
  base: process.env.ELECTRON === 'true' ? './' : '/',
  server: {
    port: 3000,
    proxy: {
      '/api': 'http://localhost:8000',
      '/ws': { target: 'ws://localhost:8000', ws: true },
    },
  },
  build: {
    outDir: 'dist',
    // Electron 环境下使用相对路径
    assetsDir: 'assets',
  },
})
