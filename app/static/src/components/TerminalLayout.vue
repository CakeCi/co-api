<template>
  <div class="terminal-layout">
    <!-- Mobile Header -->
    <header v-if="isMobile" class="mobile-header">
      <button class="menu-toggle" @click="toggleSidebar">
        <span class="menu-icon" :class="{ open: sidebarOpen }">
          <span></span>
          <span></span>
          <span></span>
        </span>
      </button>
      <div class="mobile-title">
        <span>co-api</span>
      </div>
      <button class="search-toggle" @click="openSearch">
        ?
      </button>
    </header>

    <!-- Sidebar -->
    <aside
      class="terminal-sidebar"
      :class="{
        'sidebar-open': sidebarOpen,
        'sidebar-collapsed': isCollapsed && !isMobile,
        'mobile-sidebar': isMobile
      }"
    >
      <div class="sidebar-header">
        <div class="logo">
          <h2 class="logo-text">co-api</h2>
          <p class="logo-version">v2.0.0</p>
        </div>
        <button
          v-if="!isMobile"
          class="collapse-btn"
          @click="toggleCollapse"
        >
          <span :class="{ 'rotate-180': isCollapsed }">◀</span>
        </button>
      </div>

      <nav class="sidebar-nav">
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="nav-item"
          :class="{ active: $route.path === item.path }"
          @click="handleNavClick"
        >
          <span class="nav-icon">{{ item.icon }}</span>
          <span v-if="!isCollapsed" class="nav-label">{{ item.label }}</span>
          <!-- 活跃指示器 - 参考 octopus layoutId -->
          <span v-if="$route.path === item.path" class="active-indicator"></span>
        </router-link>
      </nav>

      <div class="sidebar-footer">
        <div v-if="!isCollapsed" class="user-info">
          <div class="user-name">{{ authStore.user?.username || 'Admin' }}</div>
          <div class="user-role">管理员</div>
        </div>
        <TerminalButton
          :variant="isCollapsed ? 'ghost' : 'default'"
          :size="isCollapsed ? 'sm' : 'md'"
          @click="authStore.logout"
        >
          <span v-if="isCollapsed">X</span>
          <span v-else>退出登录</span>
        </TerminalButton>
      </div>
    </aside>

    <!-- Overlay for mobile -->
    <div
      v-if="isMobile && sidebarOpen"
      class="sidebar-overlay"
      @click="closeSidebar"
    ></div>

    <!-- Content -->
    <main class="main-content" :class="{ 'sidebar-collapsed': isCollapsed && !isMobile }">
      <div class="content-header">
        <div class="breadcrumb">
          <span v-for="(crumb, index) in breadcrumbs" :key="index">
            <router-link v-if="crumb.path" :to="crumb.path">{{ crumb.label }}</router-link>
            <span v-else>{{ crumb.label }}</span>
            <span v-if="index < breadcrumbs.length - 1" class="separator">/</span>
          </span>
        </div>
        <div class="header-actions">
          <button class="action-btn" @click="openSearch">
            ?
          </button>
          <button class="action-btn" @click="refreshPage">
            R
          </button>
        </div>
      </div>

      <div class="content-body">
        <slot />
      </div>
    </main>

    <!-- Bottom Navigation - 参考 octopus NavBar (移动端) -->
    <nav v-if="isMobile" class="bottom-nav">
      <router-link
        v-for="item in navItems"
        :key="item.path"
        :to="item.path"
        class="bottom-nav-item"
        :class="{ active: $route.path === item.path }"
      >
        <span class="bottom-nav-icon">{{ item.icon }}</span>
        <span class="bottom-nav-label">{{ item.label }}</span>
        <!-- 活跃指示器 -->
        <span v-if="$route.path === item.path" class="bottom-active-indicator"></span>
      </router-link>
    </nav>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import TerminalButton from './TerminalButton.vue'

const authStore = useAuthStore()
const route = useRoute()

const isMobile = ref(false)
const sidebarOpen = ref(false)
const isCollapsed = ref(false)

