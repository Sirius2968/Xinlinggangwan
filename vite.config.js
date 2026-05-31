import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

// ============================================================
// CDN 外部化：生产构建时走 CDN，通过 Import Map 让浏览器解析裸模块
// ============================================================
const CDN_EXTERNALS = ['vue', 'vue-router', 'pinia', 'element-plus', 'axios', 'echarts']

/**
 * ESM 格式的 CDN 地址
 * esm.sh 自动将 npm 包转为浏览器 ESM，国内不通可换成 jsdelivr
 */
const IMPORT_MAP = {
  vue: 'https://esm.sh/vue@3.5',
  'vue-router': 'https://esm.sh/vue-router@4',
  pinia: 'https://esm.sh/pinia@3',
  'element-plus': 'https://esm.sh/element-plus@2.9',
  axios: 'https://esm.sh/axios@1',
  echarts: 'https://esm.sh/echarts@5',
}

/**
 * 构建时注入 <script type="importmap">，告诉浏览器去哪找外部模块
 */
function importMapPlugin() {
  return {
    name: 'vite-importmap-cdn',
    apply: 'build',
    transformIndexHtml(html) {
      const mapJson = JSON.stringify({ imports: IMPORT_MAP }, null, 2)
      return {
        html,
        tags: [
          {
            tag: 'script',
            attrs: { type: 'importmap' },
            children: mapJson,
            injectTo: 'head-prepend',
          },
        ],
      }
    },
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    vueDevTools(),
    // CDN 模式仅适合海外部署，国内/本地关闭更优
    // importMapPlugin(),
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
      output: {
        manualChunks(id) {
          // echarts 超大（1MB+），只有心理健康页面用，单独拆出按需加载
          if (id.includes('node_modules/echarts')) return 'echarts'
          // element-plus 组件按页面拆，避免首屏全量加载
          if (id.includes('node_modules/element-plus')) {
            // 按组件目录分组，减少单个 chunk 体积
            if (id.includes('/es/components/')) return 'vendor/element-ui'
            return 'vendor/element-core'
          }
        },
      },
    },
    // 小于此阈值的模块不单独拆 chunk，减少 HTTP 请求数
    cssMinify: true,
  },
})
