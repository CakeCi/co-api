<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="loadingStore.isLoading" class="global-loader">
        <div class="loader-content">
          <div class="spinner">
            <div class="spinner-ring"></div>
            <div class="spinner-ring"></div>
            <div class="spinner-ring"></div>
          </div>
          <div class="loader-message">
            {{ loadingStore.currentTask?.message || '加载中...' }}
          </div>
          <div v-if="loadingStore.currentTask?.progress !== undefined" class="progress-bar">
            <div 
              class="progress-fill" 
              :style="{ width: `${loadingStore.currentTask.progress}%` }"
            ></div>
            <span class="progress-text">{{ loadingStore.currentTask.progress }}%</span>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { useLoadingStore } from '@/stores/loading'

const loadingStore = useLoadingStore()
</script>

<style scoped>
.global-loader {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}

.loader-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.spinner {
  position: relative;
  width: 64px;
  height: 64px;
}

.spinner-ring {
  position: absolute;
  width: 100%;
  height: 100%;
  border: 3px solid transparent;
  border-top-color: var(--primary-green);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.spinner-ring:nth-child(2) {
  width: 80%;
  height: 80%;
  top: 10%;
  left: 10%;
  animation-delay: -0.2s;
  border-top-color: var(--primary-cyan);
}

.spinner-ring:nth-child(3) {
  width: 60%;
  height: 60%;
  top: 20%;
  left: 20%;
  animation-delay: -0.4s;
  border-top-color: var(--primary-yellow);
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.loader-message {
  color: var(--text-primary);
  font-size: 14px;
  font-weight: 500;
}

.progress-bar {
  width: 200px;
  height: 4px;
  background: var(--bg-tertiary);
  border-radius: 2px;
  overflow: hidden;
  position: relative;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--primary-green), var(--primary-cyan));
  border-radius: 2px;
  transition: width 0.3s ease;
}

.progress-text {
  position: absolute;
  top: 8px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 12px;
  color: var(--text-secondary);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
