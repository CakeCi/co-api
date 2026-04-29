<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="isOpen" class="global-search-overlay" @click="close">
        <div class="global-search-modal" @click.stop
>
          <div class="search-header">
            <div class="search-input-wrapper">
              <span class="search-icon">?</span>
              <input
                ref="inputRef"
                v-model="query"
                type="text"
                placeholder="搜索..."
                class="search-input"
                @keydown.down.prevent="navigateDown"
                @keydown.up.prevent="navigateUp"
                @keydown.enter.prevent="selectCurrent"
                @keydown.esc.prevent="close"
              />
              <span class="shortcut-hint">ESC 关闭</span>
            </div>
          </div>
          
          <div class="search-results">
            <div v-if="loading" class="results-loading">
              <Skeleton v-for="i in 5" :key="i" height="40" />
            </div>
            
            <div v-else-if="!query" class="results-empty">
              <div class="recent-searches" v-if="recentSearches.length > 0">
                <div class="section-title">最近搜索</div>
                <div
                  v-for="(item, index) in recentSearches"
                  :key="index"
                  class="result-item"
                  @click="selectRecent(item)"
                >
                  <span class="result-icon">T</span>
                  <span class="result-text">{{ item }}</span>
                </div>
              </div>
              
              <div class="quick-actions">
                <div class="section-title">快捷操作</div>
                <div
                  v-for="action in quickActions"
                  :key="action.key"
                  class="result-item"
                  :class="{ active: selectedIndex === action.index }"
                  @click="executeAction(action)"
                  @mouseenter="selectedIndex = action.index"
                >
                  <span class="result-icon">{{ action.icon }}</span>
                  <span class="result-text">{{ action.label }}</span>
                  <span class="result-shortcut">{{ action.shortcut }}</span>
                </div>
              </div>
            </div>
            
            <div v-else-if="results.length === 0" class="results-empty">
              <div class="empty-state">
                <div class="empty-icon">?</div>
                <div class="empty-text">未找到 "{{ query }}" 相关结果</div>
              </div>
            </div>
            
            <div v-else class="results-list">
              <div
                v-for="(result, index) in results"
                :key="result.id"
                class="result-item"
                :class="{ active: selectedIndex === index }"
                @click="selectResult(result)"
                @mouseenter="selectedIndex = index"
              >
                <span class="result-icon">{{ result.icon || 'F' }}</span>
                <div class="result-content">
                  <div class="result-title" v-html="highlightText(result.title)"></div>
                  <div class="result-description" v-if="result.description">
                    {{ result.description }}
                  </div>
                </div>
                <span class="result-category">{{ result.category }}</span>
              </div>
            </div>
          </div>
          
          <div class="search-footer">
            <div class="footer-hints">
              <span>↑↓ 导航</span>
              <span>↵ 选择</span>
              <span>ESC 关闭</span>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import Skeleton from './Skeleton.vue'

export interface SearchResult {
  id: string
  title: string
  description?: string
  icon?: string
  category: string
  path?: string
  action?: () => void
}

interface Props {
  results?: SearchResult[]
  loading?: boolean
  recentSearches?: string[]
}

const props = withDefaults(defineProps<Props>(), {
  results: () => [],
  loading: false,
  recentSearches: () => []
})

const emit = defineEmits<{
  (e: 'search', query: string): void
  (e: 'select', result: SearchResult): void
}>()

const router = useRouter()
const isOpen = ref(false)
const query = ref('')
const inputRef = ref<HTMLInputElement>()
const selectedIndex = ref(0)

const quickActions = [
  { key: 'channels', icon: '▸', label: '渠道管理', shortcut: 'G C', path: '/channels', index: 0 },
  { key: 'pools', icon: '◆', label: '连接池', shortcut: 'G P', path: '/pools', index: 1 },
  { key: 'tokens', icon: '◇', label: 'Token管理', shortcut: 'G T', path: '/tokens', index: 2 },
  { key: 'logs', icon: '▬', label: '请求日志', shortcut: 'G L', path: '/logs', index: 3 },
  { key: 'dashboard', icon: '■', label: '仪表盘', shortcut: 'G D', path: '/', index: 4 }
]

const allResults = computed(() => {
  if (!query.value) return quickActions
  return props.results
})

watch(query, (newQuery) => {
  selectedIndex.value = 0
  if (newQuery) {
    emit('search', newQuery)
  }
})

