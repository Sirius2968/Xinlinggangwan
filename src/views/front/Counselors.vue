<script setup>
import { ref, nextTick, onMounted } from 'vue'
import { createChat, sendMessageStream, getChatHistory } from '@/api/chat'

// ============================================================
// 对话列表（左侧边栏）
// ============================================================
const conversations = ref([])
const activeId = ref(null)

async function newChat() {
  const localId = Date.now()
  try {
    const res = await createChat()
    const chatId = res.chat_id || res.data?.chat_id
    conversations.value.unshift({ id: localId, chatId, title: '新对话' })
    activeId.value = localId
    messages.value = []
    inputText.value = ''
  } catch (err) {
    console.error('createChat 失败:', err)
    conversations.value.unshift({ id: localId, chatId: null, title: '新对话(离线)' })
    activeId.value = localId
    messages.value = []
    inputText.value = ''
  }
}

// ============================================================
// 消息列表（右侧主体）
// ============================================================
const messages = ref([])
const inputText = ref('')
const loading = ref(false)
const chatArea = ref(null)

/**
 * 添加一条消息到列表
 */
function addMessage(role, content) {
  messages.value.push({
    role,
    content,
    time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
  })
}

/**
 * 切换对话时加载历史消息
 */
async function switchChat(conv) {
  activeId.value = conv.id
  if (conv.chatId) {
    try {
      const res = await getChatHistory(conv.chatId)
      const list = res.messages || res.data?.messages || res.data || []
      messages.value = (Array.isArray(list) ? list : []).map((m) => ({
        role: m.role,
        content: m.content,
        time: m.time || '',
      }))
    } catch {
      messages.value = []
    }
  } else {
    messages.value = []
  }
}

/** 清空当前对话的消息 */
function clearChat() {
  messages.value = []
}

/**
 * 发送消息（SSE 流式）
 */
function handleSend() {
  const text = inputText.value.trim()
  if (!text || loading.value) return

  const conv = conversations.value.find((c) => c.id === activeId.value)
  if (!conv || !conv.chatId) {
    addMessage('assistant', '会话未创建成功，请点击"新对话"重试。')
    return
  }

  // 用户消息
  addMessage('user', text)
  inputText.value = ''
  loading.value = true

  // 更新对话标题
  if (conv.title === '新对话') {
    conv.title = text.slice(0, 15) + (text.length > 15 ? '…' : '')
  }

  // 先插入一条空的 AI 消息，后续逐步填充
  addMessage('assistant', '')

  nextTick(() => scrollToBottom())

  sendMessageStream(conv.chatId, text, {
    onChunk: (chunk) => {
      const lastMsg = messages.value[messages.value.length - 1]
      if (lastMsg && lastMsg.role === 'assistant') {
        lastMsg.content += chunk
        nextTick(() => scrollToBottom())
      }
    },
    onDone: () => {
      loading.value = false
      // 如果流没有返回任何内容
      const lastMsg = messages.value[messages.value.length - 1]
      if (lastMsg && lastMsg.role === 'assistant' && !lastMsg.content) {
        lastMsg.content = '抱歉，我暂时无法回复。'
      }
      nextTick(() => scrollToBottom())
    },
    onError: (err) => {
      console.error('SSE 流式错误:', err)
      const lastMsg = messages.value[messages.value.length - 1]
      if (lastMsg && lastMsg.role === 'assistant' && !lastMsg.content) {
        lastMsg.content = '抱歉，服务暂时不可用，请稍后再试。'
      }
      loading.value = false
    },
  })
}

function scrollToBottom() {
  if (chatArea.value) {
    chatArea.value.scrollTop = chatArea.value.scrollHeight
  }
}

// 页面加载时自动创建一个会话
onMounted(() => {
  newChat()
})

/**
 * 快捷提问
 */
const quickQuestions = [
  '我最近总是失眠，怎么办？',
  '如何缓解工作压力？',
  '总是感到焦虑正常吗？',
  '怎样改善人际关系？',
]
</script>

