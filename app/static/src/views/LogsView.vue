<template>
  <TerminalLayout>
    <div class="fade-in">
      <div class="flex justify-between items-center mb-6">
        <h2 class="text-xl font-bold glow-text">请求记录</h2>
        <div class="flex gap-2">
          <select v-model="filterToken" @change="loadLogs(1)" class="form-input">
            <option value="">所有令牌</option>
            <option v-for="t in allTokens" :key="t.id" :value="t.id">{{ t.name }}</option>
          </select>
          <select v-model="filterModel" @change="loadLogs(1)" class="form-input">
            <option value="">所有模型</option>
            <option v-for="m in allModels" :key="m" :value="m">{{ m }}</option>
          </select>
        </div>
      </div>

      <!-- 日志卡片列表 - 参考 octopus LogCard -->
      <div class="space-y-3">
        <div
          v-for="(log, index) in logs"
          :key="log.id"
          class="log-card"
          :class="{ 'has-error': log.status !== 1 }"
          :style="{ animationDelay: `${index * 0.03}s` }"
          @click="showDetail(log.id)"
        >
          <div class="p-4">
            <div class="flex items-start gap-4">
              <!-- 模型标识 -->
              <div class="model-avatar" :class="getModelColor(log.model)">
                <span>{{ getModelInitial(log.model) }}</span>
              </div>

              <div class="flex-1 min-w-0">
                <!-- 头部信息 -->
                <div class="flex items-center gap-2 mb-2 flex-wrap">
                  <span class="text-sm font-semibold truncate">{{ log.model }}</span>
                  <span class="text-xs opacity-40">→</span>
                  <span class="text-xs opacity-70">{{ log.channel_name || `渠道#${log.channel_id}` }}</span>
                  <span
                    class="status-badge"
                    :class="log.status === 1 ? 'bg-green-900/30 text-green-400' : 'bg-red-900/30 text-red-400'"
                  >
                    {{ log.status === 1 ? '成功' : '失败' }}
                  </span>
                </div>

                <!-- 指标行 -->
                <div class="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs text-muted">
                  <div class="flex items-center gap-1.5">
                    <span class="text-green-400 opacity-60">◈</span>
                    <span>{{ formatDateTime(log.created_at) }}</span>
                  </div>
                  <div class="flex items-center gap-1.5">
                    <span class="text-green-400 opacity-60">▸</span>
                    <span>首字 {{ log.first_token_ms > 0 ? formatDuration(log.first_token_ms) : '-' }}</span>
                  </div>
                  <div class="flex items-center gap-1.5">
                    <span class="text-green-400 opacity-60">◇</span>
                    <span>输入 {{ log.prompt_tokens?.toLocaleString() || 0 }}</span>
                  </div>
                  <div class="flex items-center gap-1.5">
                    <span class="text-green-400 opacity-60">▣</span>
                    <span>输出 {{ log.completion_tokens?.toLocaleString() || 0 }}</span>
                  </div>
                </div>

                <!-- 错误信息 -->
                <div v-if="log.error_msg" class="mt-2 p-2 rounded bg-red-900/20 border border-red-900/30">
                  <p class="text-xs text-red-400 line-clamp-2">{{ log.error_msg }}</p>
                </div>
              </div>

              <!-- 操作 -->
              <div class="flex gap-1 flex-shrink-0">
                <button class="icon-btn" @click.stop="showDetail(log.id)">
                  <span>▤</span>
                </button>
                <button class="icon-btn" @click.stop="replayLog(log.id)">
                  <span>↻</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div v-if="logs.length === 0" class="text-center py-12 opacity-50">
        暂无请求记录
      </div>

      <!-- Pagination -->
      <div v-if="totalPages > 1" class="flex justify-between items-center mt-4 text-xs">
        <div class="opacity-70">第 {{ currentPage }} / {{ totalPages }} 页，共 {{ total }} 条</div>
        <div class="flex gap-1">
          <TerminalButton
            v-if="currentPage > 1"
            size="sm"
            @click="loadLogs(currentPage - 1)"
          >
            上一页
          </TerminalButton>
          <TerminalButton
            v-for="p in pageRange"
            :key="p"
            size="sm"
            :variant="p === currentPage ? 'default' : 'ghost'"
            @click="loadLogs(p)"
          >
            {{ p }}
          </TerminalButton>
          <TerminalButton
            v-if="currentPage < totalPages"
            size="sm"
            @click="loadLogs(currentPage + 1)"
          >
            下一页
          </TerminalButton>
        </div>
      </div>
    </div>

    <!-- Detail Modal - 参考 octopus MorphingDialogContent -->
    <TerminalModal v-model="showDetailModal" title="请求详情" size="lg">
      <!-- Loading state -->
      <div v-if="!detail" class="flex items-center justify-center py-12">
        <div class="loading-spinner"></div>
        <span class="ml-3 text-sm text-dim">加载中...</span>
      </div>
      <div v-if="detail" class="space-y-4">
        <!-- 头部信息 -->
        <div class="flex items-center gap-3 pb-3 border-b border-green-900/20">
          <div class="model-avatar" :class="getModelColor(detail.model)">
            <span>{{ getModelInitial(detail.model) }}</span>
          </div>
          <div>
            <div class="text-sm font-semibold">{{ detail.model }}</div>
            <div class="text-xs opacity-60">{{ detail.channel_name }} · {{ formatDateTime(detail.created_at) }}</div>
          </div>
          <span
            class="status-badge ml-auto"
            :class="detail.status === 1 ? 'bg-green-900/30 text-green-400' : 'bg-red-900/30 text-red-400'"
          >
            {{ detail.status === 1 ? '成功' : '失败' }}
          </span>
        </div>

        <!-- 指标网格 -->
        <div class="grid grid-cols-2 md:grid-cols-3 gap-3">
          <div class="detail-metric">
            <div class="text-xs opacity-60">总用时</div>
            <div class="text-sm font-mono">{{ formatDuration(detail.duration_ms) }}</div>
          </div>
          <div class="detail-metric">
            <div class="text-xs opacity-60">首字时间</div>
            <div class="text-sm font-mono">{{ detail.first_token_ms > 0 ? formatDuration(detail.first_token_ms) : '-' }}</div>
          </div>
          <div class="detail-metric">
            <div class="text-xs opacity-60">输入 Tokens</div>
            <div class="text-sm font-mono">{{ detail.prompt_tokens?.toLocaleString() || 0 }}</div>
          </div>
          <div class="detail-metric">
            <div class="text-xs opacity-60">输出 Tokens</div>
            <div class="text-sm font-mono">{{ detail.completion_tokens?.toLocaleString() || 0 }}</div>
          </div>
          <div class="detail-metric">
            <div class="text-xs opacity-60">令牌</div>
            <div class="text-sm font-mono">{{ detail.token_name }}</div>
          </div>
          <div class="detail-metric">
            <div class="text-xs opacity-60">上游模型</div>
            <div class="text-sm font-mono">{{ detail.upstream_model || '-' }}</div>
          </div>
        </div>

        <!-- 请求/响应内容 -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div class="content-panel">
            <div class="content-header">
              <span class="text-green-400">▸</span>
              <span class="text-sm font-medium">请求体</span>
              <span class="text-xs opacity-50 ml-auto">{{ detail.prompt_tokens?.toLocaleString() || 0 }} tokens</span>
            </div>
            <div class="content-body">
              <pre v-if="detail.request_body" class="text-xs font-mono whitespace-pre-wrap">{{ detail.request_body }}</pre>
              <p v-else class="text-xs opacity-50 text-center py-4">无请求内容</p>
            </div>
          </div>

          <div class="content-panel">
            <div class="content-header">
              <span class="text-green-400">◈</span>
              <span class="text-sm font-medium">响应体</span>
              <span class="text-xs opacity-50 ml-auto">{{ detail.completion_tokens?.toLocaleString() || 0 }} tokens</span>
            </div>
            <div class="content-body">
              <pre v-if="detail.response_body" class="text-xs font-mono whitespace-pre-wrap">{{ detail.response_body }}</pre>
              <p v-else class="text-xs opacity-50 text-center py-4">无响应内容</p>
            </div>
          </div>
        </div>

        <!-- 错误信息 -->
        <div v-if="detail.error_msg" class="p-3 rounded-lg bg-red-900/20 border border-red-900/30">
          <div class="text-xs font-medium text-red-400 mb-1">错误信息</div>
          <p class="text-xs text-red-400/80 whitespace-pre-wrap">{{ detail.error_msg }}</p>
        </div>
      </div>
      <template #footer>
        <TerminalButton @click="showDetailModal = false">关闭</TerminalButton>
      </template>
    </TerminalModal>

    <!-- Replay Result Modal -->
    <TerminalModal v-model="showReplayModal" title="重放结果" size="lg">
      <div v-if="replayResult" class="space-y-4">
        <div class="flex items-center gap-2">
          <span
            class="text-xl"
            :class="replayResult.success ? 'text-green-400' : 'text-red-400'"
          >
            {{ replayResult.success ? '✓' : '✗' }}
          </span>
          <span class="font-bold" :class="replayResult.success ? 'text-green-400' : 'text-red-400'">
            {{ replayResult.message }}
          </span>
        </div>
        <div v-if="replayResult.response" class="space-y-2">
          <div class="text-xs font-bold text-green-400">响应数据</div>
          <pre class="p-3 bg-black/30 rounded text-xs font-mono overflow-x-auto max-h-80">{{
            JSON.stringify(replayResult.response, null, 2)
          }}</pre>
        </div>
      </div>
      <template #footer>
        <TerminalButton @click="showReplayModal = false">关闭</TerminalButton>
      </template>
    </TerminalModal>
  </TerminalLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import TerminalLayout from '@/components/TerminalLayout.vue'