function open() {
  isOpen.value = true
  query.value = ''
  selectedIndex.value = 0
  nextTick(() => {
    inputRef.value?.focus()
  })
}

function close() {
  isOpen.value = false
}

function navigateDown() {
  if (selectedIndex.value < allResults.value.length - 1) {
    selectedIndex.value++
  }
}

function navigateUp() {
  if (selectedIndex.value > 0) {
    selectedIndex.value--
  }
}

function selectCurrent() {
  const current = allResults.value[selectedIndex.value]
  if (current) {
    if ('path' in current && current.path) {
      router.push(current.path)
      close()
    } else if ('action' in current && current.action) {
      current.action()
      close()
    } else {
      emit('select', current as SearchResult)
    }
  }
}

function selectResult(result: SearchResult) {
  if (result.path) {
    router.push(result.path)
    close()
  } else if (result.action) {
    result.action()
    close()
  } else {
    emit('select', result)
  }
}

function selectRecent(item: string) {
  query.value = item
  emit('search', item)
}

function executeAction(action: any) {
  if (action.path) {
    router.push(action.path)
    close()
  }
}

function highlightText(text: string): string {
  if (!query.value) return text
  const regex = new RegExp(`(${query.value})`, 'gi')
  return text.replace(regex, '<mark>$1</mark>')
}

// Expose methods
defineExpose({
  open,
  close
})
</script>

<style scoped>
.global-search-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding-top: 120px;
  z-index: 1000;
}

.global-search-modal {
  width: 100%;
  max-width: 640px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-secondary);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg), 0 0 40px rgba(0, 255, 65, 0.1);
  overflow: hidden;
}

.search-header {
  padding: 16px;
  border-bottom: 1px solid var(--border-muted);
}

.search-input-wrapper {
  display: flex;
  align-items: center;
  gap: 12px;
  background: var(--bg-primary);
  border: 1px solid var(--border-muted);
  border-radius: var(--radius-md);
  padding: 12px 16px;
  transition: all var(--transition-fast);
}

.search-input-wrapper:focus-within {
  border-color: var(--primary-green);
  box-shadow: 0 0 0 2px rgba(0, 255, 65, 0.2);
}

.search-icon {
  font-size: 18px;
  opacity: 0.6;
}

.search-input {
  flex: 1;
  background: transparent;
  border: none;
  color: var(--text-primary);
  font-size: 16px;
  font-family: inherit;
  outline: none;
}

.search-input::placeholder {
  color: var(--text-muted);
}

.shortcut-hint {
  font-size: 12px;
  color: var(--text-muted);
  background: var(--bg-tertiary);
  padding: 2px 6px;
  border-radius: var(--radius-sm);
}

.search-results {
  max-height: 400px;
  overflow-y: auto;
  padding: 8px;
}

.section-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  padding: 8px 12px;
}

.result-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.result-item:hover,
.result-item.active {
  background: var(--bg-hover);
}

.result-item.active {
  border-left: 2px solid var(--primary-green);
}

.result-icon {
  font-size: 18px;
  width: 24px;
  text-align: center;
}

.result-content {
  flex: 1;
  min-width: 0;
}

.result-title {
  font-size: 14px;
  color: var(--text-primary);
  font-weight: 500;
}

.result-title :deep(mark) {
  background: rgba(0, 255, 65, 0.3);
  color: var(--primary-green);
  border-radius: 2px;
  padding: 0 2px;
}

.result-description {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.result-category {
  font-size: 11px;
  color: var(--text-muted);
  background: var(--bg-tertiary);
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  white-space: nowrap;
}

.result-shortcut {
  font-size: 11px;
  color: var(--text-muted);
  background: var(--bg-tertiary);
  padding: 2px 6px;
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
}

.results-loading {
  padding: 8px;
}

.results-empty {
  padding: 24px;
  text-align: center;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  color: var(--text-secondary);
}

.empty-icon {
  font-size: 32px;
  opacity: 0.5;
}

.empty-text {
  font-size: 14px;
}

.search-footer {
  padding: 12px 16px;
  border-top: 1px solid var(--border-muted);
  background: var(--bg-tertiary);
}

.footer-hints {
  display: flex;
  gap: 16px;
  justify-content: center;
  font-size: 12px;
  color: var(--text-muted);
}

.footer-hints span {
  display: flex;
  align-items: center;
  gap: 4px;
}

/* Transitions */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
