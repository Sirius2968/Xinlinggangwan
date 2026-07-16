<script setup>
defineProps({
  conversations: { type: Array, default: () => [] },
  activeId: { type: [String, null], default: null },
  openMenuId: { type: [String, null], default: null },
  isBgGenerating: { type: Function, default: () => false },
})

const emit = defineEmits([
  'select-chat', 'new-chat', 'delete-chat', 'rename-chat',
  'toggle-pin', 'toggle-menu', 'clear-all',
])
</script>

<template>
  <aside class="chat-sidebar">
    <el-button type="primary" class="new-chat-btn" @click="emit('new-chat')">
      + 新对话
    </el-button>

    <div class="conv-list">
      <div
        v-for="conv in conversations"
        :key="conv.id"
        class="conv-item"
        :class="{ active: conv.id === activeId, pinned: conv.isPinned }"
        @click="emit('select-chat', conv)"
      >
        <span v-if="conv.isPinned" class="pin-indicator" title="已置顶">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="M16 12V4h1V2H7v2h1v8l-2 2v2h5.2v6h1.6v-6H18v-2l-2-2z"/></svg>
        </span>
        <span v-if="isBgGenerating(conv)" class="bg-loading-dot" title="后台生成中"></span>
        <span class="conv-title">{{ conv.title }}</span>
        <span class="conv-menu-btn" @click.stop="emit('toggle-menu', conv.id)">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
            <circle cx="5" cy="12" r="2" />
            <circle cx="12" cy="12" r="2" />
            <circle cx="19" cy="12" r="2" />
          </svg>
        </span>
        <div v-if="openMenuId === conv.id" class="conv-menu-dropdown" @click.stop>
          <div class="menu-item" @click="emit('toggle-pin', conv)">{{ conv.isPinned ? '取消置顶' : '置顶' }}</div>
          <div class="menu-item" @click="emit('rename-chat', conv)">重命名</div>
          <div class="menu-item danger" @click="emit('delete-chat', conv)">删除对话</div>
        </div>
      </div>
    </div>

    <div class="sidebar-footer">
      <el-button type="danger" plain @click="emit('clear-all')">清空对话</el-button>
    </div>
  </aside>
</template>

<style lang="scss" scoped>
.chat-sidebar {
  width: $sidebar-width;
  background: $color-bg-sidebar;
  border-right: 1px solid $color-border;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  transition: width 0.25s ease;
}

.new-chat-btn { margin: 16px; }

.conv-list {
  flex: 1;
  @include scrollable-y;
  padding: 0 8px;
}

.conv-item {
  display: flex; align-items: center;
  padding: 12px 16px; border-radius: $radius-lg;
  cursor: pointer; margin-bottom: 4px;
  position: relative;
  transition: background 0.2s;

  &:hover {
    background: $color-bg-hover;
    .conv-menu-btn { opacity: 1; }
  }

  &.active { background: $color-primary-bg; }

  &.pinned {
    background: $color-bg-pinned;
    &:hover { background: $color-bg-pinned-hover; }
    &.active { background: $color-primary-dark-bg; }
  }
}

.pin-indicator {
  flex-shrink: 0; display: flex; align-items: center;
  color: $color-text-secondary; margin-right: 4px;
}

.bg-loading-dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: $color-primary; flex-shrink: 0; margin-right: 6px;
  animation: pulse-dot 1.5s infinite ease-in-out;
}

@keyframes pulse-dot {
  0%, 100% { opacity: 0.3; transform: scale(0.8); }
  50% { opacity: 1; transform: scale(1); }
}

.conv-title {
  font-size: $font-size-base; color: $color-text-dark;
  flex: 1; min-width: 0;
  @include text-ellipsis;
}

.conv-menu-btn {
  flex-shrink: 0; width: 28px; height: 28px;
  @include flex-center;
  border-radius: $radius-md; color: $color-text-light;
  cursor: pointer; opacity: 0;
  transition: opacity 0.15s, background 0.15s; margin-left: 4px;

  &:hover { background: #ddd; color: $color-text-medium; }
}

.conv-menu-dropdown {
  position: absolute; top: 100%; right: 8px; z-index: 100;
  background: $color-white; border-radius: $radius-lg;
  box-shadow: $shadow-dropdown; padding: 4px; min-width: 120px;
}

.menu-item {
  padding: 8px 12px; font-size: $font-size-base; color: $color-text-dark;
  cursor: pointer; border-radius: $radius-sm; transition: background 0.15s;

  &:hover { background: $color-bg-hover-light; }
  &.danger { color: $color-danger; &:hover { background: $color-danger-bg; } }
}

.sidebar-footer {
  padding: 12px 16px;
  border-top: 1px solid $color-border;
  text-align: center;
}
</style>
