<template>
  <div class="echart-wrapper">
    <!-- Loading State -->
    <div v-if="loading" class="chart-loading">
      <div class="chart-spinner">
        <svg viewBox="0 0 24 24">
          <circle class="spinner-track" cx="12" cy="12" r="10" fill="none" stroke-width="2"/>
          <circle class="spinner-head" cx="12" cy="12" r="10" fill="none" stroke-width="2"/>
        </svg>
      </div>
      <div class="loading-text">加载图表...</div>
    </div>
    
    <!-- Empty State -->
    <div v-else-if="isEmpty" class="chart-empty">
      <div class="empty-icon">■</div>
      <div class="empty-text">{{ emptyText }}</div>
    </div>
    
    <!-- Chart Container -->
    <div 
      v-show="!loading && !isEmpty"
      ref="chartRef" 
      class="echart-container"
      :class="{ 'chart-fade-in': !loading }"
    ></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick, computed } from 'vue'
import * as echarts from 'echarts'

interface Props {
  option: echarts.EChartsOption
  loading?: boolean
  emptyText?: string
  theme?: 'dark' | 'light'
  autoResize?: boolean
  animation?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  emptyText: '暂无数据',
  theme: 'dark',
  autoResize: true,
  animation: true
})

const chartRef = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null

const isEmpty = computed(() => {
  if (!props.option) return true
  const opt = props.option as any
  if (opt.series && Array.isArray(opt.series)) {
    return opt.series.every((s: any) => !s.data || s.data.length === 0)
  }
  return false
})

function initChart() {
  if (!chartRef.value || chart) return
  
  chart = echarts.init(chartRef.value, props.theme, {
    renderer: 'canvas'
  })
  
  if (props.option) {
    const option = {
      ...props.option,
      animation: props.animation,
      animationDuration: 1000,
      animationEasing: 'cubicOut' as const
    }
    chart.setOption(option, true)
  }
}

function updateChart() {
  if (chart && props.option && !isEmpty.value) {
    const option = {
      ...props.option,
      animation: props.animation,
      animationDuration: 800,
      animationEasing: 'cubicOut' as const
    }
    chart.setOption(option, {
      notMerge: false,
      lazyUpdate: false,
      silent: false
    })
  }
}

function handleResize() {
  if (props.autoResize) {
    chart?.resize()
  }
}

// 使用 ResizeObserver 更精确地监听容器大小变化
let resizeObserver: ResizeObserver | null = null

onMounted(() => {
  nextTick(() => {
    if (!isEmpty.value && !props.loading) {
      initChart()
    }
  })
  
  window.addEventListener('resize', handleResize)
  
  if (chartRef.value && typeof ResizeObserver !== 'undefined') {
    resizeObserver = new ResizeObserver(() => {
      handleResize()
    })
    resizeObserver.observe(chartRef.value)
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  resizeObserver?.disconnect()
  
  if (chart) {
    chart.dispose()
    chart = null
  }
})

watch(() => props.option, () => {
  if (isEmpty.value || props.loading) {
    if (chart) {
      chart.dispose()
      chart = null
    }
    return
  }
  
  if (!chart) {
    nextTick(() => initChart())
  } else {
    updateChart()
  }
}, { deep: true })

watch(() => props.loading, (newVal) => {
  if (!newVal && !isEmpty.value) {
    nextTick(() => {
      if (!chart) initChart()
    })
  }
})
</script>

<style scoped>
.echart-wrapper {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 200px;
}

.echart-container {
  width: 100%;
  height: 100%;
  min-height: 200px;
}

.chart-fade-in {
  animation: chartFadeIn 0.6s ease-out;
}

@keyframes chartFadeIn {
  from {
    opacity: 0;
    transform: scale(0.95);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

/* Loading State */
.chart-loading {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  background: rgba(5, 8, 5, 0.8);
}

.chart-spinner {
  width: 40px;
  height: 40px;
}

.chart-spinner svg {
  width: 100%;
  height: 100%;
  animation: spinner-rotate 1s linear infinite;
}

.chart-spinner .spinner-track {
  stroke: rgba(0, 255, 65, 0.2);
}

.chart-spinner .spinner-head {
  stroke: var(--primary-green, #00ff41);
  stroke-dasharray: 20, 80;
  stroke-dashoffset: 0;
  animation: spinner-dash 1.5s ease-in-out infinite;
}

.loading-text {
  color: var(--text-secondary);
  font-size: 14px;
}

/* Empty State */
.chart-empty {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.empty-icon {
  font-size: 32px;
  opacity: 0.5;
}

.empty-text {
  color: var(--text-secondary);
  font-size: 14px;
}

@keyframes spinner-rotate {
  to {
    transform: rotate(360deg);
  }
}

@keyframes spinner-dash {
  0% {
    stroke-dasharray: 1, 80;
    stroke-dashoffset: 0;
  }
  50% {
    stroke-dasharray: 40, 80;
    stroke-dashoffset: -20;
  }
  100% {
    stroke-dasharray: 40, 80;
    stroke-dashoffset: -60;
  }
}
</style>
