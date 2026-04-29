<template>
  <div class="skeleton" :class="{ pulse: animated }" :style="skeletonStyle">
    <slot />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  width?: string | number
  height?: string | number
  borderRadius?: string | number
  animated?: boolean
  variant?: 'text' | 'circular' | 'rectangular'
}

const props = withDefaults(defineProps<Props>(), {
  animated: true,
  variant: 'text',
  borderRadius: '4px'
})

const skeletonStyle = computed(() => {
  const style: Record<string, string> = {}
  
  if (props.width) {
    style.width = typeof props.width === 'number' ? `${props.width}px` : props.width
  }
  if (props.height) {
    style.height = typeof props.height === 'number' ? `${props.height}px` : props.height
  }
  
  if (props.variant === 'circular') {
    style.borderRadius = '50%'
  } else if (props.variant === 'text') {
    style.borderRadius = typeof props.borderRadius === 'number' 
      ? `${props.borderRadius}px` 
      : props.borderRadius
  } else {
    style.borderRadius = '0'
  }
  
  return style
})
</script>

<style scoped>
.skeleton {
  background: linear-gradient(
    90deg,
    var(--skeleton-base) 25%,
    var(--skeleton-highlight) 50%,
    var(--skeleton-base) 75%
  );
  background-size: 200% 100%;
  display: inline-block;
}

.skeleton.pulse {
  animation: skeleton-loading 1.5s ease-in-out infinite;
}

@keyframes skeleton-loading {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}
</style>
