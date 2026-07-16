<script setup>
defineProps({
  modelValue: { type: String, default: '' },
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'send', 'stop'])

function onKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    emit('send')
  }
}
</script>

<template>
  <div class="chat-input">
    <el-input
      :model-value="modelValue"
      type="textarea"
      :rows="2"
      placeholder="请输入你的问题..."
      resize="none"
      @update:model-value="emit('update:modelValue', $event)"
      @keydown.enter.exact.prevent="emit('send')"
    />
    <button
      class="send-btn"
      :class="{ active: !!modelValue.trim(), streaming: loading }"
      :disabled="!modelValue.trim() && !loading"
      @click="loading ? emit('stop') : emit('send')"
    >
      <svg v-if="!loading" class="send-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <line x1="12" y1="19" x2="12" y2="5" />
        <polyline points="5 12 12 5 19 12" />
      </svg>
      <svg v-else class="stop-icon" width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
        <rect x="3" y="3" width="18" height="18" rx="3" />
      </svg>
    </button>
  </div>
</template>

<style lang="scss" scoped>
.chat-input {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 24px;
  border-top: 1px solid $color-border;
  background: $color-white;
}

.send-btn {
  width: 36px; height: 36px; flex-shrink: 0;
  @include flex-center;
  border: none; border-radius: $radius-lg;
  background: $color-bg-input-disabled;
  color: $color-white;
  cursor: pointer;
  transition: background 0.2s, transform 0.15s;

  &.active { background: $color-primary; &:hover { background: $color-primary-hover; } }
  &.streaming { background: $color-warning; &:hover { background: $color-warning-hover; } }
  &:disabled { cursor: not-allowed; opacity: 0.5; }

  .stop-icon { color: $color-white; }
}
</style>
