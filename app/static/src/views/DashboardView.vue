<template>
  <TerminalLayout>
    <div class="fade-in">
      <h2 class="text-xl font-bold page-title mb-6">数据看板</h2>

      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div v-for="(card, index) in statsCards" :key="card.key"
          class="stat-card" :style="{ animationDelay: `${index * 0.06}s` }">
          <div class="flex items-center gap-3 mb-3">
            <div class="stat-icon"><span class="text-base">{{ card.icon }}</span></div>
            <span class="text-xs text-dim">{{ card.label }}</span>
          </div>
          <div class="text-2xl font-bold font-mono">{{ card.value }}</div>
          <div v-if="card.subValue" class="text-xs text-dim mt-1">{{ card.subValue }}</div>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <div class="content-card">
          <h3 class="text-sm font-bold mb-4 flex items-center gap-2"><span class="text-green">▬</span> 请求趋势 (最近7天)</h3>
          <EChart :option="trendChartOption" style="height: 300px" />
        </div>
        <div class="content-card">
          <h3 class="text-sm font-bold mb-4 flex items-center gap-2"><span class="text-green">▬</span> 模型分布 (最近7天)</h3>
          <EChart :option="modelChartOption" style="height: 300px" />
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <div class="content-card">
          <h3 class="text-sm font-bold mb-4 flex items-center gap-2"><span class="text-green">▬</span> 最近活动</h3>
          <div class="space-y-2 max-h-80 overflow-auto">
            <div v-for="(activity, idx) in recentActivities" :key="idx" class="activity-item">
              <div class="flex items-center gap-3">
                <div class="activity-icon" :class="activity.status === 'success' ? 'bg-green/10 text-green' : 'bg-red-900/20 text-red-400'">
                  <span>{{ activity.status === 'success' ? '▸' : '✕' }}</span>
                </div>
                <div class="flex-1 min-w-0">
                  <div class="flex items-center gap-2">
                    <span class="text-sm font-medium truncate">{{ activity.model }}</span>
                    <span class="text-xs text-soft">→</span>
                    <span class="text-xs text-dim truncate">{{ activity.channel }}</span>
                  </div>
                  <div class="text-xs text-soft mt-0.5">{{ activity.time }} · {{ activity.tokens }} tokens · {{ activity.duration }}ms</div>
                </div>
              </div>
            </div>
            <div v-if="recentActivities.length === 0" class="text-center text-xs text-dim py-8">暂无活动记录</div>
          </div>
        </div>

        <div class="content-card">
          <h3 class="text-sm font-bold mb-4 flex items-center gap-2"><span class="text-green">▬</span> 模型排行</h3>
          <div class="space-y-1 max-h-80 overflow-auto">
            <div v-for="(model, idx) in modelRankings" :key="idx" class="rank-item">
              <div class="flex items-center gap-3">
                <div class="rank-number" :class="idx < 3 ? 'font-bold' : 'text-dim'">{{ idx + 1 }}</div>
                <div class="flex-1 min-w-0">
                  <div class="flex items-center justify-between">
                    <span class="text-sm truncate">{{ model.name }}</span>
                    <span class="text-xs font-mono">{{ model.count }}</span>
                  </div>
                  <div class="mt-1 rank-bar-bg">
                    <div class="rank-bar-fill" :style="{ width: `${(model.count / maxModelCount) * 100}%` }"></div>
                  </div>
                </div>
              </div>
            </div>
            <div v-if="modelRankings.length === 0" class="text-center text-xs text-dim py-8">暂无数据</div>
          </div>
        </div>
      </div>

      <div class="content-card mb-6">
        <div class="flex justify-between items-center mb-4">
          <h3 class="text-sm font-bold flex items-center gap-2"><span class="text-green">▬</span> 渠道健康状态</h3>
          <span class="text-xs text-dim">自动刷新: 30s</span>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <div v-for="ch in channels" :key="ch.id" class="channel-card">
            <div class="flex justify-between items-start">
              <div class="min-w-0">
                <div class="text-sm font-bold truncate">{{ ch.name }}</div>
                <div class="text-xs text-dim mt-1 truncate">{{ ch.base_url }}</div>
              </div>
              <HealthBadge :health="healthMap[ch.id]" />
            </div>
            <div v-if="healthMap[ch.id]" class="mt-3 grid grid-cols-3 gap-2 text-xs">
              <div class="metric-box"><div class="text-dim text-xs">成功率</div><div class="font-mono">{{ healthMap[ch.id]?.success_rate?.toFixed(1) || 0 }}%</div></div>
              <div class="metric-box"><div class="text-dim text-xs">总请求</div><div class="font-mono">{{ formatNumber(healthMap[ch.id]?.total_requests || 0) }}</div></div>
              <div class="metric-box"><div class="text-dim text-xs">连续失败</div><div class="font-mono" :class="(healthMap[ch.id]?.consecutive_failures || 0) > 3 ? 'text-red-400' : ''">{{ healthMap[ch.id]?.consecutive_failures || 0 }}</div></div>
            </div>
          </div>
        </div>
      </div>

      <div class="content-card">
        <h3 class="text-sm font-bold mb-4 flex items-center gap-2"><span class="text-green">▬</span> 系统状态</h3>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
          <div class="status-item"><span class="status-dot bg-green-400"></span><span>网关服务: 运行中</span></div>
          <div class="status-item"><span class="status-dot" :class="(stats?.active_channels || 0) > 0 ? 'bg-green-400' : 'bg-red-400'"></span><span>上游渠道: {{ stats?.active_channels || 0 }} 个活跃</span></div>
          <div class="status-item"><span class="status-dot bg-green-400"></span><span>数据库: 正常</span></div>
        </div>
      </div>
    </div>
  </TerminalLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import TerminalLayout from '@/components/TerminalLayout.vue'
