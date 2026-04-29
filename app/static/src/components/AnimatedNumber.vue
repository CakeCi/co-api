<template>
  <span class="animated-number">{{ displayValue }}</span>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'

const props = defineProps<{
  value: number
  duration?: number
  prefix?: string
  suffix?: string
}>()

const displayValue = ref('0')
let animationFrame: number | null = null

function animateNumber(target: number, duration: number = 1000) {
  if (animationFrame) {
    cancelAnimationFrame(animationFrame)
  }

  const start = performance.now()
  const from = parseInt(displayValue.value.replace(/[^0-9]/g, '')) || 0

  function update(currentTime: number) {
    const elapsed = currentTime - start
    const progress = Math.min(elapsed / duration, 1)

    // easeOutExpo
    const easeProgress = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress)
    const current = Math.round(from + (target - from) * easeProgress)

    displayValue.value = (props.prefix || '') + current.toLocaleString() + (props.suffix || '')

    if (progress < 1) {
      animationFrame = requestAnimationFrame(update)
    }
  }

  animationFrame = requestAnimationFrame(update)
}

watch(() => props.value, (newValue) => {
  animateNumber(newValue, props.duration || 800)
}, { immediate: false })

onMounted(() => {
  animateNumber(props.value, props.duration || 800)
})
</script>

<style scoped>
.animated-number {
  font-variant-numeric: tabular-nums;
}
</style>
