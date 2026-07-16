<script setup>
import { ref } from 'vue'
import { getBubbleHtml } from './markdown'
import MentalHealthFormCard from './MentalHealthFormCard.vue'

const props = defineProps({
  displayMode: { type: String, default: 'empty' },
  messages: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  reconnecting: { type: Boolean, default: false },
  reconnectStatus: { type: Object, default: null },
  giveUpInfo: { type: Object, default: null },
  starterPrompts: { type: Array, default: () => [] },
  hoveredMsgIndex: { type: Number, default: -1 },
})

const emit = defineEmits([
  'starter-click', 'copy-markdown', 'regenerate', 'continue-generation',
  'submit-form', 'hover-message', 'retry-last-message',
])

const chatArea = ref(null)

function scrollToBottom() {
  if (chatArea.value) {
    chatArea.value.scrollTop = chatArea.value.scrollHeight
  }
}

function onHover(index) {
  emit('hover-message', index)
}

function onLeave() {
  emit('hover-message', -1)
}

function msgHtml(msg, index) {
  const lastIdx = props.messages.length - 1
  return getBubbleHtml(msg, index, props.loading, lastIdx)
}

defineExpose({ scrollToBottom })
</script>

<template>
  <!-- 没有对话或未选中：引导创建 -->
  <div v-if="displayMode === 'empty'" class="chat-empty">
    <span class="empty-emoji">💬</span>
    <p>快来对话吧</p>
  </div>

  <!-- 选中了空对话：初始提示词 + 起始对话引导 -->
  <div v-else-if="displayMode === 'prompt'" class="chat-empty">
    <span class="empty-emoji">💭</span>
    <p>如果有心理上的问题 可以向我倾诉哦</p>
    <div class="starter-prompts">
      <button
        v-for="(prompt, idx) in starterPrompts"
        :key="idx"
        class="starter-btn"
        @click="emit('starter-click', prompt)"
      >{{ prompt }}</button>
    </div>
  </div>

  <!-- 消息列表 -->
  <div v-else ref="chatArea" class="chat-messages">
    <template v-for="(msg, i) in messages" :key="i">
      <!-- 心理健康表单卡片 -->
      <MentalHealthFormCard
        v-if="msg.role === 'form'"
        :msg="msg"
        @submit="emit('submit-form', $event)"
      />

      <!-- 普通消息 -->
      <div
        v-else
        class="message-row"
        :class="msg.role === 'user' ? 'msg-user' : 'msg-ai'"
        @mouseenter="msg.role === 'assistant' && msg.content ? onHover(i) : null"
        @mouseleave="onLeave"
      >
        <div class="msg-avatar">
          {{ msg.role === 'user' ? '👤' : '🤖' }}
        </div>
        <div class="msg-body">
          <div
            v-if="msg.content"
            class="msg-bubble"
            :class="{
              typing: msg.role === 'assistant' && !msg.content,
              streaming: msg.role === 'assistant' && loading && i === messages.length - 1,
            }"
            v-html="msgHtml(msg, i)"
          ></div>
          <div v-else class="msg-bubble typing">
            <span class="dot"></span><span class="dot"></span><span class="dot"></span>
          </div>
          <div
            v-if="msg.role === 'assistant'"
            class="msg-actions"
            :class="{ visible: msg.content && hoveredMsgIndex === i && !loading }"
          >
            <button class="msg-action-btn" title="复制 Markdown" @click="emit('copy-markdown', msg)">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2" /><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
              </svg>
              <span>复制</span>
            </button>
            <button class="msg-action-btn" title="重新生成" @click="emit('regenerate', i)">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="23 4 23 10 17 10" /><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
              </svg>
              <span>重新生成</span>
            </button>
            <button
              v-if="msg.interrupted"
              class="msg-action-btn continue-btn"
              title="继续生成"
              @click="emit('continue-generation', i)"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polygon points="5 3 19 12 5 21 5 3" />
              </svg>
              <span>继续生成</span>
            </button>
          </div>
          <span class="msg-time">{{ msg.time }}</span>
        </div>
      </div>
    </template>

    <!-- 🔄 重连提示条 -->
    <div v-if="reconnecting && reconnectStatus" class="reconnect-banner reconnect-busy">
      <svg class="reconnect-spinner" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10" stroke-opacity="0.3" />
        <path d="M12 2a10 10 0 0 1 10 10" stroke-linecap="round" />
      </svg>
      <span>正在重新连接 ({{ reconnectStatus.attempt }}/{{ reconnectStatus.maxRetries }})...</span>
    </div>

    <!-- ❌ 放弃重连提示条 -->
    <div v-if="giveUpInfo" class="reconnect-banner reconnect-fail">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="10" /><line x1="15" y1="9" x2="9" y2="15" /><line x1="9" y1="9" x2="15" y2="15" />
      </svg>
      <span>网络不稳定，消息发送失败</span>
      <button class="reconnect-retry-btn" @click="emit('retry-last-message')">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="23 4 23 10 17 10" /><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
        </svg>
        点击重试
      </button>
    </div>
  </div>
