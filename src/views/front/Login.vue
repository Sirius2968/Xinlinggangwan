<script setup>
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { login as loginApi, register as registerApi } from '@/api/user'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

// ============================================================
// 状态定义
// ============================================================

const isLogin = ref(true)

const form = reactive({
  account: '',     // 登录：用户名/邮箱 | 注册：用户名
  password: '',
  confirmPassword: '',
  sex: '',
  email: '',
})

const errors = reactive({
  account: '',
  password: '',
  confirmPassword: '',
  sex: '',
  email: '',
})

// ============================================================
// 校验规则
// ============================================================

const EMAIL_REG = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

// ============================================================
// 校验函数
// ============================================================

// 用户名校验：非空即可
function validateAccount() {
  if (!form.account) { errors.account = ''; return }
  errors.account = form.account.trim().length >= 1 ? '' : '请输入用户名'
}

function validatePassword() {
  if (!form.password) { errors.password = ''; return }
  errors.password = form.password.length >= 6 ? '' : '密码长度不能少于6位'
}

function validateConfirmPassword() {
  if (!form.confirmPassword) { errors.confirmPassword = ''; return }
  errors.confirmPassword = form.confirmPassword === form.password ? '' : '两次输入的密码不一致'
}

function validateSex() {
  if (!form.sex) { errors.sex = ''; return }
  errors.sex = ''
}

function validateEmail() {
  if (!form.email) { errors.email = ''; return }
  errors.email = EMAIL_REG.test(form.email) ? '' : '请输入正确的邮箱格式'
}

// ============================================================
// 业务逻辑
// ============================================================

function toggleMode() {
  isLogin.value = !isLogin.value
  // 重置所有字段
  Object.keys(form).forEach((k) => (form[k] = ''))
  Object.keys(errors).forEach((k) => (errors[k] = ''))
}

/** 校验注册所有字段，有错返回 true */
function hasRegisterError() {
  validateAccount()
  validatePassword()
  validateConfirmPassword()
  validateSex()
  validateEmail()
  return Object.values(errors).some((v) => v)
}

async function handleSubmit() {
  if (!isLogin.value) {
    // ==================== 注册 ====================
    if (hasRegisterError()) return
    // 检查必填项非空
    const required = ['account', 'password', 'confirmPassword', 'sex', 'email']
    if (required.some((k) => !form[k])) {
      ElMessage.warning('请完善所有信息')
      return
    }

    try {
      const res = await registerApi({
        username: form.account,
        password: form.password,
        confirmPassword: form.confirmPassword,
        sex: form.sex,
        email: form.email.trim(),
      })
      console.log('注册成功，后端返回:', JSON.stringify(res, null, 2))
      ElMessage.success('注册成功，请登录')
      toggleMode()
    } catch (err) {
      console.error('注册失败，后端返回:', err.response?.data || err.message)
    }
  } else {
    // ==================== 登录 ====================
    if (!form.account || !form.password) {
      ElMessage.warning('请输入用户名/邮箱和密码')
      return
    }

    try {
      const res = await loginApi({ username: form.account, password: form.password })
      // 调试：打印后端实际返回的数据结构
      console.log('登录成功，后端返回:', JSON.stringify(res, null, 2))

      // 后端返回格式：{ code, msg, data: { token, ... } }
      const token = res.data?.token || res.token
      const info = res.data || res

      userStore.setLogin({ token, userInfo: { ...info, account: form.account } })
      ElMessage.success('登录成功')
      const redirect = route.query.redirect || '/'
      router.push(redirect)
    } catch (err) {
      console.error('登录失败，后端返回:', err.response?.data || err.message)
    }
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-card" :class="{ wide: !isLogin }">
      <h2>{{ isLogin ? '登录' : '注册' }}</h2>

      <el-form :model="form" label-position="top" @submit.prevent="handleSubmit">
        <!-- 登录：用户名/邮箱 | 注册：用户名 -->
        <el-form-item :label="isLogin ? '用户名 / 邮箱' : '用户名'">
          <el-input v-model="form.account" :placeholder="isLogin ? '请输入用户名或邮箱' : '请输入用户名'" @blur="validateAccount" />
          <span v-if="errors.account" class="field-error">{{ errors.account }}</span>
        </el-form-item>

        <!-- 密码 -->
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" placeholder="请输入密码" show-password @blur="validatePassword" />
          <span v-if="errors.password" class="field-error">{{ errors.password }}</span>
        </el-form-item>

        <!-- 确认密码（仅注册） -->
        <el-form-item v-if="!isLogin" label="确认密码">
          <el-input v-model="form.confirmPassword" type="password" placeholder="请再次输入密码" show-password @blur="validateConfirmPassword" />
          <span v-if="errors.confirmPassword" class="field-error">{{ errors.confirmPassword }}</span>
        </el-form-item>

        <!-- 以下仅注册时显示 -->
        <template v-if="!isLogin">
          <!-- 性别 -->
          <el-form-item label="性别">
            <el-radio-group v-model="form.sex" @change="validateSex">
              <el-radio value="男">男</el-radio>
              <el-radio value="女">女</el-radio>
            </el-radio-group>
            <span v-if="errors.sex" class="field-error">{{ errors.sex }}</span>
          </el-form-item>

          <!-- 邮箱 -->
          <el-form-item label="邮箱">
            <el-input v-model="form.email" placeholder="请输入邮箱" maxlength="50" @blur="validateEmail" />
            <span v-if="errors.email" class="field-error">{{ errors.email }}</span>
          </el-form-item>

        </template>

        <!-- 提交 -->
        <el-form-item>
          <el-button type="primary" class="submit-btn" @click="handleSubmit">
            {{ isLogin ? '登录' : '注册' }}
          </el-button>
        </el-form-item>
      </el-form>

      <p class="toggle-text">
        {{ isLogin ? '还没有账号？' : '已有账号？' }}
        <a href="javascript:void(0)" @click="toggleMode">{{ isLogin ? '立即注册' : '去登录' }}</a>
      </p>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: calc(100vh - 180px);
}

.login-card {
  width: 400px;
  padding: 40px 36px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 16px rgba(0, 0, 0, 0.08);
}

/* 注册模式卡片加宽一点，容纳更多字段 */
.login-card.wide {
  width: 480px;
}

.login-card h2 {
  text-align: center;
  margin-bottom: 28px;
  color: #303133;
}

.submit-btn {
  width: 100%;
}

.toggle-text {
  text-align: center;
  font-size: 14px;
  color: #999;
}

.toggle-text a {
  color: #409eff;
  text-decoration: none;
}

.field-error {
  display: block;
  font-size: 12px;
  color: #f56c6c;
  margin-top: 2px;
  line-height: 1.2;
}
</style>