import TerminalModal from '@/components/TerminalModal.vue'
import TerminalButton from '@/components/TerminalButton.vue'
import { getLogs, getLogDetail, replayLog as apiReplayLog, getTokens, getChannels } from '@/api'
import type { RequestLog, Token } from '@/types'
import { formatDuration, formatDateTime } from '@/utils'

const logs = ref<RequestLog[]>([])
const allTokens = ref<Token[]>([])
const allModels = ref<string[]>([])
const filterToken = ref('')
const filterModel = ref('')
const currentPage = ref(1)
const totalPages = ref(1)
const total = ref(0)

const showDetailModal = ref(false)
const showReplayModal = ref(false)
const detail = ref<RequestLog | null>(null)
const replayResult = ref<any>(null)

const pageRange = computed(() => {
  const range: number[] = []
  const start = Math.max(1, currentPage.value - 2)
  const end = Math.min(totalPages.value, currentPage.value + 2)
  for (let i = start; i <= end; i++) range.push(i)
  return range
})

// 模型颜色映射
const modelColorMap: Record<string, string> = {
  'gpt-4': 'bg-blue-900/50 text-blue-400',
  'gpt-4o': 'bg-blue-900/50 text-blue-400',
  'gpt-3.5': 'bg-green-900/50 text-green-400',
  'claude': 'bg-orange-900/50 text-orange-400',
  'gemini': 'bg-purple-900/50 text-purple-400',
  'default': 'bg-gray-800 text-gray-400'
}

