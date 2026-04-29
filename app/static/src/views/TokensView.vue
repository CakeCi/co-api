<template>
  <TerminalLayout>
    <div class="fade-in">
      <div class="flex justify-between items-center mb-6">
        <h2 class="text-xl font-bold glow-text">API 令牌</h2>
        <TerminalButton @click="openCreateModal">+ 新建令牌</TerminalButton>
      </div>

      <DataTable
        :data="tokens"
        :columns="columns"
        :row-key="(row) => row.id"
        batchable
        :batch-actions="batchActions"
        @batch="handleBatch"
      >
        <template #cell-key="{ row }">
          <span class="font-mono text-xs">{{ maskSecret(row.key) }}</span>
        </template>

        <template #cell-status="{ value }">
          <span :class="value === 1 ? 'text-green-400' : 'text-red-400'">
            {{ value === 1 ? '启用' : '禁用' }}
          </span>
        </template>

        <template #cell-actions="{ row }">
          <TerminalButton size="sm" variant="danger" @click="deleteToken(row.id)">删除</TerminalButton>
        </template>
      </DataTable>

      <div v-if="tokens.length === 0" class="text-center py-12 opacity-50">
        暂无令牌
      </div>

      <!-- Pagination -->
      <div v-if="totalPages > 1" class="flex justify-between items-center mt-4 text-xs">
        <div class="opacity-70">第 {{ currentPage }} / {{ totalPages }} 页，共 {{ total }} 条</div>
        <div class="flex gap-1">
          <TerminalButton
            v-if="currentPage > 1"
            size="sm"
            @click="loadTokens(currentPage - 1)"
          >
            上一页
          </TerminalButton>
          <TerminalButton
            v-for="p in pageRange"
            :key="p"
            size="sm"
            :variant="p === currentPage ? 'default' : 'ghost'"
            @click="loadTokens(p)"
          >
            {{ p }}
          </TerminalButton>
          <TerminalButton
            v-if="currentPage < totalPages"
            size="sm"
            @click="loadTokens(currentPage + 1)"
          >
            下一页
          </TerminalButton>
        </div>
      </div>
    </div>

    <!-- Create Modal -->
    <TerminalModal v-model="showModal" title="新建令牌" size="sm">
      <div class="space-y-3">
        <div>
          <label class="block text-xs mb-1 opacity-80">名称</label>
          <input v-model="form.name" class="form-input" />
        </div>
      </div>
      <template #footer>
        <TerminalButton @click="saveToken">生成</TerminalButton>
        <TerminalButton variant="ghost" @click="showModal = false">取消</TerminalButton>
      </template>
    </TerminalModal>

    <!-- Show Key Modal -->
    <TerminalModal v-model="showKeyModal" title="令牌创建成功" size="sm">
      <div class="space-y-3">
        <p class="text-sm opacity-80">请立即复制密钥，关闭后将无法再次查看：</p>
        <div class="p-3 bg-black/30 rounded font-mono text-xs break-all text-green-400">
          {{ newKey }}
        </div>
        <TerminalButton @click="copyKey">复制密钥</TerminalButton>
      </div>
      <template #footer>
        <TerminalButton @click="showKeyModal = false">关闭</TerminalButton>
      </template>
    </TerminalModal>
  </TerminalLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import TerminalLayout from '@/components/TerminalLayout.vue'
import DataTable from '@/components/DataTable.vue'
import TerminalModal from '@/components/TerminalModal.vue'
import TerminalButton from '@/components/TerminalButton.vue'
import {
  getTokens,
  createToken,
  deleteToken as apiDeleteToken,
  batchUpdateTokens,
  batchDeleteTokens
} from '@/api'
import type { Token } from '@/types'
import { maskSecret } from '@/utils'

const tokens = ref<Token[]>([])
const showModal = ref(false)
const showKeyModal = ref(false)
const newKey = ref('')
const form = ref({ name: 'default' })

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

const columns = [
  { key: 'id', title: 'ID' },
  { key: 'name', title: '名称' },
  { key: 'key', title: '密钥' },
  { key: 'status', title: '状态' },
  { key: 'actions', title: '操作' }
]

const batchActions = [
  { key: 'enable', label: '批量启用' },
  { key: 'disable', label: '批量禁用' },
  { key: 'delete', label: '批量删除', variant: 'danger' as const }
]

async function loadTokens(page = 1) {
  try {
    currentPage.value = page
    const res = await getTokens(page, 20)
    tokens.value = res.data.items || res.data
    total.value = res.data.total || res.data.length
    totalPages.value = res.data.pages || 1
  } catch (e: any) {
    console.error('加载令牌失败:', e)
  }
}

function openCreateModal() {
  form.value = { name: 'default' }
  showModal.value = true
}

async function saveToken() {
  try {
    const res = await createToken(form.value)
    newKey.value = res.data.key
    showModal.value = false
    showKeyModal.value = true
    loadTokens(currentPage.value)
  } catch (e: any) {
    console.error('创建令牌失败:', e)
    alert('创建失败: ' + (e.response?.data?.detail || e.message))
  }
}

async function copyKey() {
  try {
    await navigator.clipboard.writeText(newKey.value)
    alert('已复制到剪贴板')
  } catch {
    alert('复制失败，请手动复制')
  }
}

async function deleteToken(id: number) {
  if (!confirm('确定删除令牌 #' + id + '?')) return
  try {
    await apiDeleteToken(id)
    loadTokens(currentPage.value)
  } catch (e: any) {
    console.error('删除令牌失败:', e)
  }
}

async function handleBatch(action: string, ids: (string | number)[]) {
  const numIds = ids.map(id => Number(id))
  try {
    switch (action) {
      case 'enable':
        await batchUpdateTokens(numIds, 1)
        break
      case 'disable':
        await batchUpdateTokens(numIds, 0)
        break
      case 'delete':
        if (!confirm(`确定删除 ${numIds.length} 个令牌?`)) return
        await batchDeleteTokens(numIds)
        break
    }
    loadTokens(currentPage.value)
  } catch (e: any) {
    console.error('批量操作失败:', e)
  }
}

onMounted(() => loadTokens(1))
</script>

<style scoped>
.form-input {
  width: 100%;
  background: transparent;
  border: 1px solid rgba(0, 255, 65, 0.2);
  padding: 8px 12px;
  color: white;
  font-family: inherit;
  font-size: 14px;
}

.form-input:focus {
  outline: none;
  border-color: #00ff41;
  box-shadow: 0 0 12px rgba(0, 255, 65, 0.4);
}

</style>
