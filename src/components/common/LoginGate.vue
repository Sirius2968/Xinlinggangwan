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

<style lang="scss" scoped>
.login-gate {
  @include flex-col-center;
  justify-content: center;
  min-height: 400px;
  text-align: center;
  padding: 80px 20px;

  h2 {
    font-size: 22px;
    color: $color-text-primary;
    margin-bottom: 8px;
  }

  p {
    color: $color-text-secondary;
    font-size: 15px;
    margin-bottom: 24px;
  }
}

.gate-icon {
  font-size: 56px;
  margin-bottom: 16px;
}
</style>
