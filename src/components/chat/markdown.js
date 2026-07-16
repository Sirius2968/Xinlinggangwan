import { marked } from 'marked'
import DOMPurify from 'dompurify'

let _configured = false

function _ensureConfigured() {
  if (!_configured) {
    marked.setOptions({ breaks: true, gfm: true })
    _configured = true
  }
}

export function renderMarkdown(text, sanitize = true) {
  if (!text) return ''
  _ensureConfigured()
  const raw = marked.parse(text)
  return sanitize ? DOMPurify.sanitize(raw) : raw
}

export function escapeHtml(str) {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

// ============================================================
// 纯文本降级：去除 markdown 语法字符，保留下划线文字
// ============================================================
function _stripMarkdownSyntax(text) {
  return text
    .replace(/\*\*/g, '')
    .replace(/\*/g, '')
    .replace(/__/g, '')
    .replace(/~~/g, '')
    .replace(/`/g, '')
    .replace(/^#{1,6}\s/gm, '')
}

// ============================================================
// 综合未闭合语法检测（GFM 常用内联语法全覆盖）
// ============================================================

function _unpaired(regex, text) {
  return [...text.matchAll(regex)].length % 2 !== 0
}

export function hasTrailingUnclosedSyntax(text) {
  if (!text) return false
  const tail = text.slice(-120)

  // ** 粗体
  if (_unpaired(/\*\*/g, tail)) {
    const idx = tail.lastIndexOf('**')
    if (idx === -1 || !tail.slice(idx + 2).includes('**')) return true
  }

  // * 斜体（排除 ** 组成部分）
  if (_unpaired(/(?<!\*)\*(?!\*)/g, tail)) return true

  // __ 粗体（下划线）
  if (_unpaired(/__/g, tail)) {
    const idx = tail.lastIndexOf('__')
    if (idx === -1 || !tail.slice(idx + 2).includes('__')) return true
  }

  // _ 斜体（排除 __ 组成部分）
  if (_unpaired(/(?<!_)_(?!_)/g, tail)) return true

  // ~~ 删除线
  if (_unpaired(/~~/g, tail)) return true

  // ``` 代码块
  if (_unpaired(/```/g, tail)) return true

  // ` 行内代码（排除 ``` 组成部分）
  const allTicks = [...tail.matchAll(/`/g)].length
  const fenceTicks = [...tail.matchAll(/```/g)].length * 3
  if ((allTicks - fenceTicks) % 2 !== 0) return true

  // [text](url 未闭合链接
  if (/\[[^\]]*\]\([^)]*$/.test(tail)) return true

  return false
}

// ============================================================
// 块切分（\n\n 分隔，``` 代码块边界感知）
// ============================================================

function _splitBlocks(text) {
  const normalized = text.replace(/\r\n/g, '\n')

  const fencePositions = []
  let idx = -1
  while ((idx = normalized.indexOf('```', idx + 1)) !== -1) {
    fencePositions.push(idx)
  }

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
    return { completed: [], pending: normalized }
  }

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

const _cache = new WeakMap()
const _stateMap = new WeakMap()

function _getState(msg) {
  let s = _stateMap.get(msg)
  if (!s) {
    s = {
      blockCache: new Map(),
      completedTexts: [],
      completedHtml: '',
    }
    _stateMap.set(msg, s)
  }
  return s
}

export function getBubbleHtml(msg, index, isLoading, lastIndex) {
  if (!msg.content) return ''
  if (msg.role === 'user') return escapeHtml(msg.content).replace(/\n/g, '<br>')

  // ---- 流式最后一条：块级增量渲染 ----
  if (isLoading && index === lastIndex) {
    const text = msg.content
    const state = _getState(msg)
    const { completed, pending } = _splitBlocks(text)

    // 已完成块：增量 marked 渲染 + 缓存
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

    // 未完成块（pending）：语法稳定时 marked 渲染，不稳定时纯文本降级
    let pendingHtml = ''
    if (pending) {
      if (!hasTrailingUnclosedSyntax(pending)) {
        pendingHtml = renderMarkdown(pending, false)
      } else {
        // 纯文本降级：保持高度稳定，避免滚动抖动
        const plain = _stripMarkdownSyntax(pending).trim()
        if (plain) {
          pendingHtml = '<span class="streaming-plain">' + escapeHtml(plain) + '</span>'
        }
      }
    }

    if (!state.completedHtml && !pendingHtml) {
      return '<span class="typing-indicator"><i></i><i></i><i></i></span>'
    }

    return state.completedHtml + pendingHtml
  }

  // ---- 已完成消息 ----
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
