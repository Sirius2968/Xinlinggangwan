import { ref, reactive } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useConfirm } from '@/composables/useConfirm'
import { useUserStore } from '@/stores/user'
import {
  createChat, listChats, deleteChat, renameChat,
  clearAllChats, pinChat, unpinChat, getChatHistory,
} from '@/api/chat'
import { formatTime } from '@/utils/time'

export function useChatConversations() {
  const userStore = useUserStore()
  const { confirm } = useConfirm()

  // ============================================================
  // 对话列表
  // ============================================================
  const conversations = ref([])
  const activeId = ref(null)
  const openMenuId = ref(null)

  // 起始对话引导
  const starterPrompts = [
    '今天我的心情很糟糕',
    '最近总是感觉很焦虑',
    '工作和生活让我压力很大',
    '最近我学会了一些放松的方式',
    '我总是控制不住想太多',
    '今天想分享一些开心的事情',
  ]

  // ============================================================
  // 每个对话的状态缓存（支持后台生成）
  // ============================================================
  const chatStates = reactive({})
  const chatAbortFns = {}

  function getChatState(chatId) {
    if (!chatId) return null
    if (!chatStates[chatId]) {
      chatStates[chatId] = { messages: [], loading: false }
    }
    return chatStates[chatId]
  }

  function isBgGenerating(conv) {
    if (!conv.chatId) return false
    if (conv.id === activeId.value) return false
    return chatStates[conv.chatId]?.loading || false
  }

  function toggleMenu(convId) {
    openMenuId.value = openMenuId.value === convId ? null : convId
  }

  function closeMenu() {
    openMenuId.value = null
  }

  // ============================================================
  // 对话 CRUD
  // ============================================================

  function insertConversation(conv) {
    let insertIdx = 0
    for (let i = conversations.value.length - 1; i >= 0; i--) {
      if (conversations.value[i].isPinned) {
        insertIdx = i + 1
        break
      }
    }
    conversations.value.splice(insertIdx, 0, conv)
  }

  async function loadChatList(keepCurrent = false) {
    if (!userStore.isLoggedIn) return null
    try {
      const currentActiveId = activeId.value
      const res = await listChats()
      const list = res.data || res || []
      if (Array.isArray(list) && list.length > 0) {
        conversations.value = list.map((c) => ({
          id: c.chat_id,
          chatId: c.chat_id,
          dbId: c.id,
          title: c.title || '新对话',
          isPinned: c.is_pinned || false,
        }))
        let result = null
        if (keepCurrent && currentActiveId && conversations.value.find((c) => c.id === currentActiveId)) {
          activeId.value = currentActiveId
          result = await switchChat(conversations.value.find((c) => c.id === currentActiveId))
        } else {
          result = await switchChat(conversations.value[0])
        }
        return result  // { messages, loading }
      }
      return null
    } catch {
      return null
    }
  }

  async function newChat() {
    try {
      const res = await createChat()
      const chatId = res.chat_id || res.data?.chat_id
      const dbId = res.id || res.data?.id
      insertConversation({ id: chatId, chatId, dbId, title: '新对话', isPinned: false })
      activeId.value = chatId
      const state = getChatState(chatId)
      state.messages = []
      state.loading = false
      return { chatId, messages: state.messages }
    } catch (err) {
      console.error('createChat 失败:', err)
      const localId = Date.now()
      insertConversation({ id: localId, chatId: null, title: '新对话(离线)', isPinned: false })
      activeId.value = localId
      return { chatId: null, messages: [] }
    }
  }

  async function switchChat(conv) {
    openMenuId.value = null
    if (activeId.value === conv.id) return { messages: null }

    activeId.value = conv.id

    const cached = getChatState(conv.chatId)
    if (cached && cached.messages.length > 0) {
      return { messages: cached.messages, loading: cached.loading }
    }

    let messages = []
    if (conv.chatId) {
      try {
        const res = await getChatHistory(conv.chatId)
        const list = res.messages || res.data?.messages || res.data || []
        messages = (Array.isArray(list) ? list : []).map((m) => {
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
                time: formatTime(m.created_at || m.time),
              }
            } catch {
              return { role: m.role, content: m.content, time: formatTime(m.created_at || m.time) }
            }
          }
          return { role: m.role, content: m.content, time: formatTime(m.created_at || m.time) }
        })

        const state = getChatState(conv.chatId)
        state.messages = messages

        // 恢复本地草稿（基于 msgId/formId 或 content 匹配，避免 form 消息因 content=undefined 误匹配）
        const draft = loadDraftFromLocal(conv.chatId)
        if (draft && draft.length > 0) {
          const lastHistoryMsg = messages[messages.length - 1]
          if (lastHistoryMsg) {
            const draftStart = draft.findIndex((m) => {
              if (m.role !== lastHistoryMsg.role) return false
              if (m.role === 'form') return (m.msgId != null && m.msgId === lastHistoryMsg.msgId) || m.formId === lastHistoryMsg.formId
              return m.content === lastHistoryMsg.content
            })
            if (draftStart >= 0) {
              messages.push(...draft.slice(draftStart + 1))
            }
          }
        }
      } catch {
        messages = []
      }
    }

    return { messages, loading: false }
  }

  async function handleDeleteChat(conv) {
    openMenuId.value = null
    if (conv.dbId) {
      try { await deleteChat(conv.dbId) } catch (err) { console.error('后端删除失败:', err) }
    }
    if (conv.chatId) {
      if (chatAbortFns[conv.chatId]) {
        chatAbortFns[conv.chatId]()
        delete chatAbortFns[conv.chatId]
      }
      delete chatStates[conv.chatId]
    }
    localStorage.removeItem(`chat_draft_${conv.chatId || conv.id}`)
    conversations.value = conversations.value.filter((c) => c.id !== conv.id)
    if (activeId.value === conv.id) {
      if (conversations.value.length > 0) {
        return await switchChat(conversations.value[0])
      } else {
        activeId.value = null
        return { messages: [], loading: false }
      }
    }
    return { messages: null }
  }

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
      if (conv.dbId) { await renameChat(conv.dbId, newTitle) }
      conv.title = newTitle
    } catch {
      // 用户取消
    } finally {
      openMenuId.value = null
    }
  }

  async function handleTogglePin(conv) {
    openMenuId.value = null
    try {
      if (conv.isPinned) {
        await unpinChat(conv.chatId)
      } else {
        await pinChat(conv.chatId)
      }
      await loadChatList(true)
    } catch {
      ElMessage.error('操作失败')
    }
  }

  async function handleClearChat() {
    const ok = await confirm('确定要清空当前账号下所有的对话记录吗？此操作不可恢复。', {
      title: '清空全部对话',
    })
    if (!ok) return
    try {
      await clearAllChats()
      Object.keys(chatAbortFns).forEach((k) => { chatAbortFns[k]?.(); delete chatAbortFns[k] })
      Object.keys(chatStates).forEach((k) => delete chatStates[k])
      conversations.value = []
      activeId.value = null
      await loadChatList()
      ElMessage.success('已清空全部对话')
      return { messages: [], loading: false }
    } catch {
      ElMessage.error('清空失败，请稍后重试')
    }
  }

  // ============================================================
  // 草稿存储（供 useChatStream 内部调用）
  // ============================================================
  function saveDraftToLocal(messages) {
    const conv = conversations.value.find((c) => c.id === activeId.value)
    if (!conv || messages.length === 0) return
    const key = `chat_draft_${conv.chatId || conv.id}`
    localStorage.setItem(key, JSON.stringify(messages))
  }

  function loadDraftFromLocal(chatId) {
    const key = `chat_draft_${chatId}`
    const raw = localStorage.getItem(key)
    if (!raw) return null
    try { return JSON.parse(raw) } catch { return null }
  }

  function clearDraft() {
    const conv = conversations.value.find((c) => c.id === activeId.value)
    if (!conv) return
    const key = `chat_draft_${conv.chatId || conv.id}`
    localStorage.removeItem(key)
  }

  return {
    // 状态
    conversations,
    activeId,
    openMenuId,
    chatStates,
    chatAbortFns,
    starterPrompts,
    // 方法
    getChatState,
    isBgGenerating,
    toggleMenu,
    closeMenu,
    insertConversation,
    loadChatList,
    newChat,
    switchChat,
    handleDeleteChat,
    handleRenameChat,
    handleTogglePin,
    handleClearChat,
    saveDraftToLocal,
    loadDraftFromLocal,
    clearDraft,
  }
}
