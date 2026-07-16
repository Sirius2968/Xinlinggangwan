import axios from 'axios'
import { ElMessage } from 'element-plus'

// ============================================================
// 创建 axios 实例
// ============================================================
const request = axios.create({
  baseURL: '/api',
  timeout: 10000,
})

// 缓存 token，直接从 localStorage 裸 key 读取
const _loadToken = () => localStorage.getItem('access_token') || ''
let cachedToken = _loadToken()
export function setAuthToken(token) {
  cachedToken = token || ''
}

// ============================================================
// 刷新令牌逻辑
// ============================================================
let isRefreshing = false
let pendingRequests = []  // 等待刷新的请求队列

function onRefreshed(newToken) {
  pendingRequests.forEach((cb) => cb(newToken))
  pendingRequests = []
}

function addPendingRequest(cb) {
  pendingRequests.push(cb)
}

export async function tryRefreshToken() {
  const refreshToken = localStorage.getItem('refresh_token')
  if (!refreshToken) return null

  try {
    const res = await axios.post('/api/user/refresh', { refresh_token: refreshToken })
    if (res.data?.code === 200) {
      const { access_token, refresh_token } = res.data.data
      localStorage.setItem('access_token', access_token)
      localStorage.setItem('refresh_token', refresh_token)
      setAuthToken(access_token)
      return access_token
    }
  } catch {
    // 刷新失败
  }
  return null
}

// ============================================================
// 请求拦截器
// ============================================================
request.interceptors.request.use(
  (config) => {
    if (cachedToken) {
      config.headers.Authorization = 'Bearer ' + cachedToken
    }
    if (import.meta.env.DEV) {
      console.log('>>> 请求:', config.method?.toUpperCase(), config.baseURL + config.url, config.data ? JSON.stringify(config.data) : '')
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  },
)

// ============================================================
// 响应拦截器 —— 含自动刷新令牌
// ============================================================
request.interceptors.response.use(
  (response) => {
    const res = response.data
    if (res && res.code !== undefined) {
      const code = Number(res.code)
      const successCodes = [200, 1, 0]
      if (successCodes.includes(code)) {
        return res
      }
      console.error('业务错误，后端返回 code:', res.code, '完整响应:', JSON.stringify(res))
      ElMessage.error(res.msg || res.message || '请求失败')
      return Promise.reject(new Error(res.msg || res.message || '请求失败'))
    }
    return res
  },
  async (error) => {
    const status = error.response?.status
    const body = error.response?.data
    const originalRequest = error.config

    // 401 自动尝试刷新令牌（排除刷新接口自身和登录接口）
    if (status === 401 && !originalRequest._retry && !originalRequest.url?.includes('/user/refresh')) {
      if (!isRefreshing) {
        isRefreshing = true
        let newToken = null
        try {
          newToken = await tryRefreshToken()
        } finally {
          isRefreshing = false
        }

        if (newToken) {
          onRefreshed(newToken)
          originalRequest.headers.Authorization = 'Bearer ' + newToken
          originalRequest._retry = true
          return request(originalRequest)
        }

        // 刷新失败 → 清空状态
        onRefreshed(null)
        const { useUserStore } = await import('@/stores/user')
        useUserStore().logout()
        ElMessage.error('登录已过期，请重新登录')
        return Promise.reject(error)
      }

      // 已有刷新进行中，将请求排入队列
      return new Promise((resolve) => {
        addPendingRequest((newToken) => {
          if (newToken) {
            originalRequest.headers.Authorization = 'Bearer ' + newToken
            originalRequest._retry = true
            resolve(request(originalRequest))
          } else {
            resolve(Promise.reject(error))
          }
        })
      })
    }

    switch (status) {
      case 401: {
        const { useUserStore } = await import('@/stores/user')
        useUserStore().logout()
        ElMessage.error(body?.msg || '登录已过期，请重新登录')
        break
      }
      case 403:
        ElMessage.error(body?.msg || '没有权限访问')
        break
      case 404:
        ElMessage.error(body?.msg || '请求的资源不存在')
        break
      case 500:
        ElMessage.error(body?.msg || '服务器内部错误')
        break
      default:
        ElMessage.error(body?.msg || error.message || '网络异常，请稍后重试')
    }

    return Promise.reject(error)
  },
)

export default request
