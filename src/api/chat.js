import request, { tryRefreshToken } from '@/utils/request'

/**
 * 1. 创建新对话
 *    POST /api/chat/create
 */
export function createChat() {
  return request.post('/chat/create')
}

/**
 * 2. 发送消息（非流式）
 *    POST /api/chat/message
 */
export function sendMessage(chatId, message) {
  return request.post('/chat/message', { chat_id: chatId, message })
}

// ============================================================
// SSE 重连配置
// ============================================================
const MAX_RETRIES = 3
const READ_TIMEOUT_MS = 45000           // 45s 无数据视为连接僵死（LLM 首 token 可能较慢）
const BASE_DELAY_MS = 1000              // 首次退避延迟
const MAX_DELAY_MS = 10000              // 最大退避延迟

/**
 * 3. 发送消息（SSE 流式）
 *
 *    🛡️ 断线重连机制：
 *    - Last-Event-ID: 服务端每条事件带 id，断线重连时跳过重复创建 user 消息，续接部分回复
 *    - 幂等键: 每次发送生成 UUID，后端 UNIQUE 约束去重，失败重试不产生重复消息
 *    - 指数退避 + 随机抖动: 1s → 2s → 4s → 10s(max)，避免惊群
 *
 *    🌐 弱网兜底：
 *    - navigator.onLine 检测，离线时等待 online 事件自动恢复
 *    - 读取超时：15s 无数据视为僵死连接，触发重连
 *    - 超过最大重试后返回失败状态 + 回调 onGiveUp，UI 可展示"点击重试"
 *
 *    📡 回调列表：
 *    - onChunk: 收到文本增量
 *    - onDone: 流正常结束
 *    - onError: 最终失败（超过最大重试或不可恢复错误）
 *    - onCorrection: 模型自我纠错
 *    - onCancel: 用户主动中断
 *    - onFormTrigger: 触发心理健康表单
 *    - onToolEvent: MCP 工具调用事件
 *    - onReconnecting: 即将重连 {reason, attempt, maxRetries}
 *    - onGiveUp: 放弃重连 {reason, lastEventId} —— UI 展示手动重试入口
 *
 *    返回值: abort 函数，调用后中断当前请求及重连锁链
 */