<template>
  <div class="ai-chat">
    <!-- ======== 左侧边栏 ======== -->
    <aside class="chat-sidebar">
      <el-button type="primary" class="new-chat-btn" @click="newChat">
        + 新对话
      </el-button>

      <div class="conv-list">
        <div
          v-for="conv in conversations"
          :key="conv.id"
          class="conv-item"
          :class="{ active: conv.id === activeId }"
          @click="switchChat(conv)"
        >
          <span class="conv-title">{{ conv.title }}</span>
        </div>
      </div>

      <div class="sidebar-footer">
        <el-button text @click="clearChat">清空对话</el-button>
      </div>
    </aside>

    <!-- ======== 右侧聊天区 ======== -->
    <div class="chat-main">
      <!-- 欢迎提示（无消息时显示） -->
      <div v-if="messages.length === 0" class="chat-welcome">
        <div class="welcome-avatar">🤖</div>
        <h2>你好，我是心灵港湾 AI 助手</h2>
        <p>你可以向我倾诉任何心理困扰，我会用心倾听并提供专业建议。</p>
        <div class="quick-questions">
          <el-button
            v-for="q in quickQuestions"
            :key="q"
            round
            @click="inputText = q; handleSend()"
          >
            {{ q }}
          </el-button>
        </div>
      </div>

      <!-- 消息列表 -->
      <div
        v-else
        ref="chatArea"
        class="chat-messages"
      >
        <div
          v-for="(msg, i) in messages"
          :key="i"
          class="message-row"
          :class="msg.role === 'user' ? 'msg-user' : 'msg-ai'"
        >
          <div class="msg-avatar">
            {{ msg.role === 'user' ? '👤' : '🤖' }}
          </div>
          <div class="msg-body">
            <div class="msg-bubble">{{ msg.content }}</div>
            <span class="msg-time">{{ msg.time }}</span>
          </div>
        </div>

        <!-- 加载动画 -->
        <div v-if="loading" class="message-row msg-ai">
          <div class="msg-avatar">🤖</div>
          <div class="msg-body">
            <div class="msg-bubble typing">
              <span class="dot"></span><span class="dot"></span><span class="dot"></span>
            </div>
          </div>
        </div>
      </div>

      <!-- 底部输入区 -->
      <div class="chat-input">
        <el-input
          v-model="inputText"
          type="textarea"
          :rows="2"
          placeholder="请输入你的问题..."
          resize="none"
          @keydown.enter.exact.prevent="handleSend"
        />
        <el-button
          type="primary"
          class="send-btn"
          :disabled="!inputText.trim() || loading"
          @click="handleSend"
        >
          发送
        </el-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* ===== 整体布局 ===== */
.ai-chat {
  display: flex;
  height: calc(100vh - 180px);
  min-height: 500px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 16px rgba(0, 0, 0, 0.06);
  overflow: hidden;
}

/* ===== 左侧边栏 ===== */
.chat-sidebar {
  width: 260px;
  background: #f7f8fa;
  border-right: 1px solid #ebeef5;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.new-chat-btn {
  margin: 16px;
}

.conv-list {
  flex: 1;
  overflow-y: auto;
  padding: 0 8px;
}

.conv-item {
  padding: 12px 16px;
  border-radius: 8px;
  cursor: pointer;
  margin-bottom: 4px;
  transition: background 0.2s;
}

.conv-item:hover {
  background: #e8eaed;
}

.conv-item.active {
  background: #d9ecff;
}

.conv-title {
  font-size: 14px;
  color: #333;
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sidebar-footer {
  padding: 12px 16px;
  border-top: 1px solid #ebeef5;
  text-align: center;
}

/* ===== 右侧聊天区 ===== */
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

/* ---- 欢迎页 ---- */
.chat-welcome {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  text-align: center;
}

.welcome-avatar {
  font-size: 64px;
  margin-bottom: 20px;
}

.chat-welcome h2 {
  font-size: 22px;
  color: #303133;
  margin-bottom: 8px;
}

.chat-welcome p {
  color: #909399;
  margin-bottom: 28px;
}

.quick-questions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: center;
}

/* ---- 消息列表 ---- */
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
  background: #fafafa;
}

.message-row {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  max-width: 80%;
}

.msg-user {
  flex-direction: row-reverse;
  margin-left: auto;
}

.msg-ai {
  margin-right: auto;
}

.msg-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  flex-shrink: 0;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}

.msg-body {
  display: flex;
  flex-direction: column;
}

.msg-user .msg-body {
  align-items: flex-end;
}

.msg-bubble {
  padding: 12px 16px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.7;
  word-break: break-word;
}

.msg-user .msg-bubble {
  background: #409eff;
  color: #fff;
  border-bottom-right-radius: 4px;
}

.msg-ai .msg-bubble {
  background: #fff;
  color: #303133;
  border-bottom-left-radius: 4px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}

.msg-time {
  font-size: 12px;
  color: #c0c4cc;
  margin-top: 4px;
}

/* ---- 打字动画 ---- */
.typing {
  display: flex;
  gap: 4px;
  align-items: center;
  padding: 16px 20px !important;
}

.typing .dot {
  width: 8px;
  height: 8px;
  background: #c0c4cc;
  border-radius: 50%;
  animation: bounce 1.4s infinite ease-in-out both;
}

.typing .dot:nth-child(1) { animation-delay: -0.32s; }
.typing .dot:nth-child(2) { animation-delay: -0.16s; }

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}

/* ---- 底部输入 ---- */
.chat-input {
  display: flex;
  align-items: flex-end;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid #ebeef5;
  background: #fff;
}

.send-btn {
  flex-shrink: 0;
}
</style>
