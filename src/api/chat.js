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
export function sendMessageStream(chatId, message, { onChunk, onDone, onError, onCorrection, onCancel, onFormTrigger }) {
  const controller = new AbortController()
  const token = localStorage.getItem('token') || ''

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

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })

        // 解析 SSE 数据帧: "data: <json>\n\n"
        const lines = buffer.split('\n')
        // 最后一个可能是不完整的行，保留到下次处理
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const jsonStr = line.slice(6).trim()
            if (jsonStr === '[DONE]') continue
            try {
              const parsed = JSON.parse(jsonStr)
              // 根据事件类型处理
              if (parsed.type === 'content') {
                // 增量内容
                if (parsed.content && typeof parsed.content === 'string') {
                  onChunk(parsed.content)
                }
              } else if (parsed.type === 'correction') {
                // 修正内容（去重后的完整内容）
                // 触发特殊回调或直接替换
                if (typeof onCorrection === 'function' && parsed.content) {
                  onCorrection(parsed.content)
                }
              } else if (parsed.type === 'done') {
                // 完成信号
                onDone?.(parsed.content)
              } else if (parsed.type === 'form_trigger') {
                // 触发心理健康表单
                console.log('SSE 收到 form_trigger:', parsed)
                onFormTrigger?.(parsed.ai_context || '', parsed.msg_id || null)
              } else if (parsed.type === 'error') {
                // 错误信号
                onError?.(parsed.error)
                return
              } else {
                // 兼容其他格式
                const chunk = parsed.content || parsed.delta || parsed.text || ''
                if (chunk && typeof chunk === 'string') {
                  onChunk(chunk)
                }
              }
            } catch {
              // 非 JSON 行，可能是纯文本内容
              if (jsonStr) {
                onChunk(jsonStr)
              }
            }
          }
        }
      }
      onDone?.()
    })
    .catch((err) => {
      if (err.name === 'AbortError') {
        onCancel?.()
        return
      }
      onError?.(err)
    })

  // 返回取消函数
  return () => controller.abort()
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

// ============================================================
// 睡眠追踪 API
// ============================================================

/**
 * 13. 记录睡眠数据
 *     POST /api/sleep/track
 */
export function trackSleep(data) {
  return request.post('/sleep/track', data)
}

/**
 * 14. 获取心理健康统计数据
 *     GET /api/mental-health/stats
 *     参数: period, emotion_type, start_date, end_date
 */
export function getMentalHealthStats(params) {
  return request.get('/mental-health/stats', { params })
}

/**
 * 15. 获取心理健康记录列表（带筛选）
 *     GET /api/mental-health/records
 *     参数: period, emotion_type, start_date, end_date
 */
export function getMentalHealthRecords(params) {
  return request.get('/mental-health/records', { params })
}

/**
 * 16. 获取睡眠记录列表
 *     GET /api/sleep/records
 */
export function getSleepRecords() {
  return request.get('/sleep/records')
}

/**
 * 15. 删除睡眠记录
 *     DELETE /api/sleep/{record_id}
 */
export function deleteSleepRecord(recordId) {
  return request.delete(`/sleep/${recordId}`)
}