function getModelColor(model: string): string {
  const key = Object.keys(modelColorMap).find(k => model?.toLowerCase().includes(k))
  return key ? modelColorMap[key] : modelColorMap.default
}

function getModelInitial(model: string): string {
  if (!model) return '?'
  const parts = model.split(/[-/]/)
  return parts[0]?.charAt(0).toUpperCase() || '?'
}

async function loadLogs(page = 1) {
  try {
    currentPage.value = page
    const res = await getLogs(
      page,
      20,
      filterToken.value ? Number(filterToken.value) : undefined,
      filterModel.value || undefined
    )
    logs.value = res.data.items
    total.value = res.data.total
    totalPages.value = res.data.pages
  } catch (e: any) {
    console.error('加载日志失败:', e)
  }
}

async function loadFilters() {
  const [tokensRes, channelsRes] = await Promise.all([getTokens(), getChannels()])
  allTokens.value = tokensRes.data
  const models = new Set<string>()
  channelsRes.data.forEach((c: any) => {
    c.models?.forEach((m: string) => models.add(m))
  })
  allModels.value = Array.from(models).sort()
}

async function showDetail(id: number) {
  detail.value = null
  showDetailModal.value = true
  try {
    const res = await getLogDetail(id)
    detail.value = res.data
  } catch (e: any) {
    console.error('加载详情失败:', e)
  }
}

