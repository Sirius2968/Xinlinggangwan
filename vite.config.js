import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    vueDevTools(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
  },
  server: {
    proxy: {
      // AI 对话接口 → 本地后端
      '/api/chat': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      // 其他接口（用户、文章等）→ 远程后端
      '/api': {
        target: 'http://159.75.169.224:1235',
        changeOrigin: true,
      },
    },
  },
})
