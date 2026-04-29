import { createRouter, createWebHashHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

// Lazy load with chunk names for better caching
const LoginView = () => import(/* webpackChunkName: "login" */ '@/views/LoginView.vue')
const DashboardView = () => import(/* webpackChunkName: "dashboard" */ '@/views/DashboardView.vue')
const ChannelsView = () => import(/* webpackChunkName: "channels" */ '@/views/ChannelsView.vue')
const PoolsView = () => import(/* webpackChunkName: "pools" */ '@/views/PoolsView.vue')
const TokensView = () => import(/* webpackChunkName: "tokens" */ '@/views/TokensView.vue')
const LogsView = () => import(/* webpackChunkName: "logs" */ '@/views/LogsView.vue')
const DocsView = () => import(/* webpackChunkName: "docs" */ '@/views/DocsView.vue')
const ImageGenView = () => import(/* webpackChunkName: "image-gen" */ '@/views/ImageGenView.vue')
const StatsView = () => import(/* webpackChunkName: "stats" */ '@/views/StatsView.vue')

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: LoginView,
    meta: { public: true }
  },
  {
    path: '/',
    redirect: '/dashboard'
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: DashboardView,
    meta: { 
      requiresAuth: true,
      title: '数据看板',
      keepAlive: true
    }
  },
  {
    path: '/channels',
    name: 'Channels',
    component: ChannelsView,
    meta: { 
      requiresAuth: true,
      title: '渠道管理',
      keepAlive: true
    }
  },
  {
    path: '/pools',
    name: 'Pools',
    component: PoolsView,
    meta: { 
      requiresAuth: true,
      title: '模型池',
      keepAlive: true
    }
  },
  {
    path: '/tokens',
    name: 'Tokens',
    component: TokensView,
    meta: { 
      requiresAuth: true,
      title: 'API令牌',
      keepAlive: true
    }
  },
  {
    path: '/logs',
    name: 'Logs',
    component: LogsView,
    meta: { 
      requiresAuth: true,
      title: '请求记录',
      keepAlive: false
    }
  },
  {
    path: '/docs',
    name: 'Docs',
    component: DocsView,
    meta: { 
      requiresAuth: true,
      title: 'API文档',
      keepAlive: true
    }
  },
  {
    path: '/image-gen',
    name: 'ImageGen',
    component: ImageGenView,
    meta: {
      requiresAuth: true,
      title: 'AI生图',
      keepAlive: true
    }
  },
  {
    path: '/stats',
    name: 'Stats',
    component: StatsView,
    meta: {
      requiresAuth: true,
      title: '统计报表',
      keepAlive: true
    }
  }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) {
      return savedPosition
    }
    if (to.hash) {
      return { el: to.hash, behavior: 'smooth' }
    }
    return { top: 0, behavior: 'smooth' }
  }
})

// Navigation guards
router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()
  
  // Update document title
  if (to.meta.title) {
    document.title = `${to.meta.title} - co-api`
  } else {
    document.title = 'co-api'
  }
  
  // Public routes
  if (to.meta.public) {
    // Already logged in users redirect to dashboard
    if (authStore.isLoggedIn) {
      next('/dashboard')
      return
    }
    next()
    return
  }
  
  // Auth required routes
  if (to.meta.requiresAuth) {
    if (!authStore.isLoggedIn) {
      const isAuth = await authStore.checkAuth()
      if (!isAuth) {
        next('/login')
        return
      }
    }
  }
  
  next()
})

// After navigation
router.afterEach((to, from) => {
  // Close mobile sidebar if open
  const event = new CustomEvent('router-navigated', { detail: { to, from } })
  window.dispatchEvent(event)
})

export default router