import EChart from '@/components/EChart.vue'
import HealthBadge from '@/components/HealthBadge.vue'
import { getDashboardStats, getChannels, getChannelHealth, getLogs } from '@/api'
import type { DashboardStats, Channel, HealthStatus, RequestLog } from '@/types'

const stats = ref<DashboardStats | null>(null)
const channels = ref<Channel[]>([])
const healthMap = ref<Record<number, HealthStatus>>({})
const recentLogs = ref<RequestLog[]>([])
let refreshTimer: number | null = null

const statsCards = computed(() => [
  { key: 'requests', label: '总请求数', value: formatNumber(stats.value?.total_requests || 0), subValue: `今日: ${formatNumber(stats.value?.today_requests || 0)}`, icon: '◈' },
  { key: 'tokens', label: '总Tokens', value: formatNumber(stats.value?.total_tokens || 0), subValue: `输入: ${formatNumber(stats.value?.prompt_tokens || 0)}`, icon: '◇' },
  { key: 'output', label: '输出Tokens', value: formatNumber(stats.value?.completion_tokens || 0), subValue: `失败估算: ${formatNumber(stats.value?.failed_estimated_completion_tokens || 0)}`, icon: '▸' },
  { key: 'failure', label: '失败率', value: `${stats.value?.failure_rate || 0}%`, subValue: `${stats.value?.active_channels || 0} 个活跃渠道`, icon: '▣' }
])

const recentActivities = computed(() => recentLogs.value.slice(0, 10).map((log: RequestLog) => ({
  model: log.model || '未知模型', channel: log.channel_name || `渠道#${log.channel_id}`,
  status: log.status === 1 ? 'success' : 'error', time: formatTime(log.created_at),
  tokens: ((log.prompt_tokens || 0) + (log.completion_tokens || 0)).toLocaleString(), duration: log.duration_ms || 0
})))

const modelRankings = computed(() => {
  const dist = stats.value?.model_distribution || []
  return dist.sort((a, b) => b.count - a.count).slice(0, 10).map(m => ({ name: m.model, count: m.count }))
})
const maxModelCount = computed(() => modelRankings.value.length === 0 ? 1 : Math.max(...modelRankings.value.map(m => m.count)))

