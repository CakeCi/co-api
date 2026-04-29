<template>
  <TerminalLayout>
    <div class="fade-in">
      <h2 class="text-xl font-bold glow-text mb-6">统计报表</h2>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <div class="content-card">
          <h3 class="text-lg mb-4 flex items-center gap-2">
            <span class="text-green-400">▬</span> 日统计 (近7天)
          </h3>
          <div class="space-y-2 max-h-80 overflow-auto">
            <div v-for="d in dailyStats" :key="d.date" class="flex justify-between items-center py-2 border-b border-green-900/30">
              <span class="font-mono">{{ d.date }}</span>
              <div class="flex gap-4 text-sm">
                <span>请求: {{ d.request_count }}</span>
                <span>成功: <span class="text-green-400">{{ d.success_count }}</span></span>
                <span>失败: <span class="text-red-400">{{ d.fail_count }}</span></span>
                <span>Tokens: {{ d.input_tokens + d.output_tokens }}</span>
              </div>
            </div>
          </div>
        </div>

        <div class="content-card">
          <h3 class="text-lg mb-4 flex items-center gap-2">
            <span class="text-green-400">▬</span> 模型排行
          </h3>
          <div class="space-y-2 max-h-80 overflow-auto">
            <div v-for="m in modelStats" :key="m.model_name" class="flex justify-between items-center py-2 border-b border-green-900/30">
              <span class="font-mono truncate max-w-[200px]">{{ m.model_name }}</span>
              <div class="flex gap-4 text-sm">
                <span>请求: {{ m.request_count }}</span>
                <span>Tokens: {{ m.input_tokens + m.output_tokens }}</span>
              </div>
            </div>
          </div>
        </div>

        <div class="content-card">
          <h3 class="text-lg mb-4 flex items-center gap-2">
            <span class="text-green-400">▬</span> 渠道排行
          </h3>
          <div class="space-y-2 max-h-80 overflow-auto">
            <div v-for="c in channelStats" :key="c.channel_id" class="flex justify-between items-center py-2 border-b border-green-900/30">
              <span class="truncate max-w-[200px]">{{ c.channel_name }}</span>
              <div class="flex gap-4 text-sm">
                <span>请求: {{ c.request_count }}</span>
                <span class="text-green-400">{{ c.success_count }}</span>
                <span class="text-red-400">{{ c.fail_count }}</span>
                <span>FTUT: {{ c.avg_first_token_ms }}ms</span>
              </div>
            </div>
          </div>
        </div>

        <div class="content-card">
          <h3 class="text-lg mb-4 flex items-center gap-2">
            <span class="text-green-400">▬</span> Token 用量
          </h3>
          <div class="space-y-2 max-h-80 overflow-auto">
            <div v-for="t in tokenStats" :key="t.token_id" class="flex justify-between items-center py-2 border-b border-green-900/30">
              <span class="truncate max-w-[200px]">{{ t.token_name }}</span>
              <div class="flex gap-4 text-sm">
                <span>请求: {{ t.request_count }}</span>
                <span>Tokens: {{ t.input_tokens + t.output_tokens }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </TerminalLayout>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import TerminalLayout from '@/components/TerminalLayout.vue'
import api from '@/api'

const dailyStats = ref<any[]>([])
const modelStats = ref<any[]>([])
const channelStats = ref<any[]>([])
const tokenStats = ref<any[]>([])

async function load() {
  const [d, m, c, t] = await Promise.all([
    api.get('/api/stats/daily?days=7'),
    api.get('/api/stats/models'),
    api.get('/api/stats/channels'),
    api.get('/api/stats/tokens'),
  ])
  dailyStats.value = d.data.data || []
  modelStats.value = m.data.data || []
  channelStats.value = c.data.data || []
  tokenStats.value = t.data.data || []
}

onMounted(load)
</script>

<style scoped>
.content-card { background: #0a0f0a; border: 1px solid #003300; border-radius: 8px; padding: 16px; }
</style>