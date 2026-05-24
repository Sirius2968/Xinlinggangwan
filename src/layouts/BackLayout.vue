<script setup></script>

<template>
  <div class="back-layout">
    <aside class="back-sidebar">
      <h2>后台管理</h2>
      <nav>
        <router-link to="/back">数据概览</router-link>
        <router-link to="/back/articles">文章管理</router-link>
        <router-link to="/back/users">用户管理</router-link>
      </nav>
    </aside>
    <div class="back-right">
      <header class="back-topbar">
        <span>管理员</span>
      </header>
      <main class="back-main">
        <router-view />
      </main>
    </div>
  </div>
</template>

<style scoped>
.back-layout {
  display: flex;
  min-height: 100vh;
}

.back-sidebar {
  width: 220px;
  background: #304156;
  color: #fff;
  padding: 20px 0;
  flex-shrink: 0;
}

.back-sidebar h2 {
  text-align: center;
  margin-bottom: 24px;
  font-size: 18px;
}

.back-sidebar nav {
  display: flex;
  flex-direction: column;
}

.back-sidebar a {
  color: #bfcbd9;
  text-decoration: none;
  padding: 12px 24px;
  font-size: 14px;
}

.back-sidebar a:hover {
  color: #fff;
  background: #263445;
}

.back-sidebar a.router-link-exact-active {
  color: #fff;
  background: #409eff;
}

.back-right {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.back-topbar {
  height: 50px;
  background: #fff;
  border-bottom: 1px solid #e6e6e6;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding: 0 24px;
}

.back-main {
  flex: 1;
  background: #f0f2f5;
  padding: 24px;
}
</style>
