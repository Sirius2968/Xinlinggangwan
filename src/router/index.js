import { createRouter, createWebHistory } from 'vue-router'
import FrontLayout from '@/layouts/FrontLayout.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      component: FrontLayout,
      children: [
        {
          path: '',
          name: 'Home',
          component: () => import('@/views/front/Home.vue'),
        },
        {
          path: 'articles',
          name: 'Articles',
          component: () => import('@/views/front/Articles.vue'),
        },
        {
          path: 'article-share',
          name: 'ArticleShare',
          component: () => import('@/views/front/ArticleShare.vue'),
        },
        {
          path: 'counselors',
          name: 'Counselors',
          component: () => import('@/views/front/Counselors.vue'),
        },
        {
          path: 'mental-health',
          name: 'MentalHealth',
          component: () => import('@/views/front/MentalHealth.vue'),
        },
        {
          path: 'login',
          name: 'Login',
          component: () => import('@/views/front/Login.vue'),
        },
      ],
    },
  ],
})

// ============================================================
// 版本检测 —— 每次路由切换时对比服务器 /version.json
// 检测到新版本后自动清理 localStorage 并强制刷新
// ============================================================
const VERSION_URL = '/version.json'
let currentVersion = localStorage.getItem('app_version') || null
let checkPromise = null

async function checkVersion() {
  try {
    const res = await fetch(`${VERSION_URL}?t=${Date.now()}`)
    if (!res.ok) return
    const data = await res.json()
    const serverVersion = data.version

    if (!currentVersion) {
      // 首次访问：记住当前版本
      currentVersion = serverVersion
      localStorage.setItem('app_version', serverVersion)
      return
    }

    if (serverVersion !== currentVersion) {
      // 检测到更新 → 清理持久化数据（保留 user token）→ 强制刷新
      const keysToRemove = []
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i)
        if (key && key !== 'user' && key !== 'app_version') {
          keysToRemove.push(key)
        }
      }
      keysToRemove.forEach((k) => localStorage.removeItem(k))
      localStorage.setItem('app_version', serverVersion)
      window.location.reload()
    }
  } catch {
    // 网络异常时静默跳过
  }
}

router.beforeEach(async (to) => {
  // 已登录状态下访问登录页 → 直接跳首页
  const token = localStorage.getItem('access_token')
  if (to.name === 'Login' && token) {
    return { name: 'Home' }
  }

  // 每次路由切换时检测版本更新（复用同一次请求）
  if (!checkPromise) {
    checkPromise = checkVersion().finally(() => { checkPromise = null })
  }
  await checkPromise
})

export default router
