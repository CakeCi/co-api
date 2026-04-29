<template>
  <div class="min-h-screen flex items-center justify-center">
    <div class="w-full max-w-md p-8 content-card">
      <h1 class="text-3xl font-bold glow-text mb-2 text-center">co-api</h1>
      <p class="text-xs text-center mb-8 opacity-70">AI API 网关 // 终端 v2.0</p>
      <div v-if="error" class="text-red-400 text-sm mb-4">{{ error }}</div>
      <div class="mb-4">
        <label class="block text-xs mb-1 opacity-80">用户名</label>
        <input
          v-model="username"
          type="text"
          class="w-full bg-transparent login-input px-3 py-2 text-sm glow-input text-white"
          @keyup.enter="handleLogin"
        />
      </div>
      <div class="mb-6">
        <label class="block text-xs mb-1 opacity-80">密码</label>
        <input
          v-model="password"
          type="password"
          class="w-full bg-transparent login-input px-3 py-2 text-sm glow-input text-white"
          @keyup.enter="handleLogin"
        />
      </div>
      <TerminalButton class="w-full" :loading="loading" @click="handleLogin">
        [ 登录 ]
      </TerminalButton>
      <p class="text-xs text-center mt-4 opacity-50">默认: admin / Admin@1234</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import TerminalButton from '@/components/TerminalButton.vue'

const router = useRouter()
const authStore = useAuthStore()

const username = ref('admin')
const password = ref('Admin@1234')
const error = ref('')
const loading = ref(false)

async function handleLogin() {
  error.value = ''
  loading.value = true
  try {
    await authStore.login(username.value, password.value)
    router.push('/dashboard')
  } catch (e: any) {
    error.value = '登录失败: ' + (e.response?.data?.detail || e.message)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-input {
  border: 1px solid rgba(0, 255, 65, 0.2);
  background: transparent;
  color: white;
}

.login-input:focus {
  outline: none;
  border-color: #00ff41;
  box-shadow: 0 0 12px rgba(0, 255, 65, 0.4);
}
</style>
