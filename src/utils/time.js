/**
 * 格式化时间为 MM-DD HH:MM 格式
 * 支持 Date 对象、ISO 字符串、时间戳
 */
export function formatTime(input) {
  if (!input) {
    const d = new Date()
    const mm = String(d.getMonth() + 1).padStart(2, '0')
    const dd = String(d.getDate()).padStart(2, '0')
    const hh = String(d.getHours()).padStart(2, '0')
    const mi = String(d.getMinutes()).padStart(2, '0')
    return `${mm}-${dd} ${hh}:${mi}`
  }
  if (input instanceof Date) return _format(input)
  if (typeof input === 'number') return _format(new Date(input))
  if (typeof input === 'string') {
    const d = new Date(input)
    if (!isNaN(d.getTime())) return _format(d)
    // 纯时间如 "09:30"
    const parts = input.split(':')
    if (parts.length >= 2) {
      const now = new Date()
      return _format(new Date(now.getFullYear(), now.getMonth(), now.getDate(), +parts[0], +parts[1]))
    }
  }
  return _format(new Date())
}

function _format(d) {
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  const hh = String(d.getHours()).padStart(2, '0')
  const mi = String(d.getMinutes()).padStart(2, '0')
  return `${mm}-${dd} ${hh}:${mi}`
}
