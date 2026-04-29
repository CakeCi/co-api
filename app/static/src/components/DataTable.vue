<template>
  <div class="data-table-wrapper">
    <!-- Batch Toolbar -->
    <div v-if="batchable && selectedIds.length > 0" class="batch-toolbar">
      <span class="text-sm">已选择 {{ selectedIds.length }} 项</span>
      <TerminalButton
        v-for="action in batchActions"
        :key="action.key"
        :variant="action.variant || 'default'"
        size="sm"
        @click="$emit('batch', action.key, selectedIds)"
      >
        {{ action.label }}
      </TerminalButton>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="table-skeleton">
      <div v-for="i in skeletonRows" :key="i" class="skeleton-row">
        <Skeleton v-if="batchable" :width="20" :height="20" variant="rectangular" />
        <Skeleton 
          v-for="col in columns" 
          :key="col.key" 
          :width="col.width || '100%'" 
          :height="20"
        />
      </div>
    </div>

    <!-- Empty State -->
    <div v-else-if="!data || data.length === 0" class="empty-state">
      <div class="empty-icon">▤</div>
      <div class="empty-text">{{ emptyText }}</div>
      <div v-if="emptyDescription" class="empty-description">{{ emptyDescription }}</div>
    </div>

    <!-- Virtual Scroll Table -->
      <div v-else class="table-container">
        <table class="w-full text-sm">
          <thead>
            <tr>
              <th v-if="batchable" class="w-10 sticky-header">
                <input
                  type="checkbox"
                  :checked="isAllSelected"
                  @change="toggleSelectAll"
                />
              </th>
              <th
                v-for="col in columns"
                :key="col.key"
                :class="{ 'text-left': col.align !== 'right', 'text-right': col.align === 'right' }"
                class="sticky-header"
              >
                {{ col.title }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="row in data"
              :key="rowKey(row)"
              class="table-row"
              :class="{ 'row-selected': selectedIds.includes(rowKey(row)) }"
            >
              <td v-if="batchable" class="w-10">
                <input
                  type="checkbox"
                  :checked="selectedIds.includes(rowKey(row))"
                  @change="toggleRow(row)"
                />
              </td>
              <td
                v-for="col in columns"
                :key="col.key"
                :class="{ 'text-left': col.align !== 'right', 'text-right': col.align === 'right' }"
              >
                <slot :name="`cell-${col.key}`" :row="row" :value="row[col.key]">
                  {{ formatCell(row[col.key], col.format) }}
                </slot>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import TerminalButton from './TerminalButton.vue'
import Skeleton from './Skeleton.vue'

interface Column {
  key: string
  title: string
  align?: 'left' | 'right'
  format?: 'number' | 'date' | 'status'
  width?: string | number
}

interface BatchAction {
  key: string
  label: string
  variant?: 'default' | 'danger'
}

const props = withDefaults(defineProps<{
  data: any[]
  columns: Column[]
  rowKey: (row: any) => number | string
  batchable?: boolean
  batchActions?: BatchAction[]
  loading?: boolean
  emptyText?: string
  emptyDescription?: string
  rowHeight?: number
  overscan?: number
}>(), {
  batchable: false,
  batchActions: () => [],
  loading: false,
  emptyText: '暂无数据',
  emptyDescription: '',
  rowHeight: 48,
  overscan: 5
})

const emit = defineEmits<{
  (e: 'batch', action: string, ids: (number | string)[]): void
}>()

const selectedIds = ref<(number | string)[]>([])

// 骨架屏行数
const skeletonRows = computed(() => 5)

// 数据变化时清空选中
watch(() => props.data, () => {
  selectedIds.value = []
}, { deep: true })

const isAllSelected = computed(() => {
  if (props.data.length === 0) return false
  return props.data.every(row => selectedIds.value.includes(props.rowKey(row)))
})

function toggleSelectAll() {
  if (isAllSelected.value) {
    selectedIds.value = []
  } else {
    selectedIds.value = props.data.map(row => props.rowKey(row))
  }
}

function toggleRow(row: any) {
  const key = props.rowKey(row)
  const index = selectedIds.value.indexOf(key)
  if (index > -1) {
    selectedIds.value.splice(index, 1)
  } else {
    selectedIds.value.push(key)
  }
}

function formatCell(value: any, format?: string): string {
  if (value == null) return '-'
  switch (format) {
    case 'number':
      return typeof value === 'number' ? value.toLocaleString() : String(value)
    case 'date':
      return value ? new Date(value.replace(' ', 'T') + '+08:00').toLocaleString('zh-CN') : '-'
    case 'status':
      return value === 1 ? '启用' : '禁用'
    default:
      return String(value)
  }
}

// 移除虚拟滚动，使用普通分页
</script>

<style scoped>
.data-table-wrapper {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.batch-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  padding: 8px 12px;
  background: rgba(0, 255, 65, 0.05);
  border: 1px solid rgba(0, 255, 65, 0.2);
  border-radius: 4px;
}

.table-container {
  flex: 1;
  overflow-y: auto;
  overflow-x: auto;
  position: relative;
}

.sticky-header {
  position: sticky;
  top: 0;
  background: rgba(0, 20, 0, 0.95);
  z-index: 10;
  backdrop-filter: blur(4px);
}

table th,
table td {
  border: 1px solid rgba(0, 255, 65, 0.2);
  padding: 8px;
  height: v-bind(rowHeight + 'px');
  box-sizing: border-box;
}

table th {
  background: rgba(0, 255, 65, 0.1);
  font-weight: 600;
}

.table-row {
  transition: background-color 0.2s ease, transform 0.2s ease;
}

.table-row:hover {
  background: rgba(0, 255, 65, 0.08) !important;
  transform: translateX(4px);
}

.row-selected {
  background: rgba(0, 255, 65, 0.15) !important;
}

input[type="checkbox"] {
  accent-color: #00ff41;
  cursor: pointer;
}

/* Skeleton Loading */
.table-skeleton {
  padding: 16px;
}

.skeleton-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid rgba(0, 255, 65, 0.1);
}

/* Empty State */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 24px;
  color: var(--text-secondary);
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
  opacity: 0.6;
}

.empty-text {
  font-size: 16px;
  font-weight: 500;
  margin-bottom: 8px;
}

.empty-description {
  font-size: 14px;
  opacity: 0.7;
}

/* Scrollbar Styling */
.table-container::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

.table-container::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.3);
}

.table-container::-webkit-scrollbar-thumb {
  background: rgba(0, 255, 65, 0.3);
  border-radius: 3px;
}

.table-container::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 255, 65, 0.5);
}
</style>
