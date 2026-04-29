<template>
  <TerminalLayout>
    <div class="fade-in">
      <div class="flex justify-between items-center mb-6">
        <h2 class="text-xl font-bold glow-text">上游渠道</h2>
        <div class="flex gap-2">
          <TerminalButton size="sm" @click="showImportModal = true">导入</TerminalButton>
          <TerminalButton size="sm" @click="handleExport">导出</TerminalButton>
          <TerminalButton @click="openCreateModal">+ 新建渠道</TerminalButton>
        </div>
      </div>

      <!-- 搜索和筛选 -->
      <div class="flex gap-3 mb-4">
        <input
          v-model="searchTerm"
          placeholder="搜索渠道..."
          class="form-input flex-1 max-w-xs"
        />
        <select v-model="statusFilter" class="form-input w-32">
          <option value="all">全部</option>
          <option value="enabled">启用</option>
          <option value="disabled">禁用</option>
        </select>
        <button
          class="view-toggle"
          :class="{ active: viewMode === 'grid' }"
          @click="viewMode = 'grid'"
        >
          ▦
        </button>
        <button
          class="view-toggle"
          :class="{ active: viewMode === 'list' }"
          @click="viewMode = 'list'"
        >
          ▤
        </button>
      </div>

      <!-- 卡片式布局 - 参考 octopus 的 Channel Card -->
      <div
        :class="viewMode === 'grid'
          ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4'
          : 'space-y-3'"
      >
        <div
          v-for="(ch, index) in filteredChannels"
          :key="ch.id"
          class="channel-card"
          :style="{ animationDelay: `${index * 0.05}s` }"
        >
          <!-- 头部 -->
          <div class="flex justify-between items-start mb-3">
            <div class="min-w-0 flex-1">
              <h3 class="text-sm font-bold truncate">{{ ch.name }}</h3>
              <p class="text-xs opacity-60 mt-1 truncate">{{ ch.base_url }}</p>
            </div>
            <!-- 开关 - 参考 octopus Switch -->
            <button
              class="toggle-switch"
              :class="{ enabled: ch.status === 1 }"
              @click="toggleChannel(ch)"
            >
              <span class="toggle-thumb"></span>
            </button>
          </div>

          <!-- 统计指标 - 参考 octopus 的 metrics -->
          <div class="metrics-grid" :class="viewMode">
            <div class="metric-item">
              <div class="flex items-center gap-1 text-xs opacity-60">
                <span class="text-green-400">◈</span>
                请求
              </div>
              <div class="text-sm font-mono font-semibold">
                {{ formatNumber(healthMap[ch.id]?.total_requests || 0) }}
              </div>
            </div>
            <div class="metric-item">
              <div class="flex items-center gap-1 text-xs opacity-60">
                <span class="text-green-400">▸</span>
                成功率
              </div>
              <div class="text-sm font-mono font-semibold">
                {{ healthMap[ch.id]?.success_rate?.toFixed(1) || 0 }}%
              </div>
            </div>
            <div class="metric-item">
              <div class="flex items-center gap-1 text-xs opacity-60">
                <span class="text-green-400">◇</span>
                模型
              </div>
              <div class="text-sm font-mono font-semibold">
                {{ ch.models?.length || 0 }}
              </div>
            </div>
            <div class="metric-item">
              <div class="flex items-center gap-1 text-xs opacity-60">
                <span class="text-green-400">▣</span>
                连续失败
              </div>
              <div
                class="text-sm font-mono font-semibold"
                :class="(healthMap[ch.id]?.consecutive_failures || 0) > 3 ? 'text-red-400' : ''"
              >
                {{ healthMap[ch.id]?.consecutive_failures || 0 }}
              </div>
            </div>
          </div>

          <!-- 模型列表 -->
          <div v-if="ch.models && ch.models.length > 0" class="mt-3 model-tags">
            <div class="flex flex-wrap gap-1">
              <span
                v-for="model in ch.models.slice(0, 3)"
                :key="model"
                class="model-tag"
              >
                {{ model }}
              </span>
              <span v-if="ch.models.length > 3" class="model-tag-more">
                +{{ ch.models.length - 3 }}
              </span>
            </div>
          </div>

          <!-- 操作按钮 -->
          <div class="flex gap-2 mt-3 pt-3 border-t border-green-900/20">
            <button class="action-btn" @click="editChannel(ch)">
              <span>编辑</span>
            </button>
            <button class="action-btn" @click="testChannel(ch.id)">
              <span>测试</span>
            </button>
            <button class="action-btn" @click="syncModels(ch.id)">
              <span>同步</span>
            </button>
            <button class="action-btn danger" @click="deleteChannel(ch.id)">
              <span>删除</span>
            </button>
          </div>
        </div>
      </div>

      <div v-if="filteredChannels.length === 0" class="text-center py-12 opacity-50">
        暂无渠道配置
      </div>

      <!-- Pagination -->
      <div v-if="totalPages > 1" class="flex justify-between items-center mt-4 text-xs">
        <div class="opacity-70">第 {{ currentPage }} / {{ totalPages }} 页，共 {{ total }} 条</div>
        <div class="flex gap-1">
          <TerminalButton
            v-if="currentPage > 1"
            size="sm"
            @click="loadChannels(currentPage - 1)"
          >
            上一页
          </TerminalButton>
          <TerminalButton
            v-for="p in pageRange"
            :key="p"
            size="sm"
            :variant="p === currentPage ? 'default' : 'ghost'"
            @click="loadChannels(p)"
          >
            {{ p }}
          </TerminalButton>
          <TerminalButton
            v-if="currentPage < totalPages"
            size="sm"
            @click="loadChannels(currentPage + 1)"
          >
            下一页
          </TerminalButton>
        </div>
      </div>
    </div>

    <!-- Create Modal -->
    <TerminalModal v-model="showModal" :title="editingId ? '编辑渠道' : '新建渠道'" size="md">
      <div class="space-y-4">
        <!-- 平台预设 (新建时显示卡片) -->
        <div v-if="!editingId">
          <label class="block text-xs text-dim mb-2">选择平台</label>
          <div class="grid grid-cols-2 md:grid-cols-3 gap-2">
            <button
              v-for="p in platformList"
              :key="p.key"
              class="platform-card"
              :class="{ selected: selectedPreset === p.key }"
              @click="onPresetSelect(p.key)"
            >
              <div class="text-base mb-1">{{ p.icon }}</div>
              <div class="text-xs">{{ p.label }}</div>
            </button>
            <button
              class="platform-card"
              :class="{ selected: selectedPreset === '' }"
              @click="onPresetSelect('')"
            >
              <div class="text-base mb-1">+</div>
              <div class="text-xs">手动配置</div>
            </button>
          </div>
        </div>

        <!-- 名称 -->
        <div>
          <label class="block text-xs text-dim mb-1">名称</label>
          <input v-model="form.name" class="form-input" placeholder="如: DeepSeek-Pro" />
        </div>

        <!-- API密钥 -->
        <div>
          <label class="block text-xs text-dim mb-1">API 密钥</label>
          <input v-model="form.api_key" type="password" class="form-input"
            :placeholder="editingId ? '留空不修改' : 'sk-xxxxxxxx'" />
        </div>

        <!-- 仅手动模式显示高级选项 -->
        <div v-if="!selectedPreset" class="space-y-3 pt-3 border-t border-green-900/10">
          <div>
            <label class="block text-xs text-dim mb-1">接口格式</label>
            <select v-model="form.api_type" class="form-input">
              <option value="openai">OpenAI Compatible</option>
              <option value="anthropic">Anthropic</option>
              <option value="gemini">Google (Gemini)</option>
            </select>
          </div>
          <div>
            <label class="block text-xs text-dim mb-1">基础地址</label>
            <input v-model="form.base_url" class="form-input" placeholder="https://api.openai.com" />
          </div>
      <div>
        <label class="block text-xs text-dim mb-1">模型 (逗号分隔)</label>
        <input v-model="form.models" class="form-input" placeholder="gpt-3.5-turbo,gpt-4" />
      </div>
      <div>
        <label class="block text-xs text-dim mb-1">思考强度选项 (逗号分隔)</label>
        <input v-model="form.reasoning_levels" class="form-input" placeholder="low,medium,high" />
        <p class="text-xs text-dim mt-1">支持 xhigh 的渠道可设为 low,medium,high,xhigh</p>
      </div>
        </div>

        <!-- 预设模式只显示只读信息 -->
        <div v-if="selectedPreset" class="text-xs text-soft flex items-center gap-2">
          <span>{{ presets[selectedPreset]?.base_url }}</span>
          <span>|</span>
          <span>{{ presets[selectedPreset]?.api_type }}</span>
          <span class="text-green">保存后自动同步模型</span>
        </div>
      </div>

      <template #footer>
        <TerminalButton @click="saveChannel" :disabled="saving">
          {{ saving ? '保存中...' : '保存' }}
        </TerminalButton>
        <TerminalButton variant="ghost" @click="showModal = false">取消</TerminalButton>
      </template>
    </TerminalModal>

    <!-- Import Modal -->
    <TerminalModal v-model="showImportModal" title="导入配置" size="md">
      <div class="space-y-3">
        <p class="text-sm opacity-80">粘贴 JSON 配置数据：</p>
        <textarea
          v-model="importData"
          class="form-input w-full h-48 font-mono text-xs"
          placeholder="{ ... }"
        />
      </div>
      <template #footer>
        <TerminalButton @click="handleImport">导入</TerminalButton>
        <TerminalButton variant="ghost" @click="showImportModal = false">取消</TerminalButton>
      </template>
    </TerminalModal>

    <!-- Test Result Modal -->
    <TerminalModal v-model="showTestModal" title="测试结果" size="lg">
      <div v-if="testResult" class="space-y-4">
        <div class="flex items-center gap-2">
          <span class="text-xl" :class="testResult.success ? 'text-green-400' : 'text-red-400'">
            {{ testResult.success ? 'v' : 'x' }}
          </span>
          <span class="font-bold" :class="testResult.success ? 'text-green-400' : 'text-red-400'">
            {{ testResult.success ? '成功' : '失败' }}
          </span>
          <span v-if="testResult.status_code" class="text-xs opacity-70">(HTTP {{ testResult.status_code }})</span>
        </div>
        <div v-if="testResult.message" class="text-sm opacity-80">{{ testResult.message }}</div>
        <div v-if="testResult.response?.body" class="space-y-2">
          <div class="text-xs font-bold text-green-400">响应体</div>
          <pre class="p-3 bg-black/30 rounded text-xs font-mono overflow-x-auto max-h-60">{{
            typeof testResult.response.body === 'string'
              ? testResult.response.body
              : JSON.stringify(testResult.response.body, null, 2)
          }}</pre>
        </div>
      </div>
      <template #footer>
        <TerminalButton @click="showTestModal = false">关闭</TerminalButton>
      </template>
    </TerminalModal>
  </TerminalLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import TerminalLayout from '@/components/TerminalLayout.vue'
