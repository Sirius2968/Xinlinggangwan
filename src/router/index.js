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

// 已登录状态下访问登录页 → 直接跳首页
router.beforeEach((to) => {
  const token = localStorage.getItem('token')
  if (to.name === 'Login' && token) {
    return { name: 'Home' }
  }
})

export default router
