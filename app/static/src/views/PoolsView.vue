<template>
  <TerminalLayout>
    <div class="fade-in">
      <div class="flex justify-between items-center mb-6">
        <h2 class="text-xl font-bold glow-text">模型池</h2>
        <TerminalButton @click="openCreateModal">+ 新建池子</TerminalButton>
      </div>

      <DataTable
        :data="pools"
        :columns="columns"
        :row-key="(row) => row.id"
      >
        <template #cell-status="{ value }">
          <span :class="value === 1 ? 'text-green-400' : 'text-red-400'">
            {{ value === 1 ? '启用' : '禁用' }}
          </span>
        </template>

        <template #cell-actions="{ row }">
          <div class="flex gap-1">
            <TerminalButton size="sm" @click="showMembers(row)">成员</TerminalButton>
            <TerminalButton size="sm" @click="editPool(row)">编辑</TerminalButton>
            <TerminalButton size="sm" variant="danger" @click="deletePool(row.id)">删除</TerminalButton>
          </div>
        </template>
      </DataTable>

      <div v-if="pools.length === 0" class="text-center py-12 opacity-50">
        暂无模型池
      </div>

      <!-- Pagination -->
      <div v-if="totalPages > 1" class="flex justify-between items-center mt-4 text-xs">
        <div class="opacity-70">第 {{ currentPage }} / {{ totalPages }} 页，共 {{ total }} 条</div>
        <div class="flex gap-1">
          <TerminalButton
            v-if="currentPage > 1"
            size="sm"
            @click="loadPools(currentPage - 1)"
          >
            上一页
          </TerminalButton>
          <TerminalButton
            v-for="p in pageRange"
            :key="p"
            size="sm"
            :variant="p === currentPage ? 'default' : 'ghost'"
            @click="loadPools(p)"
          >
            {{ p }}
          </TerminalButton>
          <TerminalButton
            v-if="currentPage < totalPages"
            size="sm"
            @click="loadPools(currentPage + 1)"
          >
            下一页
          </TerminalButton>
        </div>
      </div>

      <!-- Members Section -->
      <div v-if="currentPool" class="mt-8">
        <div class="flex justify-between items-center mb-4">
          <h3 class="text-lg font-bold glow-text">池子成员 - {{ currentPool.name }}</h3>
          <TerminalButton size="sm" @click="openMemberModal">+ 添加成员</TerminalButton>
        </div>

        <DataTable
          :data="members"
          :columns="memberColumns"
          :row-key="(row) => row.id"
        >
          <template #cell-priority="{ value }">
            {{ value === 1 ? '主渠道' : '备用' }}
          </template>

          <template #cell-status="{ value }">
            <span :class="value === 1 ? 'text-green-400' : 'text-red-400'">
              {{ value === 1 ? '启用' : '禁用' }}
            </span>
          </template>

          <template #cell-actions="{ row }">
            <div class="flex gap-1">
              <TerminalButton size="sm" @click="editMember(row)">编辑</TerminalButton>
              <TerminalButton size="sm" variant="danger" @click="deleteMember(row.id)">删除</TerminalButton>
            </div>
          </template>
        </DataTable>

        <div v-if="members.length === 0" class="text-center py-12 opacity-50">
          暂无成员
        </div>
      </div>
    </div>

    <!-- Pool Modal -->
    <TerminalModal v-model="showPoolModal" :title="editingPoolId ? '编辑池子' : '新建池子'" size="md">
      <div class="space-y-3">
        <div>
          <label class="block text-xs mb-1 opacity-80">名称（对外暴露的模型名）</label>
          <input v-model="poolForm.name" class="form-input" />
        </div>
        <div>
          <label class="block text-xs mb-1 opacity-80">描述</label>
          <input v-model="poolForm.description" class="form-input" />
        </div>
      </div>
      <template #footer>
        <TerminalButton @click="savePool">保存</TerminalButton>
        <TerminalButton variant="ghost" @click="showPoolModal = false">取消</TerminalButton>
      </template>
    </TerminalModal>

    <!-- Member Modal -->
    <TerminalModal v-model="showMemberModal" :title="editingMemberId ? '编辑成员' : '添加成员'" size="md">
      <div class="space-y-3">
        <div>
          <label class="block text-xs mb-1 opacity-80">渠道</label>
          <select v-model="memberForm.channel_id" class="form-input">
            <option v-for="ch in allChannels" :key="ch.id" :value="ch.id">
              {{ ch.name }} ({{ ch.api_type || 'openai' }})
            </option>
          </select>
        </div>
        <div>
          <label class="block text-xs mb-1 opacity-80">模型别名</label>
          <input v-model="memberForm.alias" class="form-input" placeholder="留空使用池子名称" />
        </div>
        <div>
          <label class="block text-xs mb-1 opacity-80">权重</label>
          <input v-model.number="memberForm.weight" type="number" min="1" max="1000" class="form-input" />
        </div>
        <div>
          <label class="block text-xs mb-1 opacity-80">优先级</label>
          <select v-model.number="memberForm.priority" class="form-input">
            <option :value="1">主渠道</option>
            <option :value="2">备用渠道</option>
          </select>
        </div>
      </div>
      <template #footer>
        <TerminalButton @click="saveMember">保存</TerminalButton>
        <TerminalButton variant="ghost" @click="showMemberModal = false">取消</TerminalButton>
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
  getPools,
  createPool,
  updatePool,
  deletePool as apiDeletePool,
  getPoolMembers,
  createPoolMember,
  updatePoolMember,
  deletePoolMember,
  getChannels
} from '@/api'
import type { ModelPool, PoolMember, Channel } from '@/types'

