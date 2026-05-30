<script setup>
import { useConfirm } from '@/composables/useConfirm'
import BaseDialog from './BaseDialog.vue'

const { visible, dialogMessage, dialogTitle, handleConfirm, handleCancel } = useConfirm()
</script>

<template>
  <BaseDialog
    :model-value="visible"
    :title="dialogTitle"
    width="420px"
    confirm-text="确定"
    cancel-text="取消"
    @confirm="handleConfirm"
    @cancel="handleCancel"
    @close="handleCancel"
  >
    <p style="text-align: center; font-size: 15px; color: #606266; line-height: 1.7;">
      {{ dialogMessage }}
    </p>
  </BaseDialog>
</template>
