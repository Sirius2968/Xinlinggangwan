import { ref, computed, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import {
  sendMessageStream, regenerateMessage, renameChat,
  submitMentalHealth, updateChatMessage,
} from '@/api/chat'
import { formatTime } from '@/utils/time'

export const emotionOptions = ['开心', '平静', '充满希望', '感恩', '满足', '放松', '焦虑', '悲伤', '愤怒', '恐惧', '压力', '其他']

/**
 * 创建带时间+RAF双重节流的流式回调包装
 * - RAF 层：合并同一帧内的多个 chunk
 * - 时间层：最少间隔 ~50ms 才 flush，约 20 次/秒
 *   既避免高频 v-html 重渲染，又保持足够平滑的文本增长
 */
const MIN_FLUSH_INTERVAL = 50  // ms

function createThrottledCallbacks(raw) {
  let buffer = ''
  let rafId = null
  let lastFlushTime = 0

  function flush() {
    if (rafId) {
      cancelAnimationFrame(rafId)
      rafId = null
    }
    if (buffer) {
      raw.onChunk(buffer)
      buffer = ''
      lastFlushTime = performance.now()
    }
  }

  function scheduleFlush() {
    if (rafId) return
    rafId = requestAnimationFrame(() => {
      rafId = null
      const elapsed = performance.now() - lastFlushTime
      if (elapsed >= MIN_FLUSH_INTERVAL) {
        // 距上次更新已超过阈值，立即 flush
        const text = buffer
        buffer = ''
        if (text) {
          raw.onChunk(text)
          lastFlushTime = performance.now()
        }
      } else {
        // 距上次更新太近，推迟到间隔满后再 flush
        const remaining = MIN_FLUSH_INTERVAL - elapsed
        setTimeout(() => {
          const text = buffer
          buffer = ''
          if (text) {
            raw.onChunk(text)
            lastFlushTime = performance.now()
          }
        }, remaining)
      }
    })
  }

  return {
    onChunk: (chunk) => {
      buffer += chunk
      scheduleFlush()
    },
    onDone: (...args) => {
      flush()
      raw.onDone(...args)
    },
    onCorrection: (corrected) => {
      flush()
      raw.onCorrection(corrected)
    },
    onError: (err) => {
      flush()
      raw.onError(err)
    },
    onCancel: () => {
      flush()
      raw.onCancel()
    },
    onFormTrigger: raw.onFormTrigger,
    onToolEvent: raw.onToolEvent,
    onReconnecting: raw.onReconnecting,
    onGiveUp: raw.onGiveUp,
  }
}

export function useChatStream(ctx) {
  const {
    conversations, activeId, chatStates, chatAbortFns, getChatState,
    saveDraftToLocal, clearDraft,
  } = ctx

  // ============================================================
  // 消息状态
  // ============================================================
  const messages = ref([])
  const inputText = ref('')
  const loading = ref(false)
  const abortFn = ref(null)
  const hoveredMsgIndex = ref(-1)

  // ---- 重连状态 ----
  const reconnecting = ref(false)       // 正在重连中
  const reconnectStatus = ref(null)     // { attempt, maxRetries } 或 null
  const giveUpInfo = ref(null)          // { reason, idempotencyKey, chatId, message } 彻底失败时设置

  function resetReconnectState() {
    reconnecting.value = false
    reconnectStatus.value = null
    giveUpInfo.value = null
  }

  /** 手动重试：用户点击"重试"按钮时调用 */
  function retryLastMessage() {
    const info = giveUpInfo.value
    if (!info) return
    resetReconnectState()

    const { chatId, message: msg, idempotencyKey } = info
    const conv = conversations.value.find((c) => c.chatId === chatId)
    if (!conv) return
    const convId = conv.id
    const state = getChatState(chatId)

    state.loading = true
    if (activeId.value === convId) {
      messages.value = state.messages
      loading.value = true
    }

    chatAbortFns[chatId] = sendMessageStream(chatId, msg, buildStreamCallbacks(chatId, convId, state, idempotencyKey), 0, null, false, idempotencyKey)

    abortFn.value = () => {
      if (chatAbortFns[chatId]) {
        chatAbortFns[chatId]()
        chatAbortFns[chatId] = null
      }
    }
  }

  // 滚动函数注入（由父组件挂载时设置）
  const scrollToBottomFn = ref(null)

  const displayMode = computed(() => {
    if (conversations.value.length === 0 || !activeId.value) return 'empty'
    if (messages.value.length === 0) return 'prompt'
    return 'messages'
  })

  // ============================================================
  // 滚动
  // ============================================================
  function scrollToBottom() {
    scrollToBottomFn.value?.()
  }

  let scrollPending = false
  function scrollToBottomSmooth() {
    if (scrollPending) return
    scrollPending = true
    requestAnimationFrame(() => {
      scrollPending = false
      scrollToBottom()
    })
  }

  // ============================================================
  // 表单卡片
  // ============================================================
  function makeFormCard(aiContext, msgId = null) {
    return {
      role: 'form',
      formId: 'form_' + (msgId || Date.now()),
      msgId,
      submitted: false,
      submitting: false,
      formData: {
        mood_score: 5,
        emotion_type: '',
        description: '',
        ai_context: aiContext || '',
      },
      time: formatTime(),
    }
  }

  function insertFormCard(aiContext, msgId = null) {
    messages.value.push(makeFormCard(aiContext, msgId))
    nextTick(() => scrollToBottom())
  }

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
      if (msg.msgId) {
        try {
          await updateChatMessage(msg.msgId, JSON.stringify({
            submitted: true,
            formData: msg.formData,
            ai_context: msg.formData.ai_context || '',
          }))
        } catch (e) {
          console.error('表单持久化失败:', e)
          ElMessage.error('保存失败，请稍后重试')
          msg.submitted = false
          msg.submitting = false
          return
        }
      }
      ElMessage.success('已保存')
    } catch {
      ElMessage.error('保存失败，请稍后重试')
      msg.submitting = false
    }
  }

  // ============================================================
  // 流式回调工厂：为给定对话生成完整回调集（含重连 / 放弃处理）
  // ============================================================
  function buildStreamCallbacks(chatId, convId, state, idempotencyKey) {
    return createThrottledCallbacks({
      onChunk: (chunk) => {
        const msgs = state.messages
        const lastMsg = msgs[msgs.length - 1]
        if (lastMsg && lastMsg.role === 'assistant') {
          lastMsg.content += chunk
          if (activeId.value === convId) {
            nextTick(() => scrollToBottomSmooth())
          }
        }
      },
      onDone: (content, interrupted) => {
        resetReconnectState()
        state.loading = false
        chatAbortFns[chatId] = null
        clearDraft()
        const msgs = state.messages
        const lastMsg = msgs[msgs.length - 1]
        if (lastMsg && lastMsg.role === 'assistant') {
          if (!lastMsg.content) {
            lastMsg.content = '抱歉，我暂时无法回复。'
          }
          if (interrupted) lastMsg.interrupted = true
        }
        if (activeId.value === convId) {
          loading.value = false
          abortFn.value = null
          nextTick(() => scrollToBottomSmooth())
        }
      },
      onCorrection: (corrected) => {
        const msgs = state.messages
        const lastMsg = msgs[msgs.length - 1]
        if (lastMsg && lastMsg.role === 'assistant') {
          lastMsg.content = corrected
          if (activeId.value === convId) {
            nextTick(() => scrollToBottomSmooth())
          }
        }
      },
      onError: (err) => {
        console.error('SSE 流式错误:', err)
        state.loading = false
        chatAbortFns[chatId] = null
        const msgs = state.messages
        const lastMsg = msgs[msgs.length - 1]
        if (lastMsg && lastMsg.role === 'assistant' && !lastMsg.content) {
          lastMsg.content = '抱歉，服务暂时不可用，请稍后再试。'
        }
        if (activeId.value === convId) {
          loading.value = false
          abortFn.value = null
        }
      },
      onCancel: () => {
        resetReconnectState()
        state.loading = false
        chatAbortFns[chatId] = null
        const msgs = state.messages
        const lastMsg = msgs[msgs.length - 1]
        if (lastMsg && lastMsg.role === 'assistant') {
          if (!lastMsg.content) lastMsg.content = ''
          lastMsg.interrupted = true
        }
        saveDraftToLocal(msgs)
        if (activeId.value === convId) {
          loading.value = false
          abortFn.value = null
        }
      },
      onFormTrigger: (aiContext, msgId) => {
        state.messages.push(makeFormCard(aiContext, msgId))
        if (activeId.value === convId) {
          nextTick(() => scrollToBottom())
        }
      },
      onToolEvent: (type, payload) => {
        console.log(`%c[Dev] ${type}`, 'color:#409eff;font-weight:bold', payload)
      },
      // ---- 重连 / 放弃（新增） ----
      onReconnecting: ({ reason, attempt, maxRetries }) => {
        reconnecting.value = true
        reconnectStatus.value = { attempt, maxRetries }
        console.log(`[SSE] 正在重连 (${attempt}/${maxRetries}): ${reason}`)
      },
      onGiveUp: ({ reason }) => {
        resetReconnectState()
        state.loading = false
        chatAbortFns[chatId] = null
        // 保留 AI 消息已有的部分内容
        const msgs = state.messages
        const lastMsg = msgs[msgs.length - 1]
        if (lastMsg && lastMsg.role === 'assistant' && !lastMsg.content) {
          lastMsg.content = `[网络不稳定，消息发送失败]`
        }
        // 保存手动重试所需信息
        const userMsg = [...msgs].reverse().find(m => m.role === 'user')
        giveUpInfo.value = {
          reason,
          chatId,
          message: userMsg?.content || '',
          idempotencyKey,
        }
        if (activeId.value === convId) {
          loading.value = false
          abortFn.value = null
        }
        ElMessage.warning('消息发送失败，请点击下方重试按钮')
      },
    })
  }

  // ============================================================
  // 发送消息（SSE 流式）
  // ============================================================
  function handleSend() {
    const text = inputText.value.trim()
    if (!text || loading.value) return

    const conv = conversations.value.find((c) => c.id === activeId.value)
    if (!conv || !conv.chatId) {
      messages.value.push({
        role: 'assistant', content: '会话未创建成功，请点击"新对话"重试。',
        time: formatTime(),
      })
      return
    }

    const chatId = conv.chatId
    const convId = conv.id
    const state = getChatState(chatId)
    const now = () => formatTime()
    const idempotencyKey = crypto.randomUUID()

    resetReconnectState()

    state.messages.push({ role: 'user', content: text, time: now(), idempotencyKey })
    inputText.value = ''

    if (conv.title === '新对话' && conv.dbId) {
      const newTitle = text.slice(0, 15) + (text.length > 15 ? '…' : '')
      conv.title = newTitle
      renameChat(conv.dbId, newTitle).catch(() => {})
    }

    state.messages.push({ role: 'assistant', content: '', time: now() })
    state.loading = true

    messages.value = state.messages
    loading.value = true

    nextTick(() => scrollToBottom())

    chatAbortFns[chatId] = sendMessageStream(
      chatId, text,
      buildStreamCallbacks(chatId, convId, state, idempotencyKey),
      0, null, false, idempotencyKey,
    )

    abortFn.value = () => {
      if (chatAbortFns[chatId]) {
        chatAbortFns[chatId]()
        chatAbortFns[chatId] = null
      }
    }
  }

  function stopGeneration() {
    const conv = conversations.value.find((c) => c.id === activeId.value)
    if (conv && chatAbortFns[conv.chatId]) {
      chatAbortFns[conv.chatId]()
      chatAbortFns[conv.chatId] = null
    }
    abortFn.value = null
    loading.value = false
    if (conv && chatStates[conv.chatId]) {
      chatStates[conv.chatId].loading = false
    }
    saveDraftToLocal(messages.value)
  }

  // ============================================================
  // 重新生成
  // ============================================================
  async function handleRegenerate(msgIndex) {
    const conv = conversations.value.find((c) => c.id === activeId.value)
    if (!conv || !conv.chatId) {
      ElMessage.error('会话未创建成功')
      return
    }
    try {
      const res = await regenerateMessage(conv.chatId)
      const triggerMsg = (res.data?.trigger_message) || (res.trigger_message)
      if (!triggerMsg) {
        ElMessage.error('没有找到可重新生成的消息')
        return
      }

      const chatId = conv.chatId
      const convId = conv.id
      const state = getChatState(chatId)
      const idempotencyKey = crypto.randomUUID()

      resetReconnectState()

      state.messages.splice(msgIndex, 1)
      state.messages.push({
        role: 'assistant', content: '',
        time: formatTime(),
      })
      state.loading = true

      messages.value = state.messages
      loading.value = true

      chatAbortFns[chatId] = sendMessageStream(
        chatId, triggerMsg,
        buildStreamCallbacks(chatId, convId, state, idempotencyKey),
        0, null, false, idempotencyKey,
      )

      abortFn.value = () => {
        if (chatAbortFns[chatId]) {
          chatAbortFns[chatId]()
          chatAbortFns[chatId] = null
        }
      }
    } catch (err) {
      console.error('regenerate 失败:', err)
      ElMessage.error('重新生成失败，请稍后重试')
    }
  }

  // ============================================================
  // 继续生成（中断的 AI 回复续写）
  // ============================================================
  async function handleContinue(msgIndex) {
    const conv = conversations.value.find((c) => c.id === activeId.value)
    if (!conv || !conv.chatId) {
      ElMessage.error('会话未创建成功')
      return
    }

    let userMsg = null
    for (let i = msgIndex - 1; i >= 0; i--) {
      if (messages.value[i]?.role === 'user') {
        userMsg = messages.value[i]
        break
      }
    }
    if (!userMsg) {
      ElMessage.error('没有找到对应的用户消息')
      return
    }

    const chatId = conv.chatId
    const convId = conv.id
    const state = getChatState(chatId)

    resetReconnectState()

    const targetMsg = state.messages[msgIndex]
    if (targetMsg && targetMsg.role === 'assistant') {
      targetMsg.interrupted = false
    }

    state.loading = true
    messages.value = state.messages
    loading.value = true

    chatAbortFns[chatId] = sendMessageStream(
      chatId, userMsg.content,
      buildStreamCallbacks(chatId, convId, state),
      0, null, true,  // resume=true: 服务端跳过创建 user 消息，续接部分回复
    )

    abortFn.value = () => {
      if (chatAbortFns[chatId]) {
        chatAbortFns[chatId]()
        chatAbortFns[chatId] = null
      }
    }
  }

  // ============================================================
  // 复制 Markdown
  // ============================================================
  async function copyMarkdown(msg) {
    try {
      await navigator.clipboard.writeText(msg.content || '')
      ElMessage.success('已复制到剪贴板')
    } catch {
      ElMessage.error('复制失败')
    }
  }

  function handleStarterPrompt(text) {
    inputText.value = text
    handleSend()
  }

  return {
    messages,
    inputText,
    loading,
    abortFn,
    hoveredMsgIndex,
    scrollToBottomFn,
    displayMode,
    // 重连状态
    reconnecting,
    reconnectStatus,
    giveUpInfo,
    retryLastMessage,
    resetReconnectState,
    // 方法
    scrollToBottom,
    scrollToBottomSmooth,
    makeFormCard,
    insertFormCard,
    submitFormCard,
    handleSend,
    stopGeneration,
    handleRegenerate,
    handleContinue,
    copyMarkdown,
    handleStarterPrompt,
  }
}

