<template>
  <div class="toast-container">
    <transition-group name="toast">
      <div
        v-for="toast in toasts"
        :key="toast.id"
        class="toast-item"
        :class="toast.type"
      >
        <span class="toast-icon">{{ toastIcon(toast.type) }}</span>
        <span class="toast-message">{{ toast.message }}</span>
        <button class="toast-close" @click="remove(toast.id)">×</button>
      </div>
    </transition-group>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

interface Toast {
  id: number
  message: string
  type: 'success' | 'error' | 'warning' | 'info'
}

const toasts = ref<Toast[]>([])
let nextId = 0

function toastIcon(type: string): string {
  const icons = { success: '✓', error: '✗', warning: '⚠', info: 'ℹ' }
  return icons[type as keyof typeof icons] || 'ℹ'
}

function add(message: string, type: Toast['type'] = 'info', duration = 3000) {
  const id = nextId++
  toasts.value.push({ id, message, type })
  setTimeout(() => remove(id), duration)
}

function remove(id: number) {
  const index = toasts.value.findIndex(t => t.id === id)
  if (index > -1) toasts.value.splice(index, 1)
}

function success(message: string, duration?: number) {
  add(message, 'success', duration)
}

function error(message: string, duration?: number) {
  add(message, 'error', duration)
}

function warning(message: string, duration?: number) {
  add(message, 'warning', duration)
}

function info(message: string, duration?: number) {
  add(message, 'info', duration)
}

defineExpose({ success, error, warning, info, add })
</script>

<style scoped>
.toast-container {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.toast-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  border: 1px solid;
  background: #0a0f0a;
  min-width: 280px;
  max-width: 400px;
  animation: slideIn 0.3s ease;
}

.toast-item.success {
  border-color: #00ff41;
  color: #00ff41;
}

.toast-item.error {
  border-color: #ff4444;
  color: #ff4444;
}

.toast-item.warning {
  border-color: #ffaa00;
  color: #ffaa00;
}

.toast-item.info {
  border-color: #00aaff;
  color: #00aaff;
}

.toast-icon {
  font-size: 16px;
  font-weight: bold;
}

.toast-message {
  flex: 1;
  font-size: 13px;
}

.toast-close {
  background: none;
  border: none;
  color: inherit;
  cursor: pointer;
  font-size: 18px;
  opacity: 0.7;
}

.toast-close:hover {
  opacity: 1;
}

@keyframes slideIn {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}

.toast-enter-from,
.toast-leave-to {
  transform: translateX(100%);
  opacity: 0;
}
</style>
