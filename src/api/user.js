import request from '@/utils/request'

/**
 * 用户注册
 */
export function register(data) {
  return request.post('/user/register', data)
}

/**
 * 用户登录 —— 返回 access_token + refresh_token
 */
export function login(data) {
  return request.post('/user/login', data)
}

/**
 * 刷新令牌
 */
export function refreshToken(data) {
  return request.post('/user/refresh', data)
}

/**
 * 退出登录
 */
export function logout() {
  return request.post('/user/logout')
}

/**
 * 获取当前用户信息
 */
export function getUserInfo() {
  return request.get('/user/info')
}

/**
 * 修改用户信息
 */
export function updateUser(data) {
  return request.put('/user/update', data)
}

/**
 * 修改密码
 */
export function updatePassword(data) {
  return request.put('/user/updatePwd', data)
}
