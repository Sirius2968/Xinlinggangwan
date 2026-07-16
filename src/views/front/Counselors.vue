<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useUserStore } from '@/stores/user'
import { useChatConversations } from '@/components/chat/useChatConversations'
import { useChatStream } from '@/components/chat/useChatStream'
import LoginGate from '@/components/common/LoginGate.vue'
import ChatSidebar from '@/components/chat/ChatSidebar.vue'
import ChatMessages from '@/components/chat/ChatMessages.vue'
import ChatInputBar from '@/components/chat/ChatInputBar.vue'

const userStore = useUserStore()

// ---- 对话管理 ----
const {
  conversations, activeId, openMenuId, chatStates, chatAbortFns, starterPrompts,
  getChatState, isBgGenerating, toggleMenu, closeMenu,
  loadChatList, newChat, switchChat, handleDeleteChat,
  handleRenameChat, handleTogglePin, handleClearChat,
  loadDraftFromLocal,
} = useChatConversations()

// ---- 消息 / SSE 流式 ----
const {
  messages, inputText, loading, hoveredMsgIndex,
  scrollToBottomFn, displayMode,
  reconnecting, reconnectStatus, giveUpInfo, retryLastMessage,
  handleSend, stopGeneration, handleRegenerate, handleContinue,
  copyMarkdown, handleStarterPrompt,
  submitFormCard,
} = useChatStream({
  conversations, activeId, chatStates, chatAbortFns, getChatState,
  saveDraftToLocal: (msgs) => {
    const conv = conversations.value.find((c) => c.id === activeId.value)
    if (!conv || msgs.length === 0) return
    localStorage.setItem(`chat_draft_${conv.chatId || conv.id}`, JSON.stringify(msgs))
  },
  clearDraft: () => {
    const conv = conversations.value.find((c) => c.id === activeId.value)
    if (!conv) return
    localStorage.removeItem(`chat_draft_${conv.chatId || conv.id}`)
  },
  loadDraftFromLocal,
})

const chatMessagesRef = ref(null)

// ---- 对话切换 ----
async function onSelectChat(conv) {
  const result = await switchChat(conv)
  if (result && result.messages) {
    messages.value = result.messages
    loading.value = result.loading || false
  }
}

async function onNewChat() {
  const result = await newChat()
  if (result) {
    messages.value = result.messages || []
    loading.value = false
  }
  inputText.value = ''
}

async function onDeleteChat(conv) {
  const result = await handleDeleteChat(conv)
  if (result && result.messages) {
    messages.value = result.messages
    loading.value = result.loading || false
  }
}

async function onClearAll() {
  const result = await handleClearChat()
  if (result) {
    messages.value = result.messages || []
    loading.value = result.loading || false
  }
}

// ---- 生命周期 ----
onMounted(async () => {
  document.addEventListener('click', closeMenu)
  scrollToBottomFn.value = () => chatMessagesRef.value?.scrollToBottom()
  if (userStore.isLoggedIn) {
    const result = await loadChatList()
    if (result && result.messages) {
      messages.value = result.messages
      loading.value = result.loading || false
    }
  }
})

onBeforeUnmount(() => {
  document.removeEventListener('click', closeMenu)
})
</script>

<template>
  <LoginGate v-if="!userStore.isLoggedIn" message="登录后即可使用 AI 心理咨询服务" />

  <div v-else class="ai-chat">
    <!-- 左侧边栏 -->
    <ChatSidebar
      :conversations="conversations"
      :activeId="activeId"
      :openMenuId="openMenuId"
      :isBgGenerating="isBgGenerating"
      @select-chat="onSelectChat"
      @new-chat="onNewChat"
      @delete-chat="onDeleteChat"
      @rename-chat="handleRenameChat"
      @toggle-pin="handleTogglePin"
      @toggle-menu="toggleMenu"
      @clear-all="onClearAll"
    />

    <!-- 右侧聊天区 -->
    <div class="chat-main">
      <ChatMessages
        ref="chatMessagesRef"
        :displayMode="displayMode"
        :messages="messages"
        :loading="loading"
        :reconnecting="reconnecting"
        :reconnectStatus="reconnectStatus"
        :giveUpInfo="giveUpInfo"
        :starterPrompts="starterPrompts"
        :hoveredMsgIndex="hoveredMsgIndex"
        @starter-click="handleStarterPrompt"
        @copy-markdown="copyMarkdown"
        @regenerate="handleRegenerate"
        @continue-generation="handleContinue"
        @submit-form="submitFormCard"
        @retry-last-message="retryLastMessage"
        @hover-message="(idx) => hoveredMsgIndex = idx"
      />
      <ChatInputBar
        v-model="inputText"
        :loading="loading"
        @send="handleSend"
        @stop="stopGeneration"
      />
    </div>
  </div>
</template>

<style lang="scss" scoped>
.ai-chat {
  display: flex;
  height: calc(100vh - 180px);
  min-height: 500px;
  background: $color-white;
  border-radius: $radius-xl;
  box-shadow: $shadow-lg;
  overflow: hidden;
}

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

// ===== 响应式：跨组件布局协调 =====
@media (max-width: $bp-desktop-small) {
  .ai-chat { height: calc(100vh - 160px); min-height: 400px; }

  :deep(.chat-sidebar) { width: $sidebar-width-sm; }
  :deep(.chat-messages) { padding: 16px; }
  :deep(.chat-input) { padding: 10px 16px; }
  :deep(.message-row) { max-width: 88%; }
  :deep(.form-card) { max-width: 85%; margin-left: 24px; }
}

@media (max-width: $bp-mobile) {
  :deep(.chat-sidebar) { width: $sidebar-width-xs; }
  :deep(.conv-item) { padding: 10px 8px; }
  :deep(.conv-title) { font-size: 12px; }
  :deep(.new-chat-btn) { margin: 10px; font-size: 13px; }
  :deep(.chat-messages) { padding: 12px; }
  :deep(.chat-input) { padding: 8px 12px; }
  :deep(.message-row) { max-width: 92%; }
  :deep(.form-card) { max-width: 92%; margin-left: 8px; }
  :deep(.sidebar-footer) { padding: 8px 10px; }
}
</style>
