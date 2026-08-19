import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import router from '@/router'
import { get, post } from '@/api/client'

export interface User {
  id: string; username: string; display_name: string; department: string; role: string
  employee_id?: string
  email?: string; avatar_url?: string
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref(sessionStorage.getItem('token') || '')
  const user = ref<User | null>(null)

  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.role === 'super_admin' || user.value?.role === 'dept_admin')
  const isSuperAdmin = computed(() => user.value?.role === 'super_admin')

  async function login(username: string, password: string) {
    const data: any = await post('/api/auth/login', { username, password })
    token.value = data.token
    user.value = data.user
    // sessionStorage may fail in some browsers (IE kernel, compatibility mode)
    try { sessionStorage.setItem('token', data.token) } catch { localStorage.setItem('token', data.token) }
    // 只有超管进管理后台；部门管理员落前台（本部门视图）
    const redirectParam = new URLSearchParams(window.location.search).get('redirect')
    let redirect = '/'
    if (redirectParam && redirectParam.startsWith('/') && !redirectParam.startsWith('//')) {
      redirect = redirectParam
    } else if (data.user?.role === 'super_admin') {
      redirect = '/admin'
    }
    // Fallback: if router.push silently fails (old browsers), use location.href
    try {
      await router.push(redirect)
    } catch {
      window.location.href = redirect
    }
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
    sessionStorage.removeItem('token')
    router.push('/login')
  }

  return { token, user, isLoggedIn, isAdmin, isSuperAdmin, login, fetchMe, logout }
})
