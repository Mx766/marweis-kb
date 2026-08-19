<template>
  <div ref="fpPageRef" class="fp-page">
    <div class="fp-head">
      <button class="fp-back" @click="goBack">← 返回</button>
      <span class="fp-title">{{ title }}</span>
      <button v-if="showOnlyOffice" class="fp-oo" @click="loadOnlyOffice">用 OnlyOffice 打开</button>
      <button class="fp-fs" @click="toggleFullscreen" :title="isFs ? '退出全屏' : '全屏查看'">
        <el-icon :size="16"><FullScreen /></el-icon>
        {{ isFs ? '退出全屏' : '全屏' }}
      </button>
    </div>
    <div id="fp-editor" class="fp-editor" v-show="!pdfUrl && !markdownSource && !error"></div>
    <iframe v-if="pdfUrl" class="fp-pdf" :src="pdfUrl" @load="onPdfLoad"></iframe>
    <MarkdownPreview v-if="markdownSource" :source="markdownSource" class="fp-md" />
    <div v-if="loading" class="fp-msg">
      <div class="fp-msg-inner">
        <el-icon class="is-loading" :size="30"><Loading /></el-icon>
        <p>正在加载在线预览…</p>
      </div>
    </div>
    <div v-else-if="error" class="fp-msg fp-err">{{ error }}</div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { get } from '@/api/client'
import { Loading, FullScreen } from '@element-plus/icons-vue'
import MarkdownPreview from '@/components/MarkdownPreview.vue'

const route = useRoute()
const router = useRouter()
const title = ref('')
const loading = ref(true)
const error = ref('')
const pdfUrl = ref('')
const markdownSource = ref('')
const fpPageRef = ref<HTMLElement | null>(null)
const isFs = ref(false)
const showOnlyOffice = ref(false)
let docEditor: any = null
let _readyTimer: ReturnType<typeof setTimeout> | null = null
let _startedAt = 0

function hideLoading() {
  // 最短显示 700ms，避免加载太快一闪而过
  const elapsed = Date.now() - _startedAt
  const delay = Math.max(0, 700 - elapsed)
  setTimeout(() => { loading.value = false }, delay)
}

function loadScript(url: string) {
  return new Promise<void>((resolve, reject) => {
    if ((window as any).DocsAPI) return resolve()
    const s = document.createElement('script')
    s.src = `${url}/web-apps/apps/api/documents/api.js`
    s.onload = () => resolve()
    s.onerror = () => reject(new Error('script failed'))
    document.head.appendChild(s)
  })
}

function goBack() {
  const from = route.query.from as string | undefined
  if (from) {
    router.push(`/files?folder=${encodeURIComponent(from)}`)
  } else if (window.history.length > 1) {
    router.back()
  } else {
    router.push('/files')
  }
}

function onFsChange() {
  isFs.value = !!document.fullscreenElement
}

function toggleFullscreen() {
  const el = fpPageRef.value
  if (!el) return
  if (!document.fullscreenElement) {
    el.requestFullscreen?.().then(() => { isFs.value = true }).catch(() => {})
  } else {
    document.exitFullscreen?.().then(() => { isFs.value = false }).catch(() => {})
  }
}

function onPdfLoad() {
  hideLoading()
}

onBeforeUnmount(() => {
  if (_readyTimer) { clearTimeout(_readyTimer) }
  document.removeEventListener('fullscreenchange', onFsChange)
  if (pdfUrl.value.startsWith('blob:')) URL.revokeObjectURL(pdfUrl.value)
})

