import axios from 'axios'

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
