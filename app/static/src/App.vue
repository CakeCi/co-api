<template>
  <div class="terminal-app">
    <GlobalLoader />
    <ErrorBoundary>
      <router-view v-slot="{ Component }">
        <transition name="page" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </ErrorBoundary>
  </div>
</template>

<script setup lang="ts">
import GlobalLoader from './components/GlobalLoader.vue'
import ErrorBoundary from './components/ErrorBoundary.vue'
</script>

<style>
:root {
  --green: #0c9;
  --green-dim: #0b8;
  --green-muted: #086;
  --bg: #090d09;
  --bg-card: rgba(0, 20, 8, 0.55);
  --bg-card-hover: rgba(0, 28, 12, 0.65);
  --border: rgba(0, 200, 85, 0.1);
  --border-hover: rgba(0, 200, 85, 0.2);
  --border-focus: rgba(0, 200, 85, 0.3);
  --text: rgba(190, 240, 210, 0.92);
  --text-dim: rgba(170, 220, 190, 0.62);
  --text-soft: rgba(150, 200, 170, 0.4);
  --danger: rgba(255, 100, 100, 0.85);
  --radius: 8px;
  --radius-lg: 12px;
}

.terminal-app {
  min-height: 100vh;
  background: var(--bg);
  color: var(--text);
  font-family: 'SF Mono', 'Cascadia Code', 'Courier New', monospace;
  overflow-x: hidden;
  -webkit-font-smoothing: antialiased;
}

::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--green-muted); border-radius: 2px; }
::-webkit-scrollbar-thumb:hover { background: var(--green-dim); }

.fade-in { animation: fadeIn 0.25s ease-out; }
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }

.page-enter-active,
.page-leave-active { transition: all 0.2s ease; }
.page-enter-from { opacity: 0; transform: translateY(8px); }
.page-leave-to { opacity: 0; transform: translateY(-8px); }
</style>