const navItems = [
  { path: '/dashboard', label: '数据看板', icon: '■' },
  { path: '/channels', label: '渠道管理', icon: '▸' },
  { path: '/pools', label: '模型池', icon: '◆' },
  { path: '/tokens', label: 'API令牌', icon: '◇' },
  { path: '/image-gen', label: 'AI生图', icon: '▤' },
  { path: '/stats', label: '统计报表', icon: '▣' },
  { path: '/logs', label: '请求记录', icon: '▬' },
  { path: '/docs', label: 'API文档', icon: '◈' }
]

const breadcrumbs = computed(() => {
  const items: Array<{ label: string; path?: string }> = [{ label: '首页', path: '/' }]
  const current = navItems.find(item => item.path === route.path)
  if (current) {
    items.push({ label: current.label })
  }
  return items
})

function checkMobile() {
  isMobile.value = window.innerWidth < 768
  if (!isMobile.value) {
    sidebarOpen.value = false
  }
}

function toggleSidebar() {
  sidebarOpen.value = !sidebarOpen.value
}

function closeSidebar() {
  sidebarOpen.value = false
}

function toggleCollapse() {
  isCollapsed.value = !isCollapsed.value
  localStorage.setItem('sidebar-collapsed', String(isCollapsed.value))
}

function handleNavClick() {
  if (isMobile.value) {
    sidebarOpen.value = false
  }
}

function openSearch() {
  const event = new CustomEvent('global-search-open')
  window.dispatchEvent(event)
}

function refreshPage() {
  window.location.reload()
}

