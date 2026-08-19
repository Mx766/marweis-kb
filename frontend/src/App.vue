<template>
  <router-view />
  <el-dialog v-model="annOpen" title="📢 更新公告" width="560px" :close-on-click-modal="false" append-to-body>
    <div v-if="annCurrent" class="ann-box">
      <div class="ann-title">{{ annCurrent.title }}</div>
      <div class="ann-date">{{ annCurrent.created_at ? new Date(annCurrent.created_at).toLocaleString('zh-CN', { hour12: false }) : '' }}</div>
      <div class="ann-content">{{ annCurrent.content }}</div>
    </div>
    <template #footer>
      <el-button type="primary" @click="dismissAnn">知道了</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { get } from '@/api/client'

const ANN_LS_KEY = 'kb_ann_seen'
const annOpen = ref(false)
const annCurrent = ref<any>(null)

async function loadAnnouncements() {
  try {
    const token = sessionStorage.getItem('token') || localStorage.getItem('token')
    if (!token) return
    const r: any = await get('/api/announcements')
    const items = (r as any).items || []
    if (!items.length) return
    const seen = localStorage.getItem(ANN_LS_KEY) || ''
    // 只弹最新一条未读公告；知道了之后记录该条 ID，下次有新公告再弹
    const newest = items[0]
    if (newest && newest.id !== seen) {
      annCurrent.value = newest
      annOpen.value = true
    }
  } catch { /* 未登录/接口异常不阻塞页面 */ }
}

function dismissAnn() {
  if (annCurrent.value?.id) localStorage.setItem(ANN_LS_KEY, annCurrent.value.id)
  annOpen.value = false
}

function hexToHsl(hex: string): [number, number, number] {
  let r = parseInt(hex.slice(1, 3), 16) / 255
  let g = parseInt(hex.slice(3, 5), 16) / 255
  let b = parseInt(hex.slice(5, 7), 16) / 255
  const max = Math.max(r, g, b), min = Math.min(r, g, b)
  let h = 0, s = 0, l = (max + min) / 2
  if (max !== min) {
    const d = max - min
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min)
    if (max === r) h = ((g - b) / d + (g < b ? 6 : 0)) / 6
    else if (max === g) h = ((b - r) / d + 2) / 6
    else h = ((r - g) / d + 4) / 6
  }
  return [Math.round(h * 360), Math.round(s * 100), Math.round(l * 100)]
}

function hslToHex(h: number, s: number, l: number): string {
  s /= 100; l /= 100
  const a = s * Math.min(l, 1 - l)
  const f = (n: number) => {
    const k = (n + h / 30) % 12
    return Math.round((l - a * Math.max(Math.min(k - 3, 9 - k, 1), -1)) * 255)
  }
  return '#' + [f(0), f(8), f(4)].map(v => v.toString(16).padStart(2, '0')).join('')
}

function lighten(hex: string, amount: number): string {
  const [h, s, l] = hexToHsl(hex)
  return hslToHex(h, s, Math.min(100, l + amount))
}

function darken(hex: string, amount: number): string {
  const [h, s, l] = hexToHsl(hex)
  return hslToHex(h, s, Math.max(5, l - amount))
}

async function loadTheme() {
  try {
    const settings: any = await get('/api/admin/settings')
    const primary = settings?.primary_color
    const accent = settings?.accent_color || '#ffc001'
    if (!primary) return
    const root = document.documentElement
    const vars: [string, string][] = [
      ['--color-primary', primary],
      ['--color-primary-light', lighten(primary, 12)],
      ['--color-primary-dark', darken(primary, 18)],
      ['--color-accent', accent],
      ['--color-accent-light', lighten(accent, 15)],
      ['--el-color-primary', primary],
      ['--el-color-primary-light-3', lighten(primary, 12)],
      ['--el-color-primary-light-5', lighten(primary, 25)],
      ['--el-color-primary-light-7', lighten(primary, 38)],
      ['--el-color-primary-light-8', lighten(primary, 45)],
      ['--el-color-primary-light-9', lighten(primary, 52)],
      ['--el-color-primary-dark-2', darken(primary, 10)],
    ]
    for (const [k, v] of vars) root.style.setProperty(k, v)
  } catch { /* guest or settings not configured */ }
}

onMounted(() => {
  loadTheme()
  loadAnnouncements()
  document.addEventListener('keydown', handleKeydown)
})
onUnmounted(() => document.removeEventListener('keydown', handleKeydown))

function handleKeydown(e: KeyboardEvent) {
  // Ctrl+K / Cmd+K: focus search box
  if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
    e.preventDefault()
    const el = document.querySelector('.header-search input, .hero-search-input') as HTMLInputElement
    if (el) el.focus()
  }
  // /: focus search box (when not typing in an input)
  if (e.key === '/' && !['INPUT','TEXTAREA','SELECT'].includes((e.target as HTMLElement)?.tagName || '')) {
    e.preventDefault()
    const el = document.querySelector('.header-search input, .hero-search-input') as HTMLInputElement
    if (el) el.focus()
  }
}

onMounted(() => document.addEventListener('keydown', handleKeydown))
onUnmounted(() => document.removeEventListener('keydown', handleKeydown))
</script>

<style scoped>
.ann-box { max-height: 60vh; overflow-y: auto; }
.ann-title { font-size: 16px; font-weight: 700; color: var(--color-text-primary); margin-bottom: 4px; }
.ann-date { font-size: 12px; color: #999; margin-bottom: 10px; }
.ann-content { font-size: 13px; line-height: 1.8; color: #444; white-space: pre-wrap; word-break: break-word; }
</style>