import TerminalModal from '@/components/TerminalModal.vue'
import TerminalButton from '@/components/TerminalButton.vue'
import {
  getChannels,
  createChannel,
  updateChannel,
  deleteChannel as apiDeleteChannel,
  testChannel as apiTestChannel,
  getChannelHealth,
  batchUpdateChannels,
  batchDeleteChannels,
  exportConfig,
  importConfig,
  syncChannelModels,
  getPlatforms
} from '@/api'
import type { Channel, HealthStatus } from '@/types'

const channels = ref<Channel[]>([])
const healthMap = ref<Record<number, HealthStatus>>({})
const showModal = ref(false)
const showImportModal = ref(false)
const showTestModal = ref(false)
const editingId = ref<number | null>(null)
const testResult = ref<any>(null)
const importData = ref('')
const selectedPreset = ref('')
const saving = ref(false)

// Platform list with icons for card display
const platformList = [
  { key: 'deepseek', label: 'DeepSeek', icon: 'D' },
  { key: 'kimi', label: 'Kimi', icon: 'K' },
  { key: 'kimi-coding', label: 'Kimi Coding', icon: 'C' },
  { key: 'zhipu', label: '智谱', icon: 'Z' },
  { key: 'qwen', label: '通义', icon: 'T' },
  { key: 'siliconflow', label: '硅基', icon: 'S' }
]

