import { marked } from 'marked'
import DOMPurify from 'dompurify'

let _configured = false

function _ensureConfigured() {
  if (!_configured) {
    marked.setOptions({ breaks: true, gfm: true })
    _configured = true
  }
}

/**
 * 将 Markdown 文本渲染为安全的 HTML 字符串
 */
export function renderMarkdown(text, sanitize = true) {
  if (!text) return ''
  _ensureConfigured()
  const raw = marked.parse(text)
  return sanitize ? DOMPurify.sanitize(raw) : raw
}

/**
 * 转义 HTML 特殊字符
 */
export function escapeHtml(str) {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

// ============================================================
// 末尾未闭合语法检测
// ============================================================

function _hasTrailingUnclosedSyntax(text) {
  if (!text) return false
  const tail = text.slice(-80)

  const starsDbl = [...tail.matchAll(/\*\*/g)].length
  if (starsDbl % 2 !== 0) {
    const idx = tail.lastIndexOf('**')
    if (idx === -1 || !tail.slice(idx + 2).includes('**')) return true
  }

  const tripleTicks = [...tail.matchAll(/```/g)].length
  const allTicks = [...tail.matchAll(/`/g)].length
  const singleTicks = allTicks - tripleTicks * 3
  if (singleTicks % 2 !== 0) return true
  if (tripleTicks % 2 !== 0) return true

  if (/\[[^\]]*\]\([^)]*$/.test(tail)) return true

  return false
}

// ============================================================
// 块级增量渲染
// ============================================================

/**
 * 用 \n\n 切分段落，同时处理 \r\n 和 ``` 代码块边界。
 *
 * 返回 { completed, pending }：
 * - completed: 已确认完整的段落文本数组（可送 marked 渲染）
 * - pending:   末尾未完成的段落（可能为空字符串）
 */
function _splitBlocks(text) {
  // 统一换行符
  const normalized = text.replace(/\r\n/g, '\n')

  // ---- 定位所有 ``` 位置 ----
  const fencePositions = []
  let idx = -1
  while ((idx = normalized.indexOf('```', idx + 1)) !== -1) {
    fencePositions.push(idx)
  }

  // 代码块未闭合（奇数个 ```）→ 最后一个 ``` 之后的内容不可切分
  if (fencePositions.length % 2 !== 0) {
    const lastFence = fencePositions[fencePositions.length - 1]
    const before = normalized.slice(0, lastFence)
    const fromFence = normalized.slice(lastFence)

    const parts = before.split('\n\n')
    if (parts.length > 1) {
      return {
        completed: parts.slice(0, -1).filter(p => p.trim()),
        pending: (parts[parts.length - 1] || '') + fromFence,
      }
    }
    // before 没有可切分段，全部归入 pending
    return { completed: [], pending: normalized }
  }

  // 所有代码块已闭合，正常按 \n\n 切分
  const parts = normalized.split('\n\n')
  if (parts.length > 1) {
    return {
      completed: parts.slice(0, -1).filter(p => p.trim()),
      pending: parts[parts.length - 1] || '',
    }
  }

  return { completed: [], pending: normalized }
}

// ============================================================
// 消息级缓存 & getBubbleHtml
// ============================================================

// 已完成消息的渲染缓存
const _cache = new WeakMap()

// 流式消息上的解析状态（WeakMap 避免污染响应式对象）
const _stateMap = new WeakMap()

function _getState(msg) {
  let s = _stateMap.get(msg)
  if (!s) {
    s = {
      /** @type {Map<string, string>} block 文本 → marked 渲染 HTML 缓存 */
      blockCache: new Map(),
      /** @type {string[]} 已确认完成的 block 文本 */
      completedTexts: [],
      /** @type {string} 已拼接好的完成块 HTML */
      completedHtml: '',
    }
    _stateMap.set(msg, s)
  }
  return s
}

/**
 * 获取消息气泡的 HTML：
 * - 用户消息 → 纯文本
 * - AI 流式消息 → 块级增量：已完成块用 marked 渲染（缓存），
 *   未完成块仅在语法稳定时走 marked，否则用纯文本占位
 * - AI 已完成消息 → 全量 marked + DOMPurify + 缓存
 */
export function getBubbleHtml(msg, index, isLoading, lastIndex) {
  if (!msg.content) return ''
  if (msg.role === 'user') return escapeHtml(msg.content).replace(/\n/g, '<br>')

  // ---- 流式生成中的最后一条：块级增量渲染 ----
  if (isLoading && index === lastIndex) {
    const text = msg.content
    const state = _getState(msg)

    // 按 \n\n 切分
    const { completed, pending } = _splitBlocks(text)

    // ---- 已完成块：增量渲染（新块才走 marked） ----
    if (completed.length > state.completedTexts.length) {
      for (let i = state.completedTexts.length; i < completed.length; i++) {
        const blockText = completed[i]
        let html = state.blockCache.get(blockText)
        if (html === undefined) {
          html = renderMarkdown(blockText, false)
          state.blockCache.set(blockText, html)
        }
        state.completedHtml += html
      }
      state.completedTexts = completed
    }

    // ---- 未完成块（pending） ----
    let pendingHtml = ''
    if (pending) {
      if (_hasTrailingUnclosedSyntax(pending)) {
        // 语法不稳定 → 完全隐藏，等语法闭合后再出现
        // 绝不显示原始 markdown 字符（**, `, ```, [text](url）
        // 如果没有任何已完成块，下方会追加一个打字指示器
      } else {
        // 语法稳定 → 直接走 marked（结构不会再突变）
        pendingHtml = renderMarkdown(pending, false)
      }
    }

    // 没有已完成块且 pending 被隐藏 → 显示打字指示器，让用户知道正在生成
    if (!state.completedHtml && !pendingHtml) {
      return '<span class="typing-indicator"><i></i><i></i><i></i></span>'
    }

    return state.completedHtml + pendingHtml
  }

  // ---- 已完成消息：清理流式状态，走全量缓存 ----
  if (_stateMap.has(msg)) {
    _stateMap.delete(msg)
  }

  const entry = _cache.get(msg)
  if (entry && entry.raw === msg.content) {
    return entry.html
  }
  const html = renderMarkdown(msg.content, true)
  _cache.set(msg, { raw: msg.content, html })
  return html
}
