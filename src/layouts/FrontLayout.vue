<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useUserStore } from '@/stores/user'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

const userStore = useUserStore()
const router = useRouter()

const mobileMenuOpen = ref(false)

function toggleMobileMenu() {
  mobileMenuOpen.value = !mobileMenuOpen.value
}

function closeMobileMenu() {
  mobileMenuOpen.value = false
}

function handleNavClick() {
  mobileMenuOpen.value = false
}

function handleLogout() {
  userStore.logout()
  ElMessage.success('已退出登录')
  router.push('/')
}

// 点击页面其他位置关闭移动端菜单
function onDocumentClick(e) {
  const menu = document.querySelector('.mobile-nav-dropdown')
  const btn = document.querySelector('.hamburger-btn')
  if (menu && !menu.contains(e.target) && btn && !btn.contains(e.target)) {
    mobileMenuOpen.value = false
  }
}

onMounted(() => document.addEventListener('click', onDocumentClick))
onBeforeUnmount(() => document.removeEventListener('click', onDocumentClick))
</script>

<template>
  <div class="front-layout">
    <!-- 顶部导航栏 -->
    <header class="front-header">
      <div class="header-container">
        <!-- 左侧：Logo + 导航 -->
        <div class="header-left">
          <router-link to="/" class="logo" @click="closeMobileMenu">
            <span class="logo-icon">🧠</span>
            <span class="logo-text">心灵港湾</span>
          </router-link>
          <!-- 桌面端导航 -->
          <nav class="header-nav">
            <router-link to="/">首页</router-link>
            <router-link to="/articles">心理知识</router-link>
            <router-link to="/article-share">心理知识分享</router-link>
            <router-link to="/counselors">AI咨询</router-link>
            <router-link to="/mental-health">记录心理健康</router-link>
          </nav>
        </div>

        <!-- 右侧：已登录显示用户信息，未登录显示登录按钮 -->
        <div class="header-right">
          <template v-if="userStore.isLoggedIn">
            <span class="user-phone">{{ userStore.userInfo?.account }}</span>
            <el-button text @click="handleLogout">退出</el-button>
          </template>
          <el-button v-else type="primary" round @click="$router.push('/login')">登录 / 注册</el-button>

          <!-- 移动端汉堡按钮 -->
          <button class="hamburger-btn" @click.stop="toggleMobileMenu">
            <span :class="{ open: mobileMenuOpen }"></span>
            <span :class="{ open: mobileMenuOpen }"></span>
            <span :class="{ open: mobileMenuOpen }"></span>
          </button>
        </div>
      </div>

      <!-- 移动端下拉菜单 -->
      <transition name="slide-down">
        <nav v-if="mobileMenuOpen" class="mobile-nav-dropdown" @click.stop>
          <router-link to="/" @click="handleNavClick">首页</router-link>
          <router-link to="/articles" @click="handleNavClick">心理知识</router-link>
          <router-link to="/article-share" @click="handleNavClick">心理知识分享</router-link>
          <router-link to="/counselors" @click="handleNavClick">AI咨询</router-link>
          <router-link to="/mental-health" @click="handleNavClick">记录心理健康</router-link>
        </nav>
      </transition>
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

<style lang="scss" scoped>
// ===== 整体布局 =====
.front-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: $color-bg-page;
  overflow-x: hidden;
}

// ===== 顶部导航 =====
.front-header {
  background: $color-white;
  box-shadow: $shadow-header;
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

// ---- 左侧 ----
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
  color: $color-text-dark;
}

.logo-icon { font-size: 28px; }

.logo-text {
  font-size: 20px;
  font-weight: 700;
  color: $color-text-title;
}

// ---- 桌面端导航 ----
.header-nav {
  display: flex;
  gap: 8px;

  a {
    padding: 8px 16px;
    color: $color-text-medium;
    text-decoration: none;
    font-size: 15px;
    border-radius: $radius-md;
    transition: all 0.2s;

    &:hover {
      color: $color-primary;
      background: $color-primary-light-bg;
    }

    &.router-link-exact-active {
      color: $color-primary;
      font-weight: 600;
    }
  }
}

// ---- 右侧 ----
.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.user-phone {
  color: $color-text-muted;
  font-size: 14px;
}

// ---- 移动端汉堡按钮 ----
.hamburger-btn {
  display: none;
  flex-direction: column;
  justify-content: center;
  gap: 5px;
  width: 36px;
  height: 36px;
  padding: 6px;
  border: none;
  border-radius: $radius-md;
  background: transparent;
  cursor: pointer;
  transition: background 0.15s;

  &:hover { background: $color-bg-hover-light; }

  span {
    display: block;
    width: 100%;
    height: 2px;
    background: $color-text-medium;
    border-radius: 1px;
    transition: transform 0.25s, opacity 0.25s;

    &.open:nth-child(1) { transform: translateY(7px) rotate(45deg); }
    &.open:nth-child(2) { opacity: 0; }
    &.open:nth-child(3) { transform: translateY(-7px) rotate(-45deg); }
  }
}

// ---- 移动端下拉菜单（绝对定位，不影响正文布局） ----
.mobile-nav-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  z-index: 99;
  display: flex;
  flex-direction: column;
  background: $color-white;
  border-top: 1px solid $color-border;
  box-shadow: $shadow-dropdown;
  padding: 8px;

  a {
    padding: 12px 20px;
    color: $color-text-medium;
    text-decoration: none;
    font-size: 15px;
    border-radius: $radius-md;
    transition: background 0.15s;

    &:hover {
      background: $color-bg-page;
      color: $color-primary;
    }

    &.router-link-exact-active {
      color: $color-primary;
      font-weight: 600;
      background: $color-primary-light-bg;
    }
  }
}

// 下拉动画（Vue Transition 组件驱动）
.slide-down-enter-active { transition: opacity 0.2s ease, transform 0.2s ease; }
.slide-down-leave-active { transition: opacity 0.15s ease, transform 0.15s ease; }

.slide-down-enter-from { opacity: 0; transform: translateY(-12px); }
.slide-down-leave-to   { opacity: 0; transform: translateY(-8px); }

// ===== 内容区 =====
.front-main {
  flex: 1;
  max-width: 1200px;
  width: 100%;
  margin: 0 auto;
  padding: 24px;
}

// ===== 页脚 =====
.front-footer {
  background: $color-white;
  text-align: center;
  padding: 20px;
  color: $color-text-light;
  font-size: 14px;
  border-top: 1px solid $color-border;
}

// ===== 响应式 =====
@media (max-width: 768px) {
  .header-nav { display: none; }
  .hamburger-btn { display: flex; }
  .header-container { padding: 0 16px; }
  .header-left { gap: 16px; }
}
</style>
