import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

// ============================================================
// CDN 外部化：生产构建时走 CDN，开发环境仍用 node_modules
// ============================================================
const CDN_EXTERNALS = {
  vue: 'Vue',
  'vue-router': 'VueRouter',
  pinia: 'Pinia',
  'element-plus': 'ElementPlus',
  axios: 'axios',
  echarts: 'echarts',
}

/**
 * 仅在 build 时注入 CDN <script> 标签
 * 使用 jsdelivr CDN，也可替换为 unpkg / 私有 CDN
 */
function cdnPlugin() {
  const CDN_BASE = 'https://cdn.jsdelivr.net/npm'
  const scripts = [
    `${CDN_BASE}/vue@3/dist/vue.global.prod.js`,
    `${CDN_BASE}/vue-router@4/dist/vue-router.global.prod.js`,
    `${CDN_BASE}/pinia@2/dist/pinia.iife.prod.js`,
    `${CDN_BASE}/element-plus/dist/index.full.min.js`,
    `${CDN_BASE}/axios/dist/axios.min.js`,
    `${CDN_BASE}/echarts@5/dist/echarts.min.js`,
  ]

  return {
    name: 'vite-cdn-external',
    apply: 'build',
    transformIndexHtml(html) {
      return {
        html,
        tags: scripts.map((src) => ({
          tag: 'script',
          attrs: { src, crossorigin: 'anonymous' },
          injectTo: 'body-prepend',
        })),
      }
    },
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    vueDevTools(),
    cdnPlugin(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    rollupOptions: {
      external: Object.keys(CDN_EXTERNALS),
      output: {
        globals: CDN_EXTERNALS,
      },
    },
  },
})
