<script setup>
defineProps({
  modelValue: { type: Boolean, default: false },
  title: { type: String, default: '' },
  width: { type: String, default: '480px' },
  showFooter: { type: Boolean, default: true },
  confirmText: { type: String, default: '确定' },
  cancelText: { type: String, default: '取消' },
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'confirm', 'cancel', 'close'])

function handleClose() {
  emit('update:modelValue', false)
  emit('close')
}

function handleConfirm() { emit('confirm') }
function handleCancel() {
  emit('update:modelValue', false)
  emit('cancel')
}
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    :title="title"
    :width="width"
    :close-on-click-modal="false"
    destroy-on-close
    center
    @close="handleClose"
  >
    <slot />
    <template v-if="showFooter" #footer>
      <el-button @click="handleCancel">{{ cancelText }}</el-button>
      <el-button type="primary" :loading="loading" @click="handleConfirm">
        {{ confirmText }}
      </el-button>
    </template>
  </el-dialog>
</template>
