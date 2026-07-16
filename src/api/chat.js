import request from '@/utils/request'

/**
 * 1. 创建新对话
 *    POST /api/chat/create
 *    返回: { chat_id: string }
 */
export function createChat() {
  return request.post('/chat/create')
}

/**
 * 2. 发送消息（非流式）
 *    POST /api/chat/message
 *    请求体: { chat_id: string, message: string }
 *    返回: { response: string, chat_history: object[] }
 */
export function sendMessage(chatId, message) {
  return request.post('/chat/message', { chat_id: chatId, message })
}

/**
 * 3. 发送消息（SSE 流式）
 *    POST /api/chat/message/stream
 *    请求体: { chat_id: string, message: string }
 *
 *    使用 fetch 实现流式读取，通过 onChunk 回调逐步返回模型输出文本。
 *    onDone 在流正常结束时调用，onError 在异常时调用。
 *    返回 abort 函数，可用于中断请求。
 */
export function sendMessageStream(chatId, message, { onChunk, onDone, onError, onCorrection, onCancel, onFormTrigger, onToolEvent }, retryCount = 0) {
  const MAX_RETRIES = 3
  const controller = new AbortController()
  const token = localStorage.getItem('access_token') || ''

  fetch('/api/chat/message/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: 'Bearer ' + token } : {}),
    },
    body: JSON.stringify({ chat_id: chatId, message }),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        const text = await response.text().catch(() => '')
        throw new Error(text || `HTTP ${response.status}`)
      }

      const reader = response.body?.getReader()
      if (!reader) {
        throw new Error('浏览器不支持流式读取')
      }

      const decoder = new TextDecoder()
      let buffer = ''
      let completed = false

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })

        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
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
                onDone?.(parsed.content)
              } else if (parsed.type === 'form_trigger') {
                onFormTrigger?.(parsed.ai_context || '', parsed.msg_id || null)
              } else if (parsed.type === 'mcp_event' || parsed.type === 'tool_call' || parsed.type === 'tool_result') {
                onToolEvent?.(parsed.type, parsed.payload)
              } else if (parsed.type === 'error') {
                onError?.(parsed.error)
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

      // 流自然结束但没收到 done 信号 → 可能是连接中断，触发重连
      if (!completed && retryCount < MAX_RETRIES) {
        console.log(`SSE 流中断，正在重连 (${retryCount + 1}/${MAX_RETRIES})...`)
        const delay = Math.min(1000 * Math.pow(2, retryCount), 8000)
        await new Promise((r) => setTimeout(r, delay))
        const retryCtrl = sendMessageStream(chatId, message, { onChunk, onDone, onError, onCorrection, onCancel, onFormTrigger, onToolEvent }, retryCount + 1)
        // 将新的 controller 替换（让外部 abort 能取消重连中的请求）
        controller._retryCtrl = retryCtrl
      } else if (!completed) {
        onError?.(new Error('SSE 连接失败，已达最大重试次数'))
      } else {
        onDone?.()
      }
    })
    .catch((err) => {
      if (err.name === 'AbortError') {
        onCancel?.()
        return
      }
      // HTTP 错误或网络错误 → 重试
      if (retryCount < MAX_RETRIES) {
        console.log(`SSE 请求失败，正在重连 (${retryCount + 1}/${MAX_RETRIES})...`)
        const delay = Math.min(1000 * Math.pow(2, retryCount), 8000)
        setTimeout(() => {
          const retryCtrl = sendMessageStream(chatId, message, { onChunk, onDone, onError, onCorrection, onCancel, onFormTrigger, onToolEvent }, retryCount + 1)
          controller._retryCtrl = retryCtrl
        }, delay)
      } else {
        onError?.(err)
      }
    })

  return () => {
    controller.abort()
    // 取消重连中的请求
    if (controller._retryCtrl) {
      controller._retryCtrl()
    }
  }
}

/**
 * 4. 获取对话历史
 *    GET /api/chat/{chat_id}/history
 *    返回: { chat_id: string, messages: object[] }
 */
export function getChatHistory(chatId) {
  return request.get(`/chat/${chatId}/history`)
}

/**
 * 5. 删除对话
 *    DELETE /api/chat/{chat_id}
 *    返回: { code: 200, msg: "已删除" }
 */
export function deleteChat(dbId) {
  return request.delete(`/chat/${dbId}`)
}

/**
 * 6. 重命名对话
 *    PUT /api/chat/{db_id}/rename
 *    请求体: { title: string }
 */
export function renameChat(dbId, title) {
  return request.put(`/chat/${dbId}/rename`, { title })
}

/**
 * 7. 清空当前对话的消息
 *    DELETE /api/chat/{db_id}/messages
 */
export function clearChatMessages(dbId) {
  return request.delete(`/chat/${dbId}/messages`)
}

/**
 * 7b. 清空当前账号下所有对话及消息
 *     DELETE /api/chat/clear-all
 */
export function clearAllChats() {
  return request.delete('/chat/clear-all')
}

/**
 * 8. 列出所有活跃对话
 *    GET /api/chat/list
 *    返回: 对话列表（具体字段以后端实际返回为准）
 */
export function listChats() {
  return request.get('/chat/list')
}

/**
 * 9. 提交心理健康记录表单
 *    POST /api/mental-health/submit
 */
export function submitMentalHealth(data) {
  return request.post('/mental-health/submit', data)
}

/**
 * 10. 删除心理健康记录
 *     DELETE /api/mental-health/{record_id}
 */
export function deleteMentalHealthRecord(recordId) {
  return request.delete(`/mental-health/${recordId}`)
}

/**
 * 11. 更新某条消息（用于持久化 form 表单状态）
 *     PUT /api/chat/message/{msg_id}
 */
export function updateChatMessage(msgId, content) {
  return request.put(`/chat/message/${msgId}`, { content })
}

/**
 * 13. 获取心理健康统计数据
 *     GET /api/mental-health/stats
 *     参数: period, emotion_type, start_date, end_date
 */
export function getMentalHealthStats(params) {
  return request.get('/mental-health/stats', { params })
}

/**
 * 14. 获取心理健康记录列表（带筛选）
 *     GET /api/mental-health/records
 *     参数: period, emotion_type, start_date, end_date
 */
export function getMentalHealthRecords(params) {
  return request.get('/mental-health/records', { params })
}

/**
 * 15. 重新生成 AI 回复
 *     POST /api/chat/{chat_id}/regenerate
 *     删除最后一条 AI 回复，返回触发它的用户消息
 */
export function regenerateMessage(chatId) {
  return request.post(`/chat/${chatId}/regenerate`)
}
