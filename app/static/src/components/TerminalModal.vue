<template>
  <div v-if="modelValue" class="modal-overlay" @click.self="close">
    <div class="modal-content" :class="size">
      <div v-if="title" class="modal-header">
        <h3 class="text-lg font-bold glow">{{ title }}</h3>
      </div>
      <div class="modal-body">
        <slot />
      </div>
      <div v-if="$slots.footer" class="modal-footer">
        <slot name="footer" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  modelValue: boolean
  title?: string
  size?: 'sm' | 'md' | 'lg' | 'xl'
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
}>()

function close() {
  emit('update:modelValue', false)
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(5, 8, 5, 0.95);
  z-index: 50;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}

.modal-content {
  background: #0a0f0a;
  border: 1px solid rgba(0, 255, 65, 0.4);
  padding: 24px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 0 8px rgba(0, 255, 65, 0.3), inset 0 0 8px rgba(0, 255, 65, 0.1);
}

.modal-content.sm { width: 100%; max-width: 400px; }
.modal-content.md { width: 100%; max-width: 560px; }
.modal-content.lg { width: 100%; max-width: 720px; }
.modal-content.xl { width: 100%; max-width: 960px; }

.modal-header {
  margin-bottom: 16px;
}

.modal-footer {
  margin-top: 16px;
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

.glow {
  text-shadow: 0 0 8px #00ff41, 0 0 16px rgba(0, 255, 65, 0.5);
}
</style>
