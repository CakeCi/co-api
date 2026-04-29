import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getMe, login as apiLogin } from '@/api'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const isLoggedIn = ref(false)
  const user = ref({ username: 'admin' })

  async function checkAuth() {
    if (!token.value) return false
    try {
      await getMe()
      isLoggedIn.value = true
      return true
    } catch {
      token.value = ''
      localStorage.removeItem('token')
      isLoggedIn.value = false
      return false
    }
  }

  async function login(username: string, password: string) {
    const res = await apiLogin(username, password)
    token.value = res.token
    localStorage.setItem('token', token.value)
    isLoggedIn.value = true
    return true
  }

  function logout() {
    token.value = ''
    localStorage.removeItem('token')
    isLoggedIn.value = false
    window.location.reload()
  }

  return { token, isLoggedIn, user, checkAuth, login, logout }
})
