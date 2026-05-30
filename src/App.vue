<script setup>
import { Suspense } from 'vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
</script>

<template>
  <Suspense>
    <router-view />
    <template #fallback>
      <div style="display:flex;align-items:center;justify-content:center;height:100vh;color:#909399;font-size:16px;">
        加载中...
      </div>
    </template>
  </Suspense>
  <ConfirmDialog />
</template>

<style></style>
