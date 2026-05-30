<script setup>
import { useRouter } from 'vue-router'

defineProps({
  message: { type: String, default: '登录后即可使用完整功能' },
})

const router = useRouter()
</script>

<template>
  <div class="login-gate">
    <div class="gate-icon">&#x1f512;</div>
    <h2>请先登录</h2>
    <p>{{ message }}</p>
    <el-button type="primary" size="large" round @click="router.push('/login')">前往登录</el-button>
  </div>
</template>

<style scoped>
.login-gate {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  text-align: center;
  padding: 80px 20px;
}

.gate-icon {
  font-size: 56px;
  margin-bottom: 16px;
}

.login-gate h2 {
  font-size: 22px;
  color: #303133;
  margin-bottom: 8px;
}

.login-gate p {
  color: #909399;
  font-size: 15px;
  margin-bottom: 24px;
}
</style>
