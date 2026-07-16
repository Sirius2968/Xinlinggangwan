import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { setAuthToken } from '@/utils/request'

/**
 * 用户状态管理 —— 双令牌模式
 * access_token：15 分钟有效
 * refresh_token：14 天有效，用于自动续期
 */
export const useUserStore = defineStore('user', () => {
  // ---- 状态 ----
  const accessToken = ref(localStorage.getItem('access_token') || '')
  const refreshToken = ref(localStorage.getItem('refresh_token') || '')
  const userInfo = ref(JSON.parse(localStorage.getItem('userInfo') || 'null'))

  // ---- 计算属性 ----
  const isLoggedIn = computed(() => !!accessToken.value)

  // ---- 方法 ----

  /** 登录成功：存储双令牌和用户信息 */
  function setLogin(data) {
    accessToken.value = data.access_token || data.accessToken || ''
    refreshToken.value = data.refresh_token || data.refreshToken || ''
    userInfo.value = data.userInfo || data
    localStorage.setItem('access_token', accessToken.value)
    localStorage.setItem('refresh_token', refreshToken.value)
    localStorage.setItem('userInfo', JSON.stringify(userInfo.value))
    setAuthToken(accessToken.value)
  }

  /** 刷新令牌：更新双令牌 */
  function setTokens(data) {
    accessToken.value = data.access_token
    refreshToken.value = data.refresh_token
    localStorage.setItem('access_token', accessToken.value)
    localStorage.setItem('refresh_token', refreshToken.value)
    setAuthToken(accessToken.value)
  }

  function logout() {
    accessToken.value = ''
    refreshToken.value = ''
    userInfo.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('userInfo')
    setAuthToken('')
  }

  return { accessToken, refreshToken, userInfo, isLoggedIn, setLogin, setTokens, logout }
})
