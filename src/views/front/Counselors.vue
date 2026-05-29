<script setup>
import { ref, computed, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { ElMessageBox, ElMessage } from 'element-plus'
import { createChat, sendMessageStream, getChatHistory, listChats, deleteChat, renameChat, clearAllChats, submitMentalHealth, updateChatMessage } from '@/api/chat'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()

// ============================================================
// 对话列表（左侧边栏）
// ============================================================
const conversations = ref([])
const activeId = ref(null)
const openMenuId = ref(null)  // 当前打开的下拉菜单所属的对话 ID

// 起始对话引导
const starterPrompts = [
  '今天我的心情很糟糕',
  '最近总是感觉很焦虑',
  '工作和生活让我压力很大',
  '最近我学会了一些放松的方式',
  '我总是控制不住想太多',
  '今天想分享一些开心的事情',
]

/** 点击起始引导词，填入输入框并发送 */
function handleStarterPrompt(text) {
  inputText.value = text
  handleSend()
}

/** 切换下拉菜单 */
function toggleMenu(convId) {
  openMenuId.value = openMenuId.value === convId ? null : convId
}

/** 点击页面其他位置关闭菜单 */
function closeMenu() {
  openMenuId.value = null
}

/** 从数据库加载当前用户的对话列表 */
async function loadChatList() {
  if (!userStore.isLoggedIn) return
  try {
    const res = await listChats()
    const list = res.data || res || []
    if (Array.isArray(list) && list.length > 0) {
      conversations.value = list.map((c) => ({
        id: c.chat_id,
        chatId: c.chat_id,
        dbId: c.id,
        title: c.title || '新对话',
      }))
      // 自动选中最近一个
      activeId.value = conversations.value[0].chatId
      await switchChat(conversations.value[0])
    }
  } catch {
    // 加载失败，保持空列表
  }
}

/** 从后端创建新对话并加入列表 */
async function newChat() {
  try {
    const res = await createChat()
    const chatId = res.chat_id || res.data?.chat_id
    const dbId = res.id || res.data?.id
    conversations.value.unshift({ id: chatId, chatId, dbId, title: '新对话' })
    activeId.value = chatId
    messages.value = []
    inputText.value = ''
  } catch (err) {
    console.error('createChat 失败:', err)
    const localId = Date.now()
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
const abortFn = ref(null)
const chatArea = ref(null)

// ============================================================
// A2UI 心理健康表单（对话内嵌，非弹窗）
// ============================================================
const emotionOptions = ['开心', '平静', '充满希望', '感恩', '满足', '放松', '焦虑', '悲伤', '愤怒', '恐惧', '压力', '其他']

/** 在对话中插入一张可填写的心理健康自评卡片 */
function insertFormCard(aiContext, msgId = null) {
  const formId = 'form_' + (msgId || Date.now())
  messages.value.push({
    role: 'form',
    formId,
    msgId,           // 数据库主键，用于后续持久化更新
    submitted: false,
    submitting: false,
    formData: {
      mood_score: 5,
      emotion_type: '',
      description: '',
      ai_context: aiContext || '',
    },
    time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
  })
  nextTick(() => scrollToBottom())
}

/** 提交某张表单卡片 */
async function submitFormCard(msg) {
  if (!msg.formData.emotion_type) {
    ElMessage.warning('请选择情绪类型')
    return
  }
  msg.submitting = true
  try {
    const conv = conversations.value.find((c) => c.id === activeId.value)
    await submitMentalHealth({
      chat_id: conv?.chatId || null,
      mood_score: msg.formData.mood_score,
      emotion_type: msg.formData.emotion_type,
      description: msg.formData.description,
      ai_context: msg.formData.ai_context,
    })
    msg.submitted = true
    msg.submitting = false
    // 持久化提交状态到数据库（刷新后不丢失）
    if (msg.msgId) {
      try {
        await updateChatMessage(msg.msgId, JSON.stringify({
          submitted: true,
          formData: msg.formData,
          ai_context: msg.formData.ai_context || '',
        }))
      } catch { /* 持久化失败不阻塞 */ }
    }
    ElMessage.success('已保存')
  } catch {
    ElMessage.error('保存失败，请稍后重试')
    msg.submitting = false
  }
}

/** 当前聊天区的显示模式：'empty' | 'prompt' | 'messages' */
const displayMode = computed(() => {
  if (conversations.value.length === 0 || !activeId.value) return 'empty'
  if (messages.value.length === 0) return 'prompt'
  return 'messages'
})

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
  openMenuId.value = null
  activeId.value = conv.id
  // 立即清空，避免显示上一个对话的残留内容
  messages.value = []
  if (conv.chatId) {
    try {
      const res = await getChatHistory(conv.chatId)
      const list = res.messages || res.data?.messages || res.data || []
      messages.value = (Array.isArray(list) ? list : []).map((m) => {
        // 解析持久化的 form 卡片消息
        if (m.role === 'form') {
          try {
            const data = JSON.parse(m.content)
            return {
              role: 'form',
              formId: 'form_' + (m.id || Date.now()),
              msgId: m.id,
              submitted: data.submitted || false,
              submitting: false,
              formData: data.formData || {
                mood_score: 5,
                emotion_type: data.emotion_type || '',
                description: data.description || '',
                ai_context: data.ai_context || '',
              },
              time: m.time || '',
            }
          } catch {
            return { role: m.role, content: m.content, time: m.time || '' }
          }
        }
        return {
          role: m.role,
          content: m.content,
          time: m.time || '',
        }
      })
      // 如果有本地草稿（上次未完成的对话），追加到历史后面
      const draft = loadDraftFromLocal(conv.chatId)
      if (draft && draft.length > 0) {
        const lastHistoryMsg = messages.value[messages.value.length - 1]
        if (lastHistoryMsg) {
          const draftStart = draft.findIndex(
            (m) => m.content === lastHistoryMsg.content && m.role === lastHistoryMsg.role,
          )
          if (draftStart >= 0) {
            messages.value.push(...draft.slice(draftStart + 1))
          }
        }
      }
    } catch {
      messages.value = []
    }
  }
}

/** 清空当前账号下所有对话及消息（弹窗确认，同步数据库） */
async function handleClearChat() {
  try {
    await ElMessageBox.confirm('确定要清空当前账号下所有的对话记录吗？此操作不可恢复。', '清空全部对话', {
      confirmButtonText: '确定清空',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return // 用户取消
  }
  try {
    await clearAllChats()
    // 清空本地状态
    conversations.value = []
    activeId.value = null
    messages.value = []
    clearDraft()
    // 立即重新渲染：从数据库加载空列表
    await loadChatList()
    ElMessage.success('已清空全部对话')
  } catch {
    ElMessage.error('清空失败，请稍后重试')
  }
}

/** 删除单个对话（同步到数据库） */
async function handleDeleteChat(conv) {
  openMenuId.value = null
  // 调后端删除（失败也不影响本地移除）
  if (conv.dbId) {
    try {
      await deleteChat(conv.dbId)
    } catch (err) {
      console.error('后端删除失败:', err)
    }
  }
  // 清理草稿
  localStorage.removeItem(`chat_draft_${conv.chatId || conv.id}`)
  // 从列表中移除
  conversations.value = conversations.value.filter((c) => c.id !== conv.id)
  // 处理活跃对话切换
  if (activeId.value === conv.id) {
    if (conversations.value.length > 0) {
      await switchChat(conversations.value[0])
    } else {
      activeId.value = null
      messages.value = []
    }
  }
}

/** 重命名对话（同步到数据库） */
async function handleRenameChat(conv) {
  try {
    const { value } = await ElMessageBox.prompt('请输入新标题', '重命名', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      inputValue: conv.title === '新对话' ? '' : conv.title,
      inputPlaceholder: '只允许字母、汉字、数字',
      inputValidator: (val) => {
        if (!val || !val.trim()) return '标题不能为空'
        if (!/^[\u4e00-\u9fa5a-zA-Z0-9\s]+$/.test(val)) return '只允许字母、汉字和数字'
        return true
      },
    })
    const newTitle = (value || '').trim()
    if (!newTitle || newTitle === conv.title) return

    if (conv.dbId) {
      await renameChat(conv.dbId, newTitle)
    }
    conv.title = newTitle
  } catch {
    // 用户取消
  } finally {
    openMenuId.value = null
  }
}

/**
 * 将当前消息存入 localStorage（取消生成时使用）
 */
function saveDraftToLocal() {
  const conv = conversations.value.find((c) => c.id === activeId.value)
  if (!conv || messages.value.length === 0) return
  const key = `chat_draft_${conv.chatId || conv.id}`
  localStorage.setItem(key, JSON.stringify(messages.value))
}

/**
 * 从 localStorage 恢复草稿
 */
function loadDraftFromLocal(chatId) {
  const key = `chat_draft_${chatId}`
  const raw = localStorage.getItem(key)
  if (!raw) return null
  try {
    return JSON.parse(raw)
  } catch {
    return null
  }
}

/** 清除当前对话的本地草稿 */
function clearDraft() {
  const conv = conversations.value.find((c) => c.id === activeId.value)
  if (!conv) return
  const key = `chat_draft_${conv.chatId || conv.id}`
  localStorage.removeItem(key)
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

  // 更新对话标题（本地 + 持久化到数据库）
  if (conv.title === '新对话' && conv.dbId) {
    const newTitle = text.slice(0, 15) + (text.length > 15 ? '…' : '')
    conv.title = newTitle
    renameChat(conv.dbId, newTitle).catch(() => {})
  }

  // 先插入一条空的 AI 消息，后续逐步填充
  addMessage('assistant', '')

  nextTick(() => scrollToBottom())

  abortFn.value = sendMessageStream(conv.chatId, text, {
    onChunk: (chunk) => {
      const lastMsg = messages.value[messages.value.length - 1]
      if (lastMsg && lastMsg.role === 'assistant') {
        lastMsg.content += chunk
        nextTick(() => scrollToBottom())
      }
    },
    onDone: () => {
      loading.value = false
      abortFn.value = null
      clearDraft()
      const lastMsg = messages.value[messages.value.length - 1]
      if (lastMsg && lastMsg.role === 'assistant' && !lastMsg.content) {
        lastMsg.content = '抱歉，我暂时无法回复。'
      }
      nextTick(() => scrollToBottom())
    },
    onCorrection: (corrected) => {
      const lastMsg = messages.value[messages.value.length - 1]
      if (lastMsg && lastMsg.role === 'assistant') {
        lastMsg.content = corrected
        nextTick(() => scrollToBottom())
      }
    },
    onError: (err) => {
      console.error('SSE 流式错误:', err)
      loading.value = false
      abortFn.value = null
      const lastMsg = messages.value[messages.value.length - 1]
      if (lastMsg && lastMsg.role === 'assistant' && !lastMsg.content) {
        lastMsg.content = '抱歉，服务暂时不可用，请稍后再试。'
      }
    },
    onCancel: () => {
      loading.value = false
      abortFn.value = null
    },
    onFormTrigger: (aiContext, msgId) => {
      console.log('收到 form_trigger 事件, ai_context:', aiContext?.slice(0, 50), 'msgId:', msgId)
      insertFormCard(aiContext, msgId)
    },
  })
}

/**
 * 停止生成 —— 取消 SSE 流，保留已生成内容到 localStorage
 */
function stopGeneration() {
  if (abortFn.value) {
    abortFn.value()
    abortFn.value = null
  }
  loading.value = false
  // 保留已生成内容，存入 localStorage
  saveDraftToLocal()
}

function scrollToBottom() {
  if (chatArea.value) {
    chatArea.value.scrollTop = chatArea.value.scrollHeight
  }
}

// 页面加载时恢复历史会话或创建新会话
onMounted(async () => {
  document.addEventListener('click', closeMenu)
  if (userStore.isLoggedIn) {
    await loadChatList()
  }
  // 没有对话时不做任何操作，等待用户主动创建
})

onBeforeUnmount(() => {
  document.removeEventListener('click', closeMenu)
})

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
          <span class="conv-menu-btn" @click.stop="toggleMenu(conv.id)">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
              <circle cx="5" cy="12" r="2" />
              <circle cx="12" cy="12" r="2" />
              <circle cx="19" cy="12" r="2" />
            </svg>
          </span>
          <div v-if="openMenuId === conv.id" class="conv-menu-dropdown" @click.stop>
            <div class="menu-item" @click="handleRenameChat(conv)">重命名</div>
            <div class="menu-item danger" @click="handleDeleteChat(conv)">删除对话</div>
          </div>
        </div>
      </div>

      <div class="sidebar-footer">
        <el-button type="danger" plain @click="handleClearChat">清空对话</el-button>
      </div>
    </aside>

    <!-- ======== 右侧聊天区 ======== -->
    <div class="chat-main">
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
            @click="handleStarterPrompt(prompt)"
          >{{ prompt }}</button>
        </div>
      </div>

      <!-- 消息列表 -->
      <div
        v-else
        ref="chatArea"
        class="chat-messages"
      >
        <template v-for="(msg, i) in messages" :key="i">
          <!-- 心理健康表单卡片 -->
          <div v-if="msg.role === 'form'" class="form-card">
            <div class="form-card-header">
              <span class="form-card-icon">📋</span>
              <span>心理健康自评（可选）</span>
            </div>
            <template v-if="msg.submitted">
              <div class="form-done">
                <span>✅</span> 已保存 — {{ msg.formData.emotion_type }} · 评分 {{ msg.formData.mood_score }}/10
              </div>
            </template>
            <template v-else>
              <div class="form-card-body">
                <div class="form-row">
                  <span class="form-label">情绪评分</span>
                  <span class="form-score-badge">{{ msg.formData.mood_score }}</span>
                  <el-slider v-model="msg.formData.mood_score" :min="1" :max="10" :step="1" show-stops size="small" style="flex:1; margin-left:8px;" />
                </div>
                <div class="form-row">
                  <span class="form-label">情绪类型</span>
                  <el-select v-model="msg.formData.emotion_type" placeholder="选择情绪" size="small" style="width:140px;">
                    <el-option v-for="e in emotionOptions" :key="e" :label="e" :value="e" />
                  </el-select>
                </div>
                <div class="form-row">
                  <el-input v-model="msg.formData.description" type="textarea" :rows="2" maxlength="200" show-word-limit size="small" placeholder="补充描述（可选）" />
                </div>
                <el-button type="primary" size="small" :loading="msg.submitting" @click="submitFormCard(msg)">
                  提交记录
                </el-button>
              </div>
            </template>
          </div>

          <!-- 普通消息 -->
          <div v-else class="message-row" :class="msg.role === 'user' ? 'msg-user' : 'msg-ai'">
            <div class="msg-avatar">
              {{ msg.role === 'user' ? '👤' : '🤖' }}
            </div>
            <div class="msg-body">
              <div class="msg-bubble" :class="{ typing: msg.role === 'assistant' && !msg.content }">
                <template v-if="msg.content">{{ msg.content }}</template>
                <template v-else>
                  <span class="dot"></span><span class="dot"></span><span class="dot"></span>
                </template>
              </div>
              <span class="msg-time">{{ msg.time }}</span>
            </div>
          </div>
        </template>
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
        <button
          class="send-btn"
          :class="{ active: !!inputText.trim(), streaming: loading }"
          :disabled="!inputText.trim() && !loading"
          @click="loading ? stopGeneration() : handleSend()"
        >
          <!-- 发送箭头 -->
          <svg v-if="!loading" class="send-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <line x1="12" y1="19" x2="12" y2="5" />
            <polyline points="5 12 12 5 19 12" />
          </svg>
          <!-- 停止方块 -->
          <svg v-else class="stop-icon" width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
            <rect x="3" y="3" width="18" height="18" rx="3" />
          </svg>
        </button>
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
  display: flex;
  align-items: center;
  padding: 12px 16px;
  border-radius: 8px;
  cursor: pointer;
  margin-bottom: 4px;
  transition: background 0.2s;
  position: relative;
}

.conv-item:hover {
  background: #e8eaed;
}

.conv-item:hover .conv-menu-btn {
  opacity: 1;
}

.conv-item.active {
  background: #d9ecff;
}

.conv-title {
  font-size: 14px;
  color: #333;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.conv-menu-btn {
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  color: #999;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.15s, background 0.15s;
  margin-left: 4px;
}

.conv-menu-btn:hover {
  background: #ddd;
  color: #555;
}

.conv-menu-dropdown {
  position: absolute;
  top: 100%;
  right: 8px;
  z-index: 100;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.12);
  padding: 4px;
  min-width: 120px;
}

.menu-item {
  padding: 8px 12px;
  font-size: 14px;
  color: #333;
  cursor: pointer;
  border-radius: 4px;
  transition: background 0.15s;
}

.menu-item:hover {
  background: #f5f5f5;
}

.menu-item.danger {
  color: #f56c6c;
}

.menu-item.danger:hover {
  background: #fef0f0;
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

/* ---- 空状态 ---- */
.chat-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  text-align: center;
}

.empty-emoji {
  font-size: 48px;
  margin-bottom: 16px;
}

.chat-empty p {
  color: #909399;
  font-size: 15px;
  margin-bottom: 20px;
}

/* 起始对话引导按钮 */
.starter-prompts {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 10px;
  max-width: 480px;
}

.starter-btn {
  padding: 8px 18px;
  background: #fff;
  border: 1px solid #e0d4d0;
  border-radius: 20px;
  color: #6b5b5b;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.starter-btn:hover {
  background: #f8f0ed;
  border-color: #c4a89e;
  color: #4a3b3b;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(180, 140, 120, 0.15);
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
  align-items: center;
  gap: 12px;
  padding: 12px 24px;
  border-top: 1px solid #ebeef5;
  background: #fff;
}

.send-btn {
  width: 36px;
  height: 36px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 8px;
  background: #d9d9d9;
  color: #fff;
  cursor: pointer;
  transition: background 0.2s, transform 0.15s;
}

.send-btn.active {
  background: #409eff;
}

.send-btn.active:hover {
  background: #337ecc;
}

.send-btn.streaming {
  background: #e6a23c;
}

.send-btn.streaming:hover {
  background: #cf9236;
}

.send-btn:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.send-btn .stop-icon {
  color: #fff;
}

/* ---- A2UI 内嵌表单卡片 ---- */
.form-card {
  max-width: 75%;
  margin: 0 0 20px 48px;
  background: #fff;
  border: 1px solid #e0e4ed;
  border-radius: 12px;
  padding: 16px 20px;
  box-shadow: 0 1px 6px rgba(0, 0, 0, 0.03);
}

.form-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 14px;
}

.form-card-icon {
  font-size: 18px;
}

.form-card-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.form-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

.form-label {
  color: #606266;
  white-space: nowrap;
  min-width: 56px;
}

.form-score-badge {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #409eff;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 13px;
  flex-shrink: 0;
}

.form-done {
  font-size: 14px;
  color: #67c23a;
  padding: 8px 0;
}
</style>