</template>

<style lang="scss" scoped>
// ---- 空状态 ----
.chat-empty {
  flex: 1;
  @include flex-col-center;
  justify-content: center;
  padding: 40px; text-align: center;
}

.empty-emoji { font-size: 48px; margin-bottom: 16px; }

.chat-empty p { color: $color-text-secondary; font-size: 15px; margin-bottom: 20px; }

.starter-prompts {
  display: flex; flex-wrap: wrap; justify-content: center; gap: 10px; max-width: 480px;
}

.starter-btn {
  padding: 8px 18px; background: $color-white; border: 1px solid $color-border-warm;
  border-radius: $radius-round; color: #6b5b5b; font-size: $font-size-base;
  cursor: pointer; transition: all 0.2s ease; white-space: nowrap;

  &:hover {
    background: #f8f0ed; border-color: $color-border-warm-hover;
    color: #4a3b3b; transform: translateY(-1px); box-shadow: $shadow-warm;
  }
}

// ---- 消息列表 ----
.chat-messages {
  flex: 1;
  @include scrollable-y;
  padding: 20px 24px;
  background: $color-bg-chat;
  transition: padding 0.25s ease;
}

.message-row {
  display: flex; gap: 12px; margin-bottom: 32px; max-width: 80%;
  transition: max-width 0.25s ease;

  &.msg-user { flex-direction: row-reverse; margin-left: auto; }
  &.msg-ai { margin-right: auto; }
}

.msg-avatar {
  width: 36px; height: 36px; border-radius: $radius-circle;
  background: $color-white;
  @include flex-center;
  font-size: 20px; flex-shrink: 0;
  box-shadow: $shadow-sm;
}

.msg-body {
  display: flex; flex-direction: column; position: relative;
  .msg-user & { align-items: flex-end; }
}

.msg-bubble {
  @include msg-bubble-base;
  transform: translateZ(0);   // 提升到独立合成层，避免内容更新时触发大面积重绘
  contain: layout style;       // 隔离布局计算，防止气泡内容变化影响外部

  .msg-user & { background: $color-primary; color: $color-white; border-bottom-right-radius: $radius-sm; }
  .msg-ai & {
    background: $color-white; color: $color-text-primary;
    border-bottom-left-radius: $radius-sm; box-shadow: $shadow-sm;
  }

  .msg-ai & { @include md-content; }

  // 流式生成中：加强布局隔离 + 闪烁光标
  &.streaming {
    contain: layout style paint;

    &::after {
      content: '|';
      display: inline;
      animation: blink-cursor 1s step-end infinite;
      color: $color-primary;
      font-weight: 700;
      margin-left: 1px;
    }
  }

  // 未完成缓冲区的纯文本预览（v-html 动态内容，需用 :deep 穿透 scoped）
  &:deep(.streaming-pending) {
    opacity: 0.75;
  }
}

@keyframes blink-cursor {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

.msg-time { font-size: $font-size-xs; color: $color-text-placeholder; margin-top: 4px; }

// ---- 打字动画 ----
.typing {
  display: flex; gap: 4px; align-items: center; padding: 16px 20px !important;

  .dot {
    width: 8px; height: 8px; background: $color-text-placeholder; border-radius: 50%;
    animation: bounce 1.4s infinite ease-in-out both;
    &:nth-child(1) { animation-delay: -0.32s; }
    &:nth-child(2) { animation-delay: -0.16s; }
  }
}

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}

// ---- AI 消息 hover 操作按钮（绝对定位，不占布局空间） ----
.msg-actions {
  position: absolute; bottom: -26px; left: 0;
  display: flex; gap: 4px;
  opacity: 0; visibility: hidden;
  transition: opacity 0.15s ease, visibility 0.15s ease;
  z-index: 5; pointer-events: none;

  &.visible { opacity: 1; visibility: visible; pointer-events: auto; }
}

.msg-action-btn {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 4px 10px; border: 1px solid $color-border-light; border-radius: $radius-md;
  background: $color-white; color: $color-text-regular;
  font-size: 12px; cursor: pointer; transition: all 0.15s;

  &:hover { background: #f0f2f5; border-color: #c0c4cc; color: $color-text-primary; }
}

// ---- 重连提示条 ----
.reconnect-banner {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 10px 16px;
  margin-top: 8px;
  border-radius: 10px;
  font-size: 13px;
  animation: slideUp 0.3s ease;

  &.reconnect-busy {
    background: #fef7e0;
    border: 1px solid #f5dab1;
    color: #b88230;
  }

  &.reconnect-fail {
    background: #fef0f0;
    border: 1px solid #fbc4c4;
    color: #c45656;
  }
}

.reconnect-spinner {
  animation: spin 0.9s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@keyframes slideUp {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.reconnect-retry-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 12px;
  margin-left: 4px;
  border: 1px solid #e6a23c;
  border-radius: 6px;
  background: #e6a23c;
  color: #fff;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;

  &:hover {
    background: #d4922a;
    border-color: #d4922a;
  }
}
</style>