// Preset mappings
const presets: Record<string, any> = {
  deepseek: { name: 'DeepSeek', api_type: 'openai', base_url: 'https://api.deepseek.com', models: 'deepseek-chat,deepseek-reasoner' },
  kimi: { name: 'Kimi', api_type: 'openai', base_url: 'https://api.moonshot.cn', models: 'moonshot-v1-8k,moonshot-v1-32k,moonshot-v1-128k,kimi-k2' },
  'kimi-coding': { name: 'Kimi Coding', api_type: 'openai', base_url: 'https://api.kimi.com/coding/v1', models: 'kimi-for-coding' },
  zhipu: { name: '智谱GLM', api_type: 'openai', base_url: 'https://open.bigmodel.cn/api/paas/v4', models: 'glm-4,glm-4-flash' },
  qwen: { name: '通义千问', api_type: 'openai', base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1', models: 'qwen-plus,qwen-max,qwen-turbo' },
  siliconflow: { name: 'SiliconFlow', api_type: 'openai', base_url: 'https://api.siliconflow.cn', models: 'deepseek-ai/DeepSeek-V3,deepseek-ai/DeepSeek-R1,Qwen/Qwen2.5-7B-Instruct' }
}

// View mode and filters
const viewMode = ref<'grid' | 'list'>('grid')
const searchTerm = ref('')
const statusFilter = ref('all')

// Pagination
const currentPage = ref(1)
const totalPages = ref(1)
const total = ref(0)

const pageRange = computed(() => {
  const range = []
  const start = Math.max(1, currentPage.value - 2)
  const end = Math.min(totalPages.value, currentPage.value + 2)
  for (let i = start; i <= end; i++) range.push(i)
  return range
})

const filteredChannels = computed(() => {
  let result = channels.value

  if (searchTerm.value) {
    const term = searchTerm.value.toLowerCase()
    result = result.filter(ch =>
      ch.name.toLowerCase().includes(term) ||
      ch.base_url.toLowerCase().includes(term)
    )
  }

  if (statusFilter.value === 'enabled') {
    result = result.filter(ch => ch.status === 1)
  } else if (statusFilter.value === 'disabled') {
    result = result.filter(ch => ch.status === 0)
  }

  return result
})

const form = ref({
  name: '',
  api_type: 'openai',
  base_url: 'https://api.openai.com',
  api_key: '',
  models: 'gpt-3.5-turbo,gpt-4',
  reasoning_levels: 'low,medium,high'
})

async function loadChannels(page = 1) {
  try {
    currentPage.value = page
    const res = await getChannels(page, 20)
    channels.value = res.data.items || res.data
    total.value = res.data.total || res.data.length
    totalPages.value = res.data.pages || 1

    // Load health for each channel
    if (channels.value.length > 0) {
      const healthPromises = channels.value.map(async (ch) => {
        try {
          const healthRes = await getChannelHealth(ch.id)
          healthMap.value[ch.id] = healthRes.data
        } catch {
          // ignore
        }
      })
      await Promise.all(healthPromises)
    }
  } catch (e: any) {
    console.error('加载渠道失败:', e)
  }
}

function openCreateModal() {
  editingId.value = null
  selectedPreset.value = ''
  form.value = {
    name: '',
    api_type: 'openai',
    base_url: 'https://api.openai.com',
    api_key: '',
    models: 'gpt-3.5-turbo,gpt-4',
    reasoning_levels: 'low,medium,high'
  }
  showModal.value = true
}

function onPresetSelect(key: string) {
  selectedPreset.value = key
  if (!key) {
    form.value = { name: '', api_type: 'openai', base_url: 'https://api.openai.com', api_key: '', models: '', reasoning_levels: 'low,medium,high' }
    return
  }
  const preset = presets[key]
  if (preset) {
    form.value.name = preset.name
    form.value.api_type = preset.api_type
    form.value.base_url = preset.base_url
    form.value.models = preset.models
  }
}

function editChannel(channel: Channel) {
  editingId.value = channel.id
  form.value = {
    name: channel.name,
    api_type: channel.api_type || 'openai',
    base_url: channel.base_url,
    api_key: '',
    models: channel.models?.join(',') || '',
    reasoning_levels: channel.reasoning_levels || 'low,medium,high'
  }
  showModal.value = true
}

async function toggleChannel(channel: Channel) {
  try {
    const newStatus = channel.status === 1 ? 0 : 1
    await updateChannel(channel.id, { status: newStatus })
    channel.status = newStatus
  } catch (e: any) {
    console.error('切换渠道状态失败:', e)
  }
}

async function saveChannel() {
  saving.value = true
  try {
    const models = form.value.models.split(',').map(s => s.trim()).filter(Boolean)
    const data = { ...form.value, models }
    let channelId = editingId.value
    if (editingId.value) {
      await updateChannel(editingId.value, data)
    } else {
      const res = await createChannel(data)
      channelId = res.id
    }
    // Auto-sync models from upstream if preset was selected
    if (channelId && selectedPreset.value) {
      try {
        const syncRes = await syncChannelModels(channelId)
        if (syncRes.success && syncRes.data?.count > 0) {
          alert(`渠道创建成功，已自动同步 ${syncRes.data.count} 个模型`)
        } else {
          alert('渠道创建成功')
        }
      } catch {
        alert('渠道创建成功（模型同步失败，可稍后手动同步）')
      }
    } else {
      alert('保存成功')
    }
    showModal.value = false
    loadChannels(currentPage.value)
  } catch (e: any) {
    alert('保存失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    saving.value = false
  }
}

async function testChannel(id: number) {
  try {
    const res = await apiTestChannel(id)
    testResult.value = res
    showTestModal.value = true
  } catch (e: any) {
    console.error('测试渠道失败:', e)
    alert('测试失败: ' + (e.response?.data?.detail || e.message))
  }
}

async function syncModels(id: number) {
  try {
    const res = await syncChannelModels(id)
    if (res.success) {
      const count = res.data?.count || 0
      alert(`同步成功: ${count} 个模型`)
      loadChannels(currentPage.value)
    }
  } catch (e: any) {
    alert('同步失败: ' + (e.response?.data?.detail || e.message))
  }
}

async function deleteChannel(id: number) {
  if (!confirm('确定删除渠道 #' + id + '?')) return
  try {
    await apiDeleteChannel(id)
    loadChannels(currentPage.value)
  } catch (e: any) {
    console.error('删除渠道失败:', e)
  }
}

async function handleExport() {
  const res = await exportConfig()
  const dataStr = JSON.stringify(res.data, null, 2)
  const blob = new Blob([dataStr], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `co-api-config-${new Date().toISOString().slice(0, 10)}.json`
  a.click()
  URL.revokeObjectURL(url)
}

async function handleImport() {
  try {
    const data = JSON.parse(importData.value)
    await importConfig(data)
    showImportModal.value = false
    importData.value = ''
    loadChannels(1)
    alert('导入成功')
  } catch (e: any) {
    alert('导入失败: ' + e.message)
  }
}

function formatNumber(num: number): string {
  if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M'
  if (num >= 1000) return (num / 1000).toFixed(1) + 'K'
  return num.toString()
}

onMounted(() => loadChannels(1))
</script>

<style scoped>
/* 渠道卡片 - 参考 octopus Card 设计 */
.channel-card {
  background: rgba(0, 20, 5, 0.6);
  border: 1px solid rgba(0, 255, 65, 0.12);
  border-radius: 12px;
  padding: 16px;
  transition: all 0.3s ease;
  animation: cardFadeIn 0.4s ease-out both;
}

.channel-card:hover {
  border-color: rgba(0, 255, 65, 0.25);
  background: rgba(0, 30, 10, 0.7);
  transform: translateY(-2px);
}

@keyframes cardFadeIn {
  from {
    opacity: 0;
    transform: translateY(16px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 切换开关 - 参考 octopus Switch */
.toggle-switch {
  width: 40px;
  height: 22px;
  border-radius: 11px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(0, 255, 65, 0.2);
  position: relative;
  cursor: pointer;
  transition: all 0.3s ease;
  flex-shrink: 0;
}

.toggle-switch.enabled {
  background: rgba(0, 255, 65, 0.2);
  border-color: rgba(0, 255, 65, 0.4);
}

.toggle-thumb {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.6);
  transition: all 0.3s ease;
}

.toggle-switch.enabled .toggle-thumb {
  transform: translateX(18px);
  background: #00ff41;
}

/* 指标网格 */
.metrics-grid {
  display: grid;
  gap: 8px;
}

.metrics-grid.grid {
  grid-template-columns: repeat(2, 1fr);
}

.metrics-grid.list {
  grid-template-columns: repeat(4, 1fr);
}

.metric-item {
  background: rgba(0, 30, 10, 0.4);
  border-radius: 8px;
  padding: 8px 10px;
}

/* 模型标签 */
.model-tags {
  display: flex;
  flex-wrap: wrap;
}

.model-tag {
  background: rgba(0, 255, 65, 0.1);
  border: 1px solid rgba(0, 255, 65, 0.15);
  border-radius: 4px;
  padding: 2px 6px;
  font-size: 10px;
  color: rgba(0, 255, 65, 0.8);
}

.model-tag-more {
  background: rgba(0, 255, 65, 0.05);
  border-radius: 4px;
  padding: 2px 6px;
  font-size: 10px;
  opacity: 0.6;
}

/* 操作按钮 */
.action-btn {
  flex: 1;
  padding: 6px 8px;
  border-radius: 6px;
  background: rgba(0, 30, 10, 0.4);
  border: 1px solid rgba(0, 255, 65, 0.1);
  color: rgba(0, 255, 65, 0.8);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.action-btn:hover {
  background: rgba(0, 50, 20, 0.5);
  border-color: rgba(0, 255, 65, 0.25);
}

.action-btn.danger {
  color: rgba(255, 80, 80, 0.8);
  border-color: rgba(255, 80, 80, 0.1);
}

.action-btn.danger:hover {
  background: rgba(255, 80, 80, 0.1);
  border-color: rgba(255, 80, 80, 0.25);
}

/* 视图切换 */
.view-toggle {
  width: 32px;
  height: 32px;
  border-radius: 6px;
  background: rgba(0, 20, 5, 0.6);
  border: 1px solid rgba(0, 255, 65, 0.15);
  color: rgba(0, 255, 65, 0.6);
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.view-toggle:hover {
  border-color: rgba(0, 255, 65, 0.3);
}

.view-toggle.active {
  background: rgba(0, 255, 65, 0.15);
  border-color: rgba(0, 255, 65, 0.4);
  color: #00ff41;
}

/* 表单输入 */
.form-input {
  background: rgba(0, 20, 5, 0.6);
  border: 1px solid rgba(0, 255, 65, 0.15);
  border-radius: 8px;
  padding: 8px 12px;
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

.form-input::placeholder {
  color: rgba(0, 255, 65, 0.3);
}

/* 文字发光 */
.glow-text {
  color: #00ff41;
  text-shadow: 0 0 6px rgba(0, 255, 65, 0.3);
}

.platform-card {
  padding: 10px 8px; border-radius: var(--radius); cursor: pointer; transition: all 0.15s;
  background: rgba(0,20,8,0.4); border: 1px solid var(--border);
  text-align: center; color: var(--text-dim);
}
.platform-card:hover { border-color: var(--border-hover); color: var(--text); }
.platform-card.selected { border-color: var(--border-focus); background: rgba(0,180,100,0.08); color: var(--green); }
</style>