onMounted(async () => {
  _startedAt = Date.now()
  document.addEventListener('fullscreenchange', onFsChange)
  const ext = ((route.query.ext as string) || '').toLowerCase()
  const officeSet = ['doc','docx','xls','xlsx','ppt','pptx','odt','ods','odp','txt','csv']
  showOnlyOffice.value = officeSet.includes(ext)
  const id = route.params.id as string
  // md：拉取原文用 Markdown 排版渲染；其余默认 PDF 预览（快，转一次缓存后秒开）
  if (ext === 'md') {
    const token = sessionStorage.getItem('token') || localStorage.getItem('token') || ''
    try {
      const r = await fetch(`/api/files/${id}/raw`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!r.ok) throw new Error(String(r.status))
      markdownSource.value = await r.text()
      title.value = title.value || '文档预览'
      hideLoading()
    } catch {
      error.value = '预览加载失败，请下载查看'
      hideLoading()
    }
    return
  }
  try {
    const t: any = await get(`/api/files/${id}/preview-token`)
    const base = `/api/files/${id}/preview?token=${encodeURIComponent(t.token)}`
    const deadline = Date.now() + 120000
    for (;;) {
      const r = await fetch(base)
      if (r.status === 200) {
        pdfUrl.value = base
        title.value = title.value || '文档预览'
        return // loading 由 iframe @load 收起
      }
      if (r.status === 202) {
        if (Date.now() > deadline) {
          error.value = '预览生成超时，请下载查看'
          hideLoading()
          return
        }
        await new Promise((res) => setTimeout(res, 2000))
        continue
      }
      const d = await r.json().catch(() => ({}))
      error.value = d?.detail || '预览加载失败，请下载查看'
      hideLoading()
      return
    }
  } catch (e: any) {
    error.value = e?.response?.data?.detail || '预览加载失败，请下载查看'
    hideLoading()
  }
})

async function loadOnlyOffice() {
  const id = route.params.id as string
  loading.value = true
  error.value = ''
  pdfUrl.value = ''
  try {
    const resp: any = await get(`/api/files/${id}/onlyoffice-config`)
    title.value = resp.config.document.title || '文档预览'
    await loadScript(resp.documentServerUrl)
    await new Promise((r) => setTimeout(r, 80))
    docEditor = new (window as any).DocsAPI.DocEditor('fp-editor', {
      ...resp.config,
      token: resp.token,
      events: {
        onAppReady: () => {
          hideLoading()
          if (_readyTimer) { clearTimeout(_readyTimer); _readyTimer = null }
        },
        onError: () => {
          hideLoading()
          if (_readyTimer) { clearTimeout(_readyTimer); _readyTimer = null }
        },
      },
    })
    _readyTimer = setTimeout(hideLoading, 30000)
  } catch (e: any) {
    hideLoading()
    error.value = e?.response?.data?.detail || 'OnlyOffice 加载失败，请下载查看'
  }
}
</script>

<style scoped>
.fp-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f5f7fa;
  overflow: hidden;
}
.fp-head {
  flex: none;
  display: flex;
  align-items: center;
  gap: 12px;
  height: 48px;
  padding: 0 16px;
  background: #fff;
  border-bottom: 1px solid #e5e7eb;
}
.fp-back {
  border: 1px solid #d0d5dd;
  background: #fff;
  border-radius: 6px;
  padding: 4px 12px;
  cursor: pointer;
}
.fp-title {
  font-size: 14px;
  font-weight: 600;
  color: #1a1a2e;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}
.fp-fs {
  flex: none;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border: 1px solid #d0d5dd;
  background: #fff;
  border-radius: 6px;
  padding: 5px 12px;
  cursor: pointer;
  font-size: 13px;
  color: #333;
}
.fp-fs:hover { border-color: var(--color-primary); color: var(--color-primary); }
.fp-oo {
  flex: none;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border: 1px solid var(--color-primary);
  background: var(--color-primary);
  color: #fff;
  border-radius: 6px;
  padding: 5px 12px;
  cursor: pointer;
  font-size: 13px;
}
.fp-oo:hover { opacity: .9; }
.fp-page:fullscreen { overflow: auto; background: #fff; }
.fp-page:fullscreen .fp-head { display: none; }
.fp-page:fullscreen .fp-editor,
.fp-page:fullscreen > iframe {
  height: 100vh;
}
.fp-editor {
  flex: 1 1 auto;
  min-height: 0;
}
.fp-editor iframe,
.fp-page > iframe {
  width: 100%;
  height: calc(100vh - 48px);
  border: 0;
}
.fp-pdf {
  flex: 1 1 auto;
  min-height: 0;
}
.fp-md {
  flex: 1 1 auto;
  overflow: auto;
  padding: 24px 32px;
  background: #fff;
}
.fp-msg {
  position: fixed;
  inset: 0;
  z-index: 20;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(245, 247, 250, 0.95);
  color: #666;
}
.fp-msg-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 28px 40px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 8px 30px rgba(0,0,0,.08);
  color: var(--color-primary);
}
.fp-msg-inner p { margin: 0; font-size: 14px; color: #555; }
.fp-err {
  color: #dc2626;
}
</style>
