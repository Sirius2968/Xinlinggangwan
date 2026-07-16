import { ref } from 'vue'
import { defineStore } from 'pinia'
import { setAuthToken } from '@/utils/request'

/**
 * 用户状态管理
 *
 * Token 存储在 localStorage 裸 key（access_token / refresh_token），
 * 不与 Pinia persist 耦合，避免两套存储 key 不同步的问题。
 * Pinia 仅管理 userInfo 和 isLoggedIn 的响应式状态。
 */
export const useUserStore = defineStore('user', () => {
  const userInfo = ref(null)
  // 必须是 ref 而非 computed — localStorage.getItem() 不参与 Vue 响应式，
  // 用 computed 会导致无依赖、缓存永不更新
  const isLoggedIn = ref(!!localStorage.getItem('access_token'))

  function setLogin(data) {
    const at = data.access_token || data.accessToken || ''
    const rt = data.refresh_token || data.refreshToken || ''
    localStorage.setItem('access_token', at)
    localStorage.setItem('refresh_token', rt)
    userInfo.value = data.userInfo || data
    isLoggedIn.value = true
    setAuthToken(at)
  }

  function setTokens(data) {
    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
    isLoggedIn.value = true
    setAuthToken(data.access_token)
  }

  function logout() {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    userInfo.value = null
    isLoggedIn.value = false
    setAuthToken('')
  }

  return { userInfo, isLoggedIn, setLogin, setTokens, logout }
}, {
  persist: {
    key: 'user',
    storage: localStorage,
    pick: ['userInfo'],
  },
})
