import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import router from '@/router'
import { get, post } from '@/api/client'

export interface User {
  id: string; username: string; display_name: string; department: string; role: string
  email?: string; avatar_url?: string
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const user = ref<User | null>(null)

  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.role === 'super_admin' || user.value?.role === 'dept_admin')

  async function login(username: string, password: string) {
    const data: any = await post('/api/auth/login', { username, password })
    token.value = data.token
    user.value = data.user
    localStorage.setItem('token', data.token)
    // Redirect to the original page — only allow safe relative paths
    const redirectParam = new URLSearchParams(window.location.search).get('redirect')
    let redirect = '/'
    if (redirectParam && redirectParam.startsWith('/') && !redirectParam.startsWith('//')) {
      redirect = redirectParam
    }
    router.push(redirect)
  }

  async function fetchMe() {
    if (!token.value) return
    try {
      const data: any = await get('/api/auth/me')
      user.value = data
    } catch { logout() }
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('token')
    router.push('/login')
  }

  return { token, user, isLoggedIn, isAdmin, login, fetchMe, logout }
})