export function sendMessageStream(chatId, message, callbacks, retryCount = 0, lastEventId = null, resume = false, idempotencyKey = null) {
  const {
    onChunk, onDone, onError, onCorrection, onCancel,
    onFormTrigger, onToolEvent,
    onReconnecting,   // (info) => void    重连前通知 UI
    onGiveUp,          // (info) => void    彻底放弃时通知 UI
  } = callbacks

  const token = localStorage.getItem('access_token') || ''

  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: 'Bearer ' + token } : {}),
    ...(lastEventId != null ? { 'Last-Event-ID': String(lastEventId) } : {}),
  }

  let currentEventId = lastEventId || 0
  let completed = false
  let readTimer = null   // 读取超时计时器
  let aborted = false

  const controller = new AbortController()

  // ---- 弱网检测：offline 时标记，online 时触发重连 ----
  let networkLost = false

  function onNetworkOffline() {
    networkLost = true
    console.log('[SSE] 网络断开，等待恢复...')
  }

  function onNetworkOnline() {
    if (networkLost && !completed && !aborted) {
      networkLost = false
      console.log('[SSE] 网络恢复，尝试继续接收...')
      // 网络恢复后不做额外操作——如果 stream 已被 abort，后续 catch 会触发 retry
    }
  }

  window.addEventListener('offline', onNetworkOffline)
  window.addEventListener('online', onNetworkOnline)

  function cleanupNetworkListeners() {
    window.removeEventListener('offline', onNetworkOffline)
    window.removeEventListener('online', onNetworkOnline)
  }

  // ---- 读取超时重置 ----
  function resetReadTimer(reader) {
    if (readTimer) clearTimeout(readTimer)
    readTimer = setTimeout(() => {
      console.log('[SSE] 读取超时 (15s 无数据)，关闭连接触发重连')
      reader.cancel('read-timeout')
    }, READ_TIMEOUT_MS)
  }

  function clearReadTimer() {
    if (readTimer) { clearTimeout(readTimer); readTimer = null }
  }

  // ---- 退避延迟（含随机抖动 ±20%） ----
  function backoffDelay(attempt) {
    const base = Math.min(BASE_DELAY_MS * Math.pow(2, attempt), MAX_DELAY_MS)
    const jitter = base * 0.2 * (Math.random() * 2 - 1)
    return Math.round(base + jitter)
  }

  // ---- 发起重连 ----
  function scheduleRetry(reason) {
    if (aborted) return
    if (retryCount >= MAX_RETRIES) {
      console.log(`[SSE] 已达最大重试次数 (${MAX_RETRIES})，放弃`)
      cleanupNetworkListeners()
      onGiveUp?.({ reason, lastEventId: currentEventId, idempotencyKey })
      onError?.(new Error(`连接失败，已重试 ${MAX_RETRIES} 次`))
      return
    }

    const attempt = retryCount + 1
    const delay = backoffDelay(retryCount)
    console.log(`[SSE] 重连 (${attempt}/${MAX_RETRIES}) 延迟${delay}ms, reason=${reason}, lastEventId=${currentEventId}`)

    onReconnecting?.({ reason, attempt, maxRetries: MAX_RETRIES })

    setTimeout(() => {
      if (aborted) return
      const retryCtrl = sendMessageStream(
        chatId, message, callbacks,
        attempt, currentEventId, resume, idempotencyKey,
      )
      controller._retryCtrl = retryCtrl
    }, delay)
  }

  // ---- 发起 HTTP 请求 ----
  const body = { chat_id: chatId, message }
  if (resume) body.resume = true
  if (idempotencyKey) body.idempotency_key = idempotencyKey

  fetch('/api/chat/message/stream', {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        if (response.status === 401) {
          const newToken = await tryRefreshToken()
          if (newToken) throw new Error('__TOKEN_REFRESHED__')
        }
        const text = await response.text().catch(() => '')
        throw new Error(text || `HTTP ${response.status}`)
      }

      const reader = response.body?.getReader()
      if (!reader) {
        throw new Error('浏览器不支持流式读取')
      }

      const decoder = new TextDecoder()
      let buffer = ''

      resetReadTimer(reader)

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        resetReadTimer(reader)

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          // SSE 注释行 (以 : 开头) —— 用作心跳，忽略
          if (line.startsWith(':')) continue

          // id: 字段（Last-Event-ID）
          if (line.startsWith('id: ')) {
            const idVal = parseInt(line.slice(4).trim(), 10)
            if (!isNaN(idVal)) currentEventId = idVal
            continue
          }

          if (line.startsWith('data: ')) {
            const jsonStr = line.slice(6).trim()
            if (jsonStr === '[DONE]') continue
            try {
              const parsed = JSON.parse(jsonStr)
              if (parsed.type === 'content') {
                if (parsed.content && typeof parsed.content === 'string') {
                  onChunk(parsed.content)
                }
              } else if (parsed.type === 'correction') {
                if (typeof onCorrection === 'function' && parsed.content) {
                  onCorrection(parsed.content)
                }
              } else if (parsed.type === 'done') {
                completed = true
                onDone?.(parsed.content, parsed.interrupted || false)
              } else if (parsed.type === 'form_trigger') {
                onFormTrigger?.(parsed.ai_context || '', parsed.msg_id || null)
              } else if (parsed.type === 'mcp_event' || parsed.type === 'tool_call' || parsed.type === 'tool_result') {
                onToolEvent?.(parsed.type, parsed.payload)
              } else if (parsed.type === 'error') {
                onError?.(parsed.error)
                cleanupNetworkListeners()
                return
              } else {
                const chunk = parsed.content || parsed.delta || parsed.text || ''
                if (chunk && typeof chunk === 'string') {
                  onChunk(chunk)
                }
              }
            } catch {
              if (jsonStr) {
                onChunk(jsonStr)
              }
            }
          }
        }
      }

      clearReadTimer()

      // 流自然结束但未收到 done 信号 → Last-Event-ID 续接
      if (!completed && !aborted) {
        scheduleRetry('stream_ended_without_done')
      }
    })
    .catch((err) => {
      clearReadTimer()

      if (err.name === 'AbortError') {
        cleanupNetworkListeners()
        onCancel?.()
        return
      }

      // Token 刷新成功 → 不消耗重试次数立即重试
      if (err.message === '__TOKEN_REFRESHED__') {
        const retryCtrl = sendMessageStream(
          chatId, message, callbacks,
          retryCount, null, false, idempotencyKey,
        )
        controller._retryCtrl = retryCtrl
        return
      }

      // 读取超时 → 重连
      if (err.message === 'read-timeout' || err?.toString?.() === 'read-timeout') {
        if (!aborted) scheduleRetry('read_timeout')
        return
      }

      // 网络离线 → 等待 online 事件后重试
      if (!navigator.onLine || err.message?.includes('Failed to fetch') || err.message?.includes('NetworkError')) {
        networkLost = true
        console.log('[SSE] 网络错误，等待网络恢复后重试...')

        function onOnlineRetry() {
          window.removeEventListener('online', onOnlineRetry)
          networkLost = false
          if (!aborted && !completed) {
            scheduleRetry('network_restored')
          }
        }
        window.addEventListener('online', onOnlineRetry, { once: true })

        // 同时在 timeout 内持续检查 navigator.onLine（兜底）
        const pollTimer = setInterval(() => {
          if (navigator.onLine && !aborted && !completed) {
            clearInterval(pollTimer)
            window.removeEventListener('online', onOnlineRetry)
            networkLost = false
            scheduleRetry('network_restored_poll')
          }
        }, 3000)
        // 2 分钟后停止轮询，交给最大重试次数兜底
        setTimeout(() => clearInterval(pollTimer), 120000)

        return
      }

      // 其他 HTTP / 网络错误 → 幂等键重试
      if (!aborted) {
        scheduleRetry(err.message?.slice(0, 60) || 'fetch_error')
      }
    })

  // ---- 返回 abort 函数 ----
  const abort = () => {
    aborted = true
    clearReadTimer()
    cleanupNetworkListeners()
    controller.abort()
    if (controller._retryCtrl) {
      controller._retryCtrl()
    }
  }

  return abort
}

