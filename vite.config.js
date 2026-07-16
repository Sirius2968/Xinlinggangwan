import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'
import fs from 'node:fs'
import path from 'node:path'

// ============================================================
// CDN 配置
// CDN_BASE_URL: 生产构建时的静态资源 CDN 地址
//   示例: https://cdn.example.com/assets/
//   留空则使用相对路径，由 nginx 直接托管
// ============================================================
const CDN_BASE_URL = process.env.CDN_BASE_URL || '/'

// ============================================================
// CDN 外部化依赖（esm.sh / jsdelivr）
//   启用后 Vue/Router/Pinia 等第三方库从 CDN 加载，不进 bundle
//   可减少构建体积，加速首次访问
// ============================================================
const ENABLE_CDN_EXTERNAL = process.env.CDN_EXTERNAL === 'true'

const IMPORT_MAP = {
  vue: 'https://esm.sh/vue@3.5',
  'vue-router': 'https://esm.sh/vue-router@4',
  pinia: 'https://esm.sh/pinia@3',
  'element-plus': 'https://esm.sh/element-plus@2.9',
  axios: 'https://esm.sh/axios@1',
  echarts: 'https://esm.sh/echarts@5',
}

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

// ============================================================
// 构建时自动生成 version.json（outDir 由 configResolved 捕获）
// ============================================================
let resolvedOutDir = 'dist'
function versionBumpPlugin() {
  return {
    name: 'vite-version-bump',
    apply: 'build',
    configResolved(config) {
      resolvedOutDir = config.build.outDir
    },
    closeBundle() {
      const p = path.resolve(resolvedOutDir, 'version.json')
      const now = new Date().toISOString()
      fs.writeFileSync(p, JSON.stringify({ version: now }))
      console.log(`  [version-bump] → ${now}`)
    },
  }
}

export default defineConfig({
  base: CDN_BASE_URL,
  plugins: [
    vue(),
    vueDevTools(),
    Components({
      resolvers: [ElementPlusResolver({ importStyle: 'css' })],
      dts: false, // 不生成 .d.ts，减少文件变动
    }),
    versionBumpPlugin(),
    ...(ENABLE_CDN_EXTERNAL ? [importMapPlugin()] : []),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
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
  css: {
    preprocessorOptions: {
      scss: {
        additionalData: `@use "@/styles/variables" as *; @use "@/styles/mixins" as *;`,
      },
    },
  },
  build: {
    // 静态资源使用内容哈希命名，利于 CDN 长效缓存
    assetsInlineLimit: 4096,
    rollupOptions: {
      output: {
        // 入口 chunk 名带哈希
        entryFileNames: 'assets/[name]-[hash].js',
        chunkFileNames: 'assets/[name]-[hash].js',
        assetFileNames: 'assets/[name]-[hash].[ext]',
        manualChunks(id) {
          if (id.includes('node_modules/echarts')) return 'echarts'
          if (id.includes('node_modules/element-plus')) {
            if (id.includes('/es/components/')) return 'vendor/element-ui'
            return 'vendor/element-core'
          }
        },
      },
    },
    cssMinify: true,
  },
})
