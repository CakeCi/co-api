<template>
  <button
    ref="btnRef"
    class="terminal-btn"
    :class="[variant, size, { 'btn-loading': loading, 'btn-pressed': isPressed }]"
    :disabled="disabled || loading"
    @click="handleClick"
    @mousedown="isPressed = true"
    @mouseup="isPressed = false"
    @mouseleave="isPressed = false"
    @touchstart="isPressed = true"
    @touchend="isPressed = false"
  >
    <span v-if="loading" class="btn-spinner">
      <svg class="spinner-icon" viewBox="0 0 24 24">
        <circle class="spinner-track" cx="12" cy="12" r="10" fill="none" stroke-width="3"/>
        <circle class="spinner-head" cx="12" cy="12" r="10" fill="none" stroke-width="3"/>
      </svg>
    </span>
    <span class="btn-content" :class="{ 'content-hidden': loading }">
      <slot />
    </span>
    <span class="ripple-container">
      <span
        v-for="ripple in ripples"
        :key="ripple.id"
        class="ripple"
        :style="{
          left: ripple.x + 'px',
          top: ripple.y + 'px',
          width: ripple.size + 'px',
          height: ripple.size + 'px'
        }"
        @animationend="removeRipple(ripple.id)"
      />
    </span>
  </button>
</template>

<script setup lang="ts">
import { ref } from 'vue'

interface Props {
  variant?: 'default' | 'danger' | 'ghost' | 'primary'
  size?: 'sm' | 'md' | 'lg'
  disabled?: boolean
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'default',
  size: 'md'
})

const emit = defineEmits<{
  (e: 'click', event: MouseEvent): void
}>()

const btnRef = ref<HTMLButtonElement>()
const isPressed = ref(false)
const ripples = ref<Array<{ id: number; x: number; y: number; size: number }>>([])
let rippleId = 0

function handleClick(event: MouseEvent) {
  if (props.loading || props.disabled) return
  
  // 创建涟漪效果
  const btn = btnRef.value
  if (btn) {
    const rect = btn.getBoundingClientRect()
    const size = Math.max(rect.width, rect.height) * 2
    const x = event.clientX - rect.left - size / 2
    const y = event.clientY - rect.top - size / 2
    
    ripples.value.push({ id: rippleId++, x, y, size })
  }
  
  emit('click', event)
}

function removeRipple(id: number) {
  const index = ripples.value.findIndex(r => r.id === id)
  if (index > -1) {
    ripples.value.splice(index, 1)
  }
}
</script>

<style scoped>
.terminal-btn {
  position: relative;
  background: transparent;
  color: var(--primary-green, #00ff41);
  border: 1px solid var(--primary-green, #00ff41);
  padding: 8px 20px;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  font-family: inherit;
  font-size: 14px;
  border-radius: 4px;
  overflow: hidden;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-height: 36px;
}

.terminal-btn:hover:not(:disabled) {
  background: var(--primary-green, #00ff41);
  color: var(--bg-primary, #050805);
  box-shadow: 0 0 16px rgba(0, 255, 65, 0.4), 0 4px 12px rgba(0, 255, 65, 0.2);
  transform: translateY(-1px);
}

.terminal-btn:active:not(:disabled),
.terminal-btn.btn-pressed:not(:disabled) {
  transform: translateY(0) scale(0.98);
  box-shadow: 0 0 8px rgba(0, 255, 65, 0.3);
}

.terminal-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Primary Variant */
.terminal-btn.primary {
  background: var(--primary-green, #00ff41);
  color: var(--bg-primary, #050805);
}

.terminal-btn.primary:hover:not(:disabled) {
  background: var(--primary-green-light, #33ff66);
  box-shadow: 0 0 20px rgba(0, 255, 65, 0.5), 0 4px 16px rgba(0, 255, 65, 0.3);
}

/* Danger Variant */
.terminal-btn.danger {
  border-color: #ff4444;
  color: #ff4444;
}

.terminal-btn.danger:hover:not(:disabled) {
  background: #ff4444;
  color: #050805;
  box-shadow: 0 0 16px rgba(255, 68, 68, 0.4), 0 4px 12px rgba(255, 68, 68, 0.2);
}

/* Ghost Variant */
.terminal-btn.ghost {
  border-color: transparent;
  color: rgba(0, 255, 65, 0.7);
  background: rgba(0, 255, 65, 0.05);
}

.terminal-btn.ghost:hover:not(:disabled) {
  background: rgba(0, 255, 65, 0.1);
  color: var(--primary-green, #00ff41);
  box-shadow: none;
  transform: none;
}

/* Size Variants */
.terminal-btn.sm {
  padding: 4px 12px;
  font-size: 12px;
  min-height: 28px;
}

.terminal-btn.lg {
  padding: 12px 28px;
  font-size: 16px;
  min-height: 44px;
}

/* Loading State */
.btn-loading {
  cursor: wait;
}

.btn-spinner {
  position: absolute;
  display: flex;
  align-items: center;
  justify-content: center;
}

.spinner-icon {
  width: 18px;
  height: 18px;
  animation: spinner-rotate 1s linear infinite;
}

.spinner-track {
  stroke: rgba(0, 255, 65, 0.2);
}

.spinner-head {
  stroke: currentColor;
  stroke-dasharray: 20, 80;
  stroke-dashoffset: 0;
  animation: spinner-dash 1.5s ease-in-out infinite;
}

.content-hidden {
  opacity: 0;
}

@keyframes spinner-rotate {
  to {
    transform: rotate(360deg);
  }
}

@keyframes spinner-dash {
  0% {
    stroke-dasharray: 1, 80;
    stroke-dashoffset: 0;
  }
  50% {
    stroke-dasharray: 40, 80;
    stroke-dashoffset: -20;
  }
  100% {
    stroke-dasharray: 40, 80;
    stroke-dashoffset: -60;
  }
}

/* Ripple Effect */
.ripple-container {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
  overflow: hidden;
  border-radius: inherit;
}

.ripple {
  position: absolute;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.3);
  animation: ripple-effect 0.6s ease-out;
  pointer-events: none;
}

@keyframes ripple-effect {
  0% {
    transform: scale(0);
    opacity: 0.5;
  }
  100% {
    transform: scale(1);
    opacity: 0;
  }
}
</style>
