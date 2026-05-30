import { ref } from 'vue'

const visible = ref(false)
const dialogMessage = ref('')
const dialogTitle = ref('确认')
const dialogType = ref('warning')
let pendingResolve = null

export function useConfirm() {
  function confirm(message, options = {}) {
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