async function replayLog(id: number) {
  try {
    const res = await apiReplayLog(id)
    replayResult.value = res
    showReplayModal.value = true
  } catch (e: any) {
    alert('重放失败: ' + (e.response?.data?.detail || e.message))
  }
}

onMounted(() => {
  loadLogs()
  loadFilters()
})
</script>

<style scoped>
/* 日志卡片 - 参考 octopus LogCard */
.log-card {
  background: rgba(0, 20, 5, 0.6);
  border: 1px solid rgba(0, 255, 65, 0.1);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  animation: cardFadeIn 0.3s ease-out both;
}

.log-card:hover {
  border-color: rgba(0, 255, 65, 0.25);
  background: rgba(0, 30, 10, 0.7);
}

.log-card.has-error {
  border-color: rgba(255, 80, 80, 0.2);
}

.log-card.has-error:hover {
  border-color: rgba(255, 80, 80, 0.35);
}

@keyframes cardFadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 模型头像 */
.model-avatar {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: bold;
  flex-shrink: 0;
}

/* 状态徽章 */
.status-badge {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
}

/* 图标按钮 */
.icon-btn {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  background: rgba(0, 30, 10, 0.4);
  border: 1px solid rgba(0, 255, 65, 0.1);
  color: rgba(0, 255, 65, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 12px;
}

.icon-btn:hover {
  background: rgba(0, 50, 20, 0.5);
  border-color: rgba(0, 255, 65, 0.25);
}

/* 详情指标 */
.detail-metric {
  background: rgba(0, 30, 10, 0.4);
  border-radius: 8px;
  padding: 10px 12px;
}

/* 内容面板 */
.content-panel {
  background: rgba(0, 15, 5, 0.5);
  border: 1px solid rgba(0, 255, 65, 0.1);
  border-radius: 10px;
  overflow: hidden;
}

.content-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-bottom: 1px solid rgba(0, 255, 65, 0.1);
  background: rgba(0, 30, 10, 0.3);
}

.content-body {
  padding: 12px;
  max-height: 300px;
  overflow: auto;
}

.content-body pre {
  color: rgba(0, 255, 65, 0.8);
  line-height: 1.5;
}

/* 表单输入 */
.form-input {
  background: rgba(0, 20, 5, 0.6);
  border: 1px solid rgba(0, 255, 65, 0.15);
  border-radius: 8px;
  padding: 6px 12px;
  color: white;
  font-family: inherit;
  font-size: 14px;
  outline: none;
  transition: all 0.2s ease;
}

.form-input:focus {
  border-color: rgba(0, 255, 65, 0.4);
  box-shadow: 0 0 12px rgba(0, 255, 65, 0.15);
}

/* 文字发光 */
.glow-text {
  color: #00ff41;
  text-shadow: 0 0 6px rgba(0, 255, 65, 0.3);
}

/* 文本颜色 */
.text-muted {
  color: rgba(0, 255, 65, 0.6);
}

/* 行数限制 */
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.loading-spinner {
  width: 24px; height: 24px;
  border: 2px solid var(--border);
  border-top-color: var(--green);
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* 滚动条 */
::-webkit-scrollbar {
  width: 4px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: rgba(0, 255, 65, 0.2);
  border-radius: 2px;
}
</style>
