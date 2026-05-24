import axios from 'axios'
import { ElMessage } from 'element-plus'

// ============================================================
// 创建 axios 实例
// baseURL 指向后端服务地址，开发环境通过 Vite 代理转发
// ============================================================
const request = axios.create({
  baseURL: '/api',        // 所有请求自动加上 /api 前缀
  timeout: 10000,         // 10 秒超时，超时自动取消请求
})

// ============================================================
// 请求拦截器 —— 发请求之前做的事
// ============================================================
request.interceptors.request.use(
  (config) => {
    // 从 localStorage 取出 token，塞到请求头的 Authorization 字段
    // 后端通过这个 token 识别"你是谁"
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = 'Bearer ' + token
    }
    console.log('>>> 请求:', config.method?.toUpperCase(), config.baseURL + config.url, config.data ? JSON.stringify(config.data) : '')
    return config // 必须返回 config，否则请求发不出去
  },
  (error) => {
    // 请求还没发出去就报错了（比如网络断开）
    return Promise.reject(error)
  },
)

// ============================================================
// 响应拦截器 —— 收到响应之后做的事
// ============================================================
request.interceptors.response.use(
  (response) => {
    const res = response.data

    // 1. 如果后端返回了 code 字段，按 code 判断成败
    // 注意：code 可能是数字 200 也可能是字符串 "200"，统一转数字比较
    if (res && res.code !== undefined) {
      const code = Number(res.code)
      const successCodes = [200, 1, 0]
      if (successCodes.includes(code)) {
        return res
      }
      // code 不在成功列表中 → 真正的业务错误
      console.error('业务错误，后端返回 code:', res.code, '完整响应:', JSON.stringify(res))
      ElMessage.error(res.msg || res.message || '请求失败')
      return Promise.reject(new Error(res.msg || res.message || '请求失败'))
    }

    // 2. 没有 code 字段 → HTTP 2xx 就视为成功，直接把整个 body 返回
    return res
  },
  (error) => {
    // HTTP 层面的错误（404、500、网络断开等）
    const status = error.response?.status

    switch (status) {
      case 401:
        localStorage.removeItem('token')
        ElMessage.error('登录已过期，请重新登录')
        window.location.href = '/login'
        break
      case 403:
        ElMessage.error('没有权限访问')
        break
      case 404:
        ElMessage.error('请求的资源不存在')
        break
      case 500:
        ElMessage.error('服务器内部错误')
        break
      default:
        ElMessage.error(error.message || '网络异常，请稍后重试')
    }

    return Promise.reject(error)
  },
)

export default request
