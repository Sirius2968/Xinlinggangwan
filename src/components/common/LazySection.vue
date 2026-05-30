<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'

const visible = ref(false)
const root = ref(null)
let observer = null

onMounted(() => {
  observer = new IntersectionObserver(
    ([entry]) => {
      if (entry.isIntersecting) {
        visible.value = true
      }
    },
    { rootMargin: '0px 0px 300px 0px' }
  )
  if (root.value) {
    observer.observe(root.value)
  }
})

onBeforeUnmount(() => {
  observer?.disconnect()
})
</script>

<template>
  <div ref="root" style="min-height: 1px">
    <slot v-if="visible" />
  </div>
</template>
