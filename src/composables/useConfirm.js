import { ref } from 'vue'

const visible = ref(false)
const dialogMessage = ref('')
const dialogTitle = ref('确认')
const dialogType = ref('warning')
let pendingResolve = null

export function useConfirm() {
  function confirm(message, options = {}) {
    // 拒绝上一个未完成的 Promise，防止内存泄漏
    if (pendingResolve) {
      const prev = pendingResolve
      pendingResolve = null
      prev(false)
    }
    dialogMessage.value = message
    dialogTitle.value = options.title || '确认'
    dialogType.value = options.type || 'warning'
    visible.value = true
    return new Promise((resolve) => {
      pendingResolve = resolve
    })
  }

  function handleConfirm() {
    visible.value = false
    pendingResolve?.(true)
    pendingResolve = null
  }

  function handleCancel() {
    visible.value = false
    pendingResolve?.(false)
    pendingResolve = null
  }

  return {
    visible,
    dialogMessage,
    dialogTitle,
    dialogType,
    confirm,
    handleConfirm,
    handleCancel,
  }
}
