import request from '@/utils/request'

/**
 * 用户注册
 * @param {Object} data - { phone, password, confirmPassword }
 * @returns {Promise} 后端返回的响应数据
 */
export function register(data) {
  return request.post('/user/add', data)
}

/**
 * 用户登录
 * @param {Object} data - { phone, password }
 * @returns {Promise} 登录成功后返回 token 和用户信息
 */
export function login(data) {
  return request.post('/user/login', data)
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
 * @param {Object} data - 要修改的字段
 */
export function updateUser(data) {
  return request.put('/user/update', data)
}

/**
 * 修改密码
 * @param {Object} data - { oldPassword, newPassword }
 */
export function updatePassword(data) {
  return request.put('/user/updatePwd', data)
}
