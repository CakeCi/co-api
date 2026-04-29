<template>
  <span class="health-badge" :class="statusClass">
    <span class="dot"></span>
    {{ statusText }}
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  health: {
    circuit_open?: boolean
    success_rate?: number
    consecutive_failures?: number
  } | null
}>()

const statusClass = computed(() => {
  if (!props.health) return 'unknown'
  if (props.health.circuit_open) return 'critical'
  if ((props.health.success_rate ?? 100) < 50) return 'warning'
  return 'healthy'
})

const statusText = computed(() => {
  if (!props.health) return '未知'
  if (props.health.circuit_open) return '熔断'
  if ((props.health.success_rate ?? 100) < 50) return '警告'
  return '健康'
})
</script>

<style scoped>
.health-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 4px;
}

.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.healthy {
  color: #00ff41;
  background: rgba(0, 255, 65, 0.1);
}

.healthy .dot {
  background: #00ff41;
}

.warning {
  color: #ffaa00;
  background: rgba(255, 170, 0, 0.1);
}

.warning .dot {
  background: #ffaa00;
}

.critical {
  color: #ff4444;
  background: rgba(255, 68, 68, 0.1);
}

.critical .dot {
  background: #ff4444;
}

.unknown {
  color: #888;
  background: rgba(136, 136, 136, 0.1);
}

.unknown .dot {
  background: #888;
}
</style>
