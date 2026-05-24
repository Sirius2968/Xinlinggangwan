<script setup>
import { useUserStore } from '@/stores/user'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

const userStore = useUserStore()
const router = useRouter()

function handleLogout() {
  userStore.logout()
  ElMessage.success('已退出登录')
  router.push('/')
}
</script>

<template>
  <div class="front-layout">
    <!-- 顶部导航栏 -->
    <header class="front-header">
      <div class="header-container">
        <!-- 左侧：Logo + 导航 -->
        <div class="header-left">
          <router-link to="/" class="logo">
            <span class="logo-icon">🧠</span>
            <span class="logo-text">心灵港湾</span>
          </router-link>
          <nav class="header-nav">
            <router-link to="/">首页</router-link>
            <router-link to="/articles">心理知识</router-link>
            <router-link to="/counselors">AI咨询</router-link>
            <router-link to="/about">关于我们</router-link>
          </nav>
        </div>
        <!-- 右侧：已登录显示用户信息，未登录显示登录按钮 -->
        <div class="header-right">
          <template v-if="userStore.isLoggedIn">
            <span class="user-phone">{{ userStore.userInfo?.account }}</span>
            <el-button text @click="handleLogout">退出</el-button>
          </template>
          <el-button v-else type="primary" round @click="$router.push('/login')">登录 / 注册</el-button>
        </div>
      </div>
    </header>

    <!-- 内容区 -->
    <main class="front-main">
      <router-view />
    </main>

    <!-- 页脚 -->
    <footer class="front-footer">
      <p>&copy; 2026 心灵港湾 · 心理健康平台</p>
    </footer>
  </div>
</template>

<style scoped>
/* ===== 整体布局 ===== */
.front-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f5f7fa;
}

/* ===== 顶部导航 ===== */
.front-header {
  background: #fff;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-container {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 60px;
  padding: 0 24px;
}

/* ---- 左侧 ---- */
.header-left {
  display: flex;
  align-items: center;
  gap: 40px;
}

.logo {
  display: flex;
  align-items: center;
  gap: 8px;
  text-decoration: none;
  color: #333;
}

.logo-icon {
  font-size: 28px;
}

.logo-text {
  font-size: 20px;
  font-weight: 700;
  color: #2c3e50;
}

.header-nav {
  display: flex;
  gap: 8px;
}

.header-nav a {
  padding: 8px 16px;
  color: #555;
  text-decoration: none;
  font-size: 15px;
  border-radius: 6px;
  transition: all 0.2s;
}

.header-nav a:hover {
  color: #409eff;
  background: #ecf5ff;
}

.header-nav a.router-link-exact-active {
  color: #409eff;
  font-weight: 600;
}

/* ---- 右侧 ---- */
.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.user-phone {
  color: #666;
  font-size: 14px;
}

/* ===== 内容区 ===== */
.front-main {
  flex: 1;
  max-width: 1200px;
  width: 100%;
  margin: 0 auto;
  padding: 24px;
}

/* ===== 页脚 ===== */
.front-footer {
  background: #fff;
  text-align: center;
  padding: 20px;
  color: #999;
  font-size: 14px;
  border-top: 1px solid #ebeef5;
}
</style>