onMounted(() => {
  checkMobile()
  window.addEventListener('resize', checkMobile)

  const saved = localStorage.getItem('sidebar-collapsed')
  if (saved) {
    isCollapsed.value = saved === 'true'
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', checkMobile)
})
</script>

<style scoped>
.terminal-layout { display: flex; height: 100vh; overflow: hidden; }

.mobile-header { display: none; position: fixed; top: 0; left: 0; right: 0; height: 56px; background: #080c08; border-bottom: 1px solid var(--border); align-items: center; padding: 0 16px; z-index: 100; }
.menu-toggle { background: none; border: none; color: var(--green); cursor: pointer; padding: 8px; }
.menu-icon { display: flex; flex-direction: column; gap: 4px; width: 20px; }
.menu-icon span { display: block; height: 2px; background: var(--green); transition: all 0.3s ease; }
.menu-icon.open span:nth-child(1) { transform: rotate(45deg) translate(4px,4px); }
.menu-icon.open span:nth-child(2) { opacity: 0; }
.menu-icon.open span:nth-child(3) { transform: rotate(-45deg) translate(4px,-4px); }
.mobile-title { flex: 1; text-align: center; font-weight: bold; color: var(--green); }
.search-toggle { background: none; border: none; color: var(--text-dim); cursor: pointer; padding: 8px; font-size: 18px; }

.terminal-sidebar { width: 240px; min-width: 240px; background: #060a06; border-right: 1px solid var(--border); display: flex; flex-direction: column; transition: width 0.2s; z-index: 200; }
.terminal-sidebar.sidebar-collapsed { width: 64px; min-width: 64px; }
.sidebar-header { display: flex; align-items: center; justify-content: space-between; padding: 16px; border-bottom: 1px solid rgba(0,180,100,0.06); }
.logo { overflow: hidden; }
.logo-text { font-size: 18px; font-weight: bold; color: var(--green); margin: 0; white-space: nowrap; }
.logo-version { font-size: 10px; color: var(--text-soft); margin: 4px 0 0; }
.collapse-btn { background: none; border: 1px solid var(--border); color: var(--text-dim); cursor: pointer; padding: 4px 8px; border-radius: 6px; transition: all 0.15s; }
.collapse-btn:hover { border-color: var(--border-hover); color: var(--green); }
.collapse-btn span { display: inline-block; transition: transform 0.2s; }
.rotate-180 { transform: rotate(180deg); }
.sidebar-nav { flex: 1; padding: 8px; overflow-y: auto; }
.nav-item { display: flex; align-items: center; gap: 12px; padding: 10px 12px; font-size: 14px; text-decoration: none; color: var(--text-dim); transition: all 0.15s; border-radius: 8px; margin-bottom: 2px; position: relative; }
.nav-item:hover { background: rgba(0,180,100,0.06); color: var(--text); }
.nav-item.active { background: rgba(0,180,100,0.08); color: var(--green); }
.active-indicator { position: absolute; left: 0; top: 50%; transform: translateY(-50%); width: 3px; height: 20px; background: var(--green); border-radius: 0 2px 2px 0; animation: indicatorSlide 0.25s ease-out; }
@keyframes indicatorSlide { from { height: 0; opacity: 0; } to { height: 20px; opacity: 1; } }
.nav-icon { font-size: 18px; width: 24px; text-align: center; flex-shrink: 0; }
.nav-label { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.sidebar-footer { padding: 16px; border-top: 1px solid rgba(0,180,100,0.06); }
.user-info { margin-bottom: 12px; }
.user-name { font-size: 14px; color: var(--text); font-weight: 500; }
.user-role { font-size: 12px; color: var(--text-soft); margin-top: 2px; }

.main-content { flex: 1; overflow: auto; background: var(--bg); }
.content-header { display: flex; align-items: center; justify-content: space-between; padding: 12px 24px; border-bottom: 1px solid rgba(0,180,100,0.06); background: #080c08; position: sticky; top: 0; z-index: 10; }
.breadcrumb { font-size: 14px; color: var(--text-dim); }
.breadcrumb a { color: var(--green); text-decoration: none; }
.breadcrumb a:hover { opacity: 0.8; }
.separator { margin: 0 8px; opacity: 0.4; }
.header-actions { display: flex; gap: 8px; }
.action-btn { background: none; border: 1px solid var(--border); color: var(--text-dim); cursor: pointer; padding: 5px 10px; border-radius: 6px; font-size: 15px; transition: all 0.15s; }
.action-btn:hover { border-color: var(--border-hover); color: var(--green); }
.content-body { padding: 24px; min-height: calc(100vh - 120px); }

.bottom-nav { display: none; position: fixed; bottom: 0; left: 0; right: 0; height: 60px; background: #040a06; border-top: 1px solid var(--border); z-index: 100; justify-content: space-around; align-items: center; }
.bottom-nav-item { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 3px; padding: 4px 8px; text-decoration: none; color: var(--text-dim); transition: all 0.15s; position: relative; flex: 1; }
.bottom-nav-item.active { color: var(--green); }
.bottom-nav-icon { font-size: 18px; transition: transform 0.15s; }
.bottom-nav-item.active .bottom-nav-icon { transform: scale(1.05); }
.bottom-nav-label { font-size: 10px; }
.bottom-active-indicator { position: absolute; top: 0; left: 50%; transform: translateX(-50%); width: 20px; height: 2px; background: var(--green); border-radius: 0 0 2px 2px; animation: bottomIndicatorSlide 0.25s ease-out; }
@keyframes bottomIndicatorSlide { from { width: 0; opacity: 0; } to { width: 20px; opacity: 1; } }

@media (max-width: 768px) {
  .terminal-layout { flex-direction: column; padding-top: 56px; padding-bottom: 60px; }
  .mobile-header { display: flex; }
  .terminal-sidebar { position: fixed; top: 56px; left: 0; bottom: 0; width: 280px; transform: translateX(-100%); transition: transform 0.25s; }
  .terminal-sidebar.sidebar-open { transform: translateX(0); }
  .sidebar-overlay { position: fixed; top: 56px; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.65); backdrop-filter: blur(4px); z-index: 150; }
  .main-content { width: 100%; }
  .content-header { padding: 12px 16px; }
  .content-body { padding: 16px; }
  .breadcrumb { font-size: 12px; }
  .bottom-nav { display: flex; }
}

.sidebar-nav::-webkit-scrollbar { width: 3px; }
.sidebar-nav::-webkit-scrollbar-track { background: transparent; }
.sidebar-nav::-webkit-scrollbar-thumb { background: var(--green-muted); border-radius: 2px; }
</style>