const trendChartOption = computed(() => {
  const trend = stats.value?.trend || []
  return {
    backgroundColor: 'transparent',
    grid: { top: 30, right: 20, bottom: 30, left: 50 },
    xAxis: { type: 'category' as const, data: trend.map(t => t.date.slice(5)), axisLine: { lineStyle: { color: 'rgba(0,200,110,0.2)' } }, axisLabel: { color: 'rgba(0,200,110,0.6)', rotate: 30, fontSize: 11 } },
    yAxis: { type: 'value' as const, axisLine: { lineStyle: { color: 'rgba(0,200,110,0.2)' } }, axisLabel: { color: 'rgba(0,200,110,0.6)' }, splitLine: { lineStyle: { color: 'rgba(0,200,110,0.06)' } } },
    series: [{ type: 'bar' as const, data: trend.map(t => t.count), itemStyle: { color: 'rgba(0,200,110,0.5)', borderRadius: [4, 4, 0, 0] } }]
  }
})
const modelChartOption = computed(() => {
  const topModels = [...(stats.value?.model_distribution || [])].sort((a, b) => b.count - a.count).slice(0, 8)
  return {
    backgroundColor: 'transparent',
    grid: { top: 20, right: 40, bottom: 20, left: 140 },
    xAxis: { type: 'value' as const, axisLine: { lineStyle: { color: 'rgba(0,200,110,0.2)' } }, axisLabel: { color: 'rgba(0,200,110,0.6)' }, splitLine: { lineStyle: { color: 'rgba(0,200,110,0.06)' } } },
    yAxis: { type: 'category' as const, data: topModels.map(m => m.model).reverse(), axisLine: { lineStyle: { color: 'rgba(0,200,110,0.2)' } }, axisLabel: { color: 'rgba(0,200,110,0.6)', fontSize: 12, width: 130, overflow: 'truncate' as const }, inverse: true },
    series: [{ type: 'bar' as const, data: topModels.map(m => m.count).reverse(), barWidth: 20, barCategoryGap: '40%', itemStyle: { color: 'rgba(0,200,110,0.6)', borderRadius: [0, 4, 4, 0] } }]
  }
})

function formatNumber(num: number): string { return num.toLocaleString() }
function formatTime(timestamp: string): string { const d = new Date(timestamp); return d.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }) }

async function loadDashboard() { try { const res = await getDashboardStats(); stats.value = res.data } catch (e) { console.error('加载看板失败:', e) } }
async function loadChannelsHealth() {
  try { const res = await getChannels(); channels.value = res.data; await Promise.all(channels.value.map(async ch => { try { healthMap.value[ch.id] = (await getChannelHealth(ch.id)).data } catch {} })) } catch {}
}
async function loadRecentLogs() { try { recentLogs.value = (await getLogs(1, 10)).data.logs || [] } catch {} }

onMounted(() => { loadDashboard(); loadChannelsHealth(); loadRecentLogs(); refreshTimer = window.setInterval(() => { loadDashboard(); loadChannelsHealth(); loadRecentLogs() }, 30000) })
onUnmounted(() => { if (refreshTimer) clearInterval(refreshTimer) })
</script>

<style scoped>
.stat-card {
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: var(--radius-lg); padding: 18px;
  transition: border-color 0.2s; animation: cardFadeIn 0.4s ease-out both;
}
.stat-card:hover { border-color: var(--border-hover); }
@keyframes cardFadeIn { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }
.stat-icon { width: 34px; height: 34px; border-radius: 8px; display: flex; align-items: center; justify-content: center; background: rgba(0,180,100,0.1); }
.content-card { background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 18px; }
.activity-item { padding: 10px 12px; background: rgba(0,16,4,0.3); border-radius: var(--radius); transition: background 0.15s; }
.activity-item:hover { background: rgba(0,24,8,0.4); }
.activity-icon { width: 26px; height: 26px; border-radius: 6px; display: flex; align-items: center; justify-content: center; font-size: 11px; flex-shrink: 0; }
.rank-item { padding: 6px 10px; transition: background 0.15s; }
.rank-item:hover { background: rgba(0,24,8,0.25); border-radius: 6px; }
.rank-number { width: 22px; font-size: 13px; text-align: center; font-family: monospace; }
.rank-bar-bg { height: 4px; background: rgba(0,180,100,0.06); border-radius: 2px; overflow: hidden; }
.rank-bar-fill { height: 100%; background: rgba(0,200,110,0.4); border-radius: 2px; transition: width 0.5s ease; }
.channel-card { background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius); padding: 14px; transition: border-color 0.15s; }
.channel-card:hover { border-color: var(--border-hover); }
.metric-box { background: rgba(0,24,8,0.3); border-radius: 6px; padding: 6px 8px; }
.status-item { display: flex; align-items: center; gap: 8px; padding: 8px 12px; background: rgba(0,16,4,0.3); border-radius: var(--radius); }
.status-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.page-title { color: var(--green); text-shadow: 0 0 16px rgba(0,200,100,0.1); }
.text-green { color: var(--green); }
.text-dim { color: var(--text-dim); }
.text-soft { color: var(--text-soft); }
.bg-green\/10 { background: rgba(0,200,100,0.1); }
</style>
