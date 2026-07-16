<script setup>
import { Suspense } from 'vue'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
</script>

<template>
  <el-config-provider :locale="zhCn">
    <Suspense>
      <router-view />
      <template #fallback>
        <div style="display:flex;align-items:center;justify-content:center;height:100vh;color:#909399;font-size:16px;">
          加载中...
        </div>
      </template>
    </Suspense>
    <ConfirmDialog />
  </el-config-provider>
</template>

<style lang="scss"></style>
