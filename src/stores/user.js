import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { setAuthToken } from '@/utils/request'

/**
 * 用户状态管理
 * 登录后 token + 用户信息存入 localStorage
 * 下次打开网站时自动恢复登录状态
 */
export const useUserStore = defineStore('user', () => {
  // ---- 状态 ----
  const token = ref(localStorage.getItem('token') || '')
  const userInfo = ref(JSON.parse(localStorage.getItem('userInfo') || 'null'))

  // ---- 计算属性 ----
  const isLoggedIn = computed(() => !!token.value)

  // ---- 方法 ----

  /** 登录成功：存储 token 和用户信息 */
  function setLogin(data) {
    token.value = data.token
    userInfo.value = data.userInfo || data
    localStorage.setItem('token', data.token)
    localStorage.setItem('userInfo', JSON.stringify(userInfo.value))
    setAuthToken(data.token)
  }

  function logout() {
    token.value = ''
    userInfo.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('userInfo')
    setAuthToken('')
  }

  return { token, userInfo, isLoggedIn, setLogin, logout }
})