const pools = ref<ModelPool[]>([])
const members = ref<PoolMember[]>([])
const allChannels = ref<Channel[]>([])
const currentPool = ref<ModelPool | null>(null)
const showPoolModal = ref(false)
const showMemberModal = ref(false)
const editingPoolId = ref<number | null>(null)
const editingMemberId = ref<number | null>(null)

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

const poolForm = ref({ name: '', description: '' })
const memberForm = ref({ channel_id: 0, alias: '', weight: 100, priority: 1 })

const columns = [
  { key: 'id', title: 'ID' },
  { key: 'name', title: '名称' },
  { key: 'description', title: '描述' },
  { key: 'member_count', title: '成员数' },
  { key: 'status', title: '状态' },
  { key: 'actions', title: '操作' }
]

const memberColumns = [
  { key: 'id', title: 'ID' },
  { key: 'channel_name', title: '渠道' },
  { key: 'alias', title: '模型别名' },
  { key: 'weight', title: '权重' },
  { key: 'priority', title: '优先级' },
  { key: 'status', title: '状态' },
  { key: 'actions', title: '操作' }
]

async function loadPools(page = 1) {
  try {
    currentPage.value = page
    const res = await getPools(page, 20)
    pools.value = res.data.items || res.data
    total.value = res.data.total || res.data.length
    totalPages.value = res.data.pages || 1
  } catch (e: any) {
    console.error('加载模型池失败:', e)
  }
}

async function loadChannels() {
  try {
    const res = await getChannels(1, 100)
    allChannels.value = res.data.items || res.data
  } catch (e: any) {
    console.error('加载渠道失败:', e)
  }
}

function openCreateModal() {
  editingPoolId.value = null
  poolForm.value = { name: '', description: '' }
  showPoolModal.value = true
}

function editPool(pool: ModelPool) {
  editingPoolId.value = pool.id
  poolForm.value = { name: pool.name, description: pool.description || '' }
  showPoolModal.value = true
}

async function savePool() {
  try {
    if (editingPoolId.value) {
      await updatePool(editingPoolId.value, poolForm.value)
    } else {
      await createPool(poolForm.value)
    }
    showPoolModal.value = false
    loadPools(currentPage.value)
  } catch (e: any) {
    console.error('保存池子失败:', e)
    alert('保存失败: ' + (e.response?.data?.detail || e.message))
  }
}

async function deletePool(id: number) {
  if (!confirm('确定删除池子 #' + id + '?')) return
  try {
    await apiDeletePool(id)
    if (currentPool.value?.id === id) currentPool.value = null
    loadPools(currentPage.value)
  } catch (e: any) {
    console.error('删除池子失败:', e)
  }
}

async function showMembers(pool: ModelPool) {
  currentPool.value = pool
  try {
    const res = await getPoolMembers(pool.id)
    members.value = res.data
  } catch (e: any) {
    console.error('加载成员失败:', e)
  }
}

function openMemberModal() {
  editingMemberId.value = null
  memberForm.value = { channel_id: allChannels.value[0]?.id || 0, alias: '', weight: 100, priority: 1 }
  showMemberModal.value = true
}

function editMember(member: PoolMember) {
  editingMemberId.value = member.id
  memberForm.value = {
    channel_id: member.channel_id,
    alias: member.alias || '',
    weight: member.weight,
    priority: member.priority
  }
  showMemberModal.value = true
}

async function saveMember() {
  if (!currentPool.value) return
  try {
    if (editingMemberId.value) {
      await updatePoolMember(currentPool.value.id, editingMemberId.value, memberForm.value)
    } else {
      await createPoolMember(currentPool.value.id, memberForm.value)
    }
    showMemberModal.value = false
    showMembers(currentPool.value)
  } catch (e: any) {
    console.error('保存成员失败:', e)
    alert('保存失败: ' + (e.response?.data?.detail || e.message))
  }
}

async function deleteMember(id: number) {
  if (!currentPool.value) return
  if (!confirm('确定删除成员 #' + id + '?')) return
  try {
    await deletePoolMember(currentPool.value.id, id)
    showMembers(currentPool.value)
  } catch (e: any) {
    console.error('删除成员失败:', e)
  }
}

onMounted(() => {
  loadPools(1)
  loadChannels()
})
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