/**
 * 4. 获取对话历史
 */
export function getChatHistory(chatId) {
  return request.get(`/chat/${chatId}/history`)
}

/**
 * 5. 删除对话
 */
export function deleteChat(dbId) {
  return request.delete(`/chat/${dbId}`)
}

/**
 * 6. 重命名对话
 */
export function renameChat(dbId, title) {
  return request.put(`/chat/${dbId}/rename`, { title })
}

/**
 * 7. 清空对话消息
 */
export function clearChatMessages(dbId) {
  return request.delete(`/chat/${dbId}/messages`)
}

/**
 * 7b. 清空所有对话
 */
export function clearAllChats() {
  return request.delete('/chat/clear-all')
}

/**
 * 8. 列出对话列表
 */
export function listChats() {
  return request.get('/chat/list')
}

/**
 * 9. 提交心理健康记录
 */
export function submitMentalHealth(data) {
  return request.post('/mental-health/submit', data)
}

/**
 * 10. 删除心理健康记录
 */
export function deleteMentalHealthRecord(recordId) {
  return request.delete(`/mental-health/${recordId}`)
}

/**
 * 11. 更新消息内容
 */
export function updateChatMessage(msgId, content) {
  return request.put(`/chat/message/${msgId}`, { content })
}

/**
 * 13. 心理健康统计
 */
export function getMentalHealthStats(params) {
  return request.get('/mental-health/stats', { params })
}

/**
 * 14. 心理健康记录列表
 */
export function getMentalHealthRecords(params) {
  return request.get('/mental-health/records', { params })
}

/**
 * 15. 重新生成 AI 回复
 */
export function regenerateMessage(chatId) {
  return request.post(`/chat/${chatId}/regenerate`)
}

/**
 * 16. 置顶 / 取消置顶
 */
export function pinChat(chatId) {
  return request.post(`/chat/${chatId}/pin`)
}

export function unpinChat(chatId) {
  return request.post(`/chat/${chatId}/unpin`)
}
