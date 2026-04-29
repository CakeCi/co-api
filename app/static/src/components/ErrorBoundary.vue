<template>
  <div v-if="hasError" class="error-boundary">
    <div class="error-content">
      <div class="error-icon">!</div>
      <h2 class="error-title">{{ title }}</h2>
      <p class="error-message">{{ errorMessage }}</p>
      <div v-if="showDetails && errorDetails" class="error-details">
        <pre>{{ errorDetails }}</pre>
      </div>
      <div class="error-actions">
        <TerminalButton variant="primary" @click="handleRetry">
          {{ retryText }}
        </TerminalButton>
        <TerminalButton v-if="showDetails" variant="ghost" @click="showDetails = !showDetails">
          {{ showDetails ? '隐藏详情' : '查看详情' }}
        </TerminalButton>
      </div>
    </div>
  </div>
  <slot v-else />
</template>

<script setup lang="ts">
import { ref, onErrorCaptured, onMounted } from 'vue'
import TerminalButton from './TerminalButton.vue'

interface Props {
  title?: string
  retryText?: string
  fallback?: (error: Error) => void
}

const props = withDefaults(defineProps<Props>(), {
  title: '页面出现错误',
  retryText: '重新加载'
})

const hasError = ref(false)
const errorMessage = ref('')
const errorDetails = ref('')
const showDetails = ref(false)

onErrorCaptured((err: Error) => {
  hasError.value = true
  errorMessage.value = err.message || '未知错误'
  errorDetails.value = err.stack || ''
  
  // 上报错误
  console.error('[ErrorBoundary]', err)
  
  // 如果有自定义处理函数
  if (props.fallback) {
    props.fallback(err)
  }
  
  return false
})

onMounted(() => {
  // 监听全局错误
  const handler = (event: ErrorEvent) => {
    hasError.value = true
    errorMessage.value = event.message || '全局错误'
    errorDetails.value = event.error?.stack || ''
    console.error('[GlobalError]', event)
  }
  
  window.addEventListener('error', handler)
  
  return () => {
    window.removeEventListener('error', handler)
  }
})

function handleRetry() {
  hasError.value = false
  errorMessage.value = ''
  errorDetails.value = ''
  window.location.reload()
}
</script>

<style scoped>
.error-boundary {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  padding: 24px;
}

.error-content {
  text-align: center;
  max-width: 500px;
}

.error-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.error-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 12px;
}

.error-message {
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 24px;
  line-height: 1.6;
}

.error-details {
  background: rgba(255, 0, 0, 0.05);
  border: 1px solid rgba(255, 0, 0, 0.2);
  border-radius: 4px;
  padding: 12px;
  margin-bottom: 24px;
  text-align: left;
  overflow-x: auto;
}

.error-details pre {
  font-size: 12px;
  color: #ff6b6b;
  white-space: pre-wrap;
  word-break: break-all;
}

.error-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
}
</style>
