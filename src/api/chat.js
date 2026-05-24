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
export function sendMessageStream(chatId, message, { onChunk, onDone, onError }) {
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
              // 常见的 SSE chunk 格式: { content: "增量文本" } 或 { delta: "..." } 或纯字符串
              const chunk = parsed.content || parsed.delta || parsed.text || ''
              if (chunk && typeof chunk === 'string') {
                onChunk(chunk)
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
      if (err.name === 'AbortError') return
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
 * 5. 列出所有活跃对话
 *    GET /api/chat/list
 *    返回: 对话列表（具体字段以后端实际返回为准）
 */
export function listChats() {
  return request.get('/chat/list')
}
