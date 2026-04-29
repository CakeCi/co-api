import { ref, computed } from 'vue'
import { defineStore } from 'pinia'

export interface LoadingTask {
  id: string
  message: string
  progress?: number
  cancellable?: boolean
}

export const useLoadingStore = defineStore('loading', () => {
  const tasks = ref<Map<string, LoadingTask>>(new Map())
  const globalMessage = ref('')
  
  const isLoading = computed(() => tasks.value.size > 0)
  const taskList = computed(() => Array.from(tasks.value.values()))
  const currentTask = computed(() => taskList.value[0])
  
  function startLoading(id: string, message: string = '加载中...') {
    tasks.value.set(id, { id, message })
  }
  
  function updateProgress(id: string, progress: number) {
    const task = tasks.value.get(id)
    if (task) {
      task.progress = Math.min(100, Math.max(0, progress))
    }
  }
  
  function stopLoading(id: string) {
    tasks.value.delete(id)
  }
  
  function setGlobalMessage(message: string) {
    globalMessage.value = message
  }
  
  function clearGlobalMessage() {
    globalMessage.value = ''
  }
  
  return {
    tasks,
    isLoading,
    taskList,
    currentTask,
    globalMessage,
    startLoading,
    updateProgress,
    stopLoading,
    setGlobalMessage,
    clearGlobalMessage
  }
})
