<script setup></script>

<template>
  <div class="dashboard">
    <h1>数据概览</h1>
    <div class="stats">
      <div class="card">文章总数：0</div>
      <div class="card">咨询师数：0</div>
      <div class="card">用户数：0</div>
    </div>
  </div>
</template>

<style scoped>
.stats {
  display: flex;
  gap: 16px;
  margin-top: 24px;
}

.card {
  background: #fff;
  padding: 24px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  flex: 1;
  text-align: center;
}
</style>
