import axios from 'axios'

// ── API Response Types ────────────────────────────────────

export interface UserProfile {
  id: string
  username: string
  display_name: string
  employee_id?: string
  department: string
  role: string
  email?: string
  avatar_url?: string
}

export interface LoginResponse {
  token: string
  user: UserProfile
  expires_at: string
}

export interface DocumentItem {
  id: string
  title: string
  category_id: string | null
  file_type: 'file' | 'link'
  original_filename: string
  file_size: number
  file_ext: string
  mime_type: string
  tags: string[] | null
  summary: string | null
  source: string | null
  source_url: string | null
  effective_date: string | null
  version: string | null
  uploader_name: string
  view_count: number
  created_at: string
  updated_at: string
}

export interface DocumentDetail extends DocumentItem {
  preview_path: string | null
  original_path: string | null
  download_count: number
  is_favorited: boolean
}

export interface DocumentListResponse {
  items: DocumentItem[]
  total: number
  page: number
  size: number
  pages: number
}

export interface SearchResult {
  items: DocumentItem[]
  total: number
  query: string
  page: number
  size: number
}

export interface CategoryNode {
  id: string
  name: string
  parent_id: string | null
  sort_order: number
  icon: string | null
  visible_departments: string[] | null
  description: string | null
  children: CategoryNode[]
  document_count: number
}

export interface UserItem {
  id: string
  username: string
  display_name: string
  employee_id?: string
  department: string
  role: string
  email?: string
  is_active: boolean
  created_at: string
}

export interface UserListResponse {
  items: UserItem[]
  total: number
  page: number
  size: number
}

export interface PersonalStats {
  total_uploads: number
  total_favorites: number
  total_history: number
}

// ── Axios Client ──────────────────────────────────────────

const client = axios.create({
  baseURL: '',
  timeout: 30000,
})

client.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

client.interceptors.response.use(
  (res) => res.data,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
      // Use relative path navigation instead of full page reload
      const currentPath = window.location.pathname
      if (currentPath !== '/login') {
        window.location.replace(`/login?redirect=${encodeURIComponent(currentPath)}`)
      }
    }
    return Promise.reject(err)
  }
)

export async function get<T = any>(url: string, params?: Record<string, any>): Promise<T> {
  // Flatten params into query string params
  if (params) {
    const search = new URLSearchParams()
    for (const key of Object.keys(params)) {
      const val = params[key]
      if (val !== undefined && val !== null && val !== '') {
        search.set(key, String(val))
      }
    }
    const qs = search.toString()
    if (qs) url = url + (url.includes('?') ? '&' : '?') + qs
  }
  return client.get(url) as Promise<T>
}

export async function post<T = any>(url: string, data?: any): Promise<T> {
  return client.post(url, data) as T
}

export async function put<T = any>(url: string, data?: any): Promise<T> {
  return client.put(url, data) as T
}

export async function del<T = any>(url: string): Promise<T> {
  return client.delete(url) as T
}

export { client }
export default client
