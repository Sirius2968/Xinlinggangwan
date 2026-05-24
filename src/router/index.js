import { createRouter, createWebHistory } from 'vue-router'
import FrontLayout from '@/layouts/FrontLayout.vue'
import BackLayout from '@/layouts/BackLayout.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    // ===== 前台 (front) =====
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
          path: 'counselors',
          name: 'Counselors',
          component: () => import('@/views/front/Counselors.vue'),
        },
        {
          path: 'about',
          name: 'About',
          component: () => import('@/views/front/About.vue'),
        },
        {
          path: 'login',
          name: 'Login',
          component: () => import('@/views/front/Login.vue'),
        },
      ],
    },

    // ===== 后台 (back) =====
    {
      path: '/back',
      component: BackLayout,
      // 后台页面需要登录才能访问
      meta: { requiresAuth: true },
      children: [
        {
          path: '',
          name: 'Dashboard',
          component: () => import('@/views/back/Dashboard.vue'),
        },
        {
          path: 'articles',
          name: 'BackArticles',
          component: () => import('@/views/back/ArticleManage.vue'),
        },
        {
          path: 'users',
          name: 'BackUsers',
          component: () => import('@/views/back/UserManage.vue'),
        },
      ],
    },
  ],
})

// ============================================================
// 全局路由守卫
// ============================================================
router.beforeEach((to) => {
  const token = localStorage.getItem('token')

  // 访问需要登录的页面但没有 token → 跳到登录页
  if (to.meta.requiresAuth && !token) {
    return { name: 'Login', query: { redirect: to.fullPath } }
  }

  // 已登录状态下访问登录页 → 直接跳首页（无需重复登录）
  if (to.name === 'Login' && token) {
    return { name: 'Home' }
  }
})

export default router
