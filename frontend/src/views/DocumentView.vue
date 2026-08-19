<template>
  <div class="document-page" v-loading="loading">
    <div class="doc-nav-bar">
      <el-button @click="goBack" class="back-btn">
        <el-icon><ArrowLeft /></el-icon> 返回上级
      </el-button>
      <el-breadcrumb separator=">">
        <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
        <el-breadcrumb-item v-if="doc?.category_id && doc?.category_name"
          :to="{ path: '/category/' + doc.category_id }">{{ doc.category_name }}</el-breadcrumb-item>
        <el-breadcrumb-item v-else :to="{ path: '/category' }">知识库</el-breadcrumb-item>
        <el-breadcrumb-item>{{ doc?.title }}</el-breadcrumb-item>
      </el-breadcrumb>
    </div>

    <el-result v-if="errorMsg" icon="error" :title="errorMsg" :sub-title="errorSub">
      <template #extra>
        <el-button type="primary" @click="$router.push('/')">返回首页</el-button>
        <el-button @click="$router.push('/login')" v-if="!auth.isLoggedIn">去登录</el-button>
      </template>
    </el-result>

    <div class="doc-layout" v-if="doc">
      <div class="doc-main">
        <!-- Preview Area -->
        <div class="doc-preview-area">
          <!-- Link / Article type -->
          <template v-if="doc.file_type === 'link'">
            <div class="article-view">
              <h1 class="article-title">{{ doc.title }}</h1>
              <p v-if="doc.summary" class="article-summary">{{ doc.summary }}</p>

              <!-- Has previewable attachment → show preview button prominently -->
              <div v-if="previewableAttachment" class="article-preview-hero">
                <div class="preview-hero-icon">
                  <el-icon :size="48"><DocumentIcon /></el-icon>
                </div>
                <h2>附件预览</h2>
                <p>{{ previewableAttachment.title }}</p>
                <p class="preview-hero-meta">{{ previewableAttachment.file_ext?.toUpperCase() }} · {{ formatSize(previewableAttachment.file_size) }}</p>
                <el-button type="primary" size="large" @click="$router.push(`/document/${previewableAttachment.id}`)">
                  <el-icon><View /></el-icon> 打开预览
                </el-button>
              </div>

              <!-- No attachment → show article text or empty state -->
              <div v-else-if="doc.content_text" class="article-body-wrapper">
                <button v-if="hasTable(doc.content_text)" class="fs-trigger" @click="toggleTableFullscreen" title="全屏查看表格">
                  <el-icon :size="16"><FullScreen /></el-icon>
                </button>
                <div class="reading-frame">
                  <div ref="articleBodyRef" class="article-body" v-html="renderContent(doc.content_text)"></div>
                </div>
              </div>
              <div v-else class="reading-frame reading-frame--empty">
                <p>本文档为外部链接引用，正文内容请访问原文查看。</p>
              </div>

              <!-- All Attachments -->
              <div v-if="doc.related_attachments?.length" class="article-attachments">
                <h3>附件 ({{ doc.related_attachments.length }})</h3>
                <div class="att-grid">
                  <div v-for="att in doc.related_attachments" :key="att.id" class="att-card"
                    @click="$router.push(`/document/${att.id}`)">
                    <span class="att-card-icon" :style="'background:' + iconBg(att.file_ext)">{{ extLabel(att.file_ext) }}</span>
                    <div class="att-card-info">
                      <span class="att-card-name">{{ att.title }}</span>
                      <span class="att-card-meta">{{ formatSize(att.file_size) }} · {{ att.file_ext?.toUpperCase() }}</span>
                    </div>
                  </div>
                </div>
              </div>

              <div class="article-actions">
                <a v-if="doc.source_url" :href="doc.source_url" target="_blank" rel="noopener">
                  <el-button type="primary" size="small">访问原文</el-button></a>
                <el-button size="small" @click="copyLink">复制链接</el-button>
              </div>
              <div v-if="isEmbeddable(doc.source_url)" class="article-embed">
                <iframe :src="doc.source_url" frameborder="0" sandbox="allow-scripts allow-popups" referrerpolicy="no-referrer"></iframe>
              </div>

              <!-- Table fullscreen overlay -->
              <Teleport to="body">
                <div v-if="tableFullscreen" class="fs-overlay" @click.self="tableFullscreen=false">
                  <div class="fs-toolbar">
                    <span class="fs-title">{{ doc.title }}</span>
                    <div class="fs-search">
                      <el-icon :size="14"><Search /></el-icon>
                      <input v-model="contentFilter" type="text" placeholder="搜索..."
                        @input="filterTableContent" class="content-search-input" />
                    </div>
                    <button class="fs-close" @click="tableFullscreen=false">
                      <el-icon :size="20"><Close /></el-icon>
                    </button>
                  </div>
                  <div class="fs-body" ref="fsBodyRef" v-html="renderContent(doc.content_text || '')"></div>
                </div>
              </Teleport>
            </div>
          </template>

          <!-- Image preview -->
          <template v-else-if="isImage">
            <div class="image-preview">
              <el-image :src="previewUrl" :alt="doc.title" fit="contain" style="max-height:600px" />
            </div>
          </template>

          <!-- Video preview -->
          <template v-else-if="isVideo">
            <div class="video-preview">
              <video ref="videoRef" controls style="max-width:100%;width:100%" :src="previewUrl"
                @loadedmetadata="onVideoLoaded">
                您的浏览器不支持此视频格式
              </video>
              <div class="video-ctrl-bar">
                <span class="video-ctrl-label">倍速</span>
                <button v-for="s in [0.5, 0.75, 1, 1.25, 1.5, 2]" :key="s"
                  class="speed-btn" :class="{ active: playbackRate === s }"
                  @click="setPlaybackRate(s)">{{ s }}x</button>
              </div>
            </div>
          </template>

          <!-- Audio preview -->
          <template v-else-if="isAudio">
            <div class="audio-preview">
              <audio controls style="width:100%" :src="previewUrl" />
            </div>
          </template>

          <!-- Document placeholder with rich info — now with inline preview -->
          <template v-else>
            <div class="preview-placeholder">
              <!-- OnlyOffice online preview (Word/Excel/PPT) -->
              <div v-if="onlyOfficeConfig" class="onlyoffice-preview">
                <div id="onlyoffice-editor" class="onlyoffice-editor"></div>
                <button class="preview-fullscreen-btn" @click="openOnlyOfficeFullscreen" title="全屏预览">
                  <el-icon :size="18"><FullScreen /></el-icon>
                </button>
                <div v-if="onlyOfficeLoading" class="onlyoffice-loading">
                  <el-icon class="is-loading" :size="30"><Loading /></el-icon>
                  <p>正在加载在线预览...</p>
                </div>
              </div>

              <div v-if="showOnlyOfficeBtn" class="oo-switch-bar">
                <el-button size="small" type="primary" plain @click="loadOnlyOffice">用 OnlyOffice 打开</el-button>
              </div>

              <MarkdownPreview v-if="markdownSource" :source="markdownSource" />

              <template v-if="!onlyOfficeConfig && !markdownSource">
              <!-- Unsupported format -->
              <div v-if="!isPreviewSupported && !previewUrl && !previewLoading" class="preview-unsupported">
                <el-result icon="info" :title="'此文件格式不支持在线预览'" :sub-title="'.' + (doc.file_ext?.toUpperCase() || '') + ' 格式'">
                  <template #extra>
                    <el-button v-if="canDownload" type="primary" @click="doDownload">下载原件查看</el-button>
                  </template>
                </el-result>
              </div>

              <!-- Error: no preview available (not a format issue, just can't get preview) -->
              <div v-else-if="!previewUrl && !previewLoading && !previewTimeout" class="preview-error">
                <el-result icon="warning" title="预览不可用"
                  sub-title="无法获取预览，请尝试下载查看">
                  <template #extra>
                    <el-button v-if="canDownload" type="primary" @click="doDownload">下载原件</el-button>
                  </template>
                </el-result>
              </div>

              <!-- Timeout with no URL yet (API call timed out) -->
              <div v-else-if="previewTimeout && !previewUrl" class="preview-error">
                <el-result icon="warning" title="预览生成较慢"
                  sub-title="该文档可能较大或暂不支持转换，可先下载原件；后台会继续尝试，稍后刷新即可预览">
                  <template #extra>
                    <el-button @click="loadDoc">刷新页面</el-button>
                    <el-button v-if="canDownload" type="primary" @click="doDownload">下载原件</el-button>
                  </template>
                </el-result>
              </div>

              <!-- Waiting for preview-token API (no URL yet) -->
              <div v-else-if="previewLoading && !previewUrl" class="preview-loading">
                <el-icon class="is-loading" :size="36"><Loading /></el-icon>
                <p>正在生成预览，首次转换可能较慢，请稍候...</p>
              </div>

              <!-- === Iframe always rendered when previewUrl is set (MUST be in DOM for @load to fire) === -->
              <div v-if="previewUrl" class="inline-preview">
                <div v-if="previewLoading" class="preview-loading-overlay">
                  <el-icon class="is-loading" :size="36"><Loading /></el-icon>
                  <p>正在加载预览...</p>
                  <p class="hint">文档较大时首次转换可能需要 1-2 分钟，转换完成后会自动加载</p>
                </div>
                <button class="preview-fullscreen-btn" @click="fullscreenPreview = true" title="全屏预览">
                  <el-icon :size="18"><FullScreen /></el-icon>
                </button>
                <iframe
                  :src="previewUrl"
                  width="100%"
                  height="700px"
                  style="border:none;border-radius:8px"
                  title="文档预览"
                  @load="onPreviewLoaded"
                ></iframe>
              </div>

              <!-- Document metadata — shown when preview is ready or format unsupported -->
              <div v-if="previewUrl || (!isPreviewSupported && !previewUrl && !previewLoading && !previewTimeout)" class="preview-page" :class="{ 'has-preview': !!previewUrl }">
                <div class="file-type-badge">
                  <el-tag :color="fileIconColor(doc.file_ext)" effect="dark" size="large">
                    {{ doc.file_ext?.toUpperCase() }}
                  </el-tag>
                </div>
                <h2>{{ doc.title }}</h2>
                <div v-if="doc.summary" class="preview-summary">{{ doc.summary }}</div>
                <div class="preview-meta-grid">
                  <div v-if="doc.source" class="meta-item">
                    <span class="meta-label">来源</span>
                    <span class="meta-value">{{ doc.source }}</span>
                  </div>
                  <div v-if="doc.effective_date" class="meta-item">
                    <span class="meta-label">发布日期</span>
                    <span class="meta-value">{{ doc.effective_date }}</span>
                  </div>
                  <div v-if="doc.version" class="meta-item">
                    <span class="meta-label">版本</span>
                    <span class="meta-value">{{ doc.version }}</span>
                  </div>
                  <div class="meta-item">
                    <span class="meta-label">文件大小</span>
                    <span class="meta-value">{{ formatSize(doc.file_size) }}</span>
                  </div>
                </div>
                <div v-if="doc.tags?.length" class="preview-tags">
                  <el-tag v-for="t in doc.tags" :key="t" size="small">{{ t }}</el-tag>
                </div>
              </div>
              </template>
            </div>
          </template>
        </div>

        <!-- Toolbar -->
        <div class="doc-toolbar">
          <el-button
            v-if="doc.file_type !== 'link' && canDownload"
            type="primary"
            :icon="DownloadIcon"
            @click="doDownload"
          >下载原件</el-button>
          <el-button :icon="LinkIcon" @click="copyLink">复制链接</el-button>
          <el-button
            :icon="StarIcon"
            :type="isFavorited ? 'warning' : 'default'"
            @click="toggleFavorite"
          >{{ isFavorited ? '已收藏' : '收藏' }}</el-button>
        </div>

        <!-- Meta info -->
        <div class="doc-meta">
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item label="上传者">{{ doc.uploader_name }}</el-descriptions-item>
            <el-descriptions-item label="发布日期" v-if="doc.effective_date">{{ doc.effective_date }}</el-descriptions-item>
            <el-descriptions-item label="更新时间">{{ formatDate(doc.updated_at) }}</el-descriptions-item>
            <el-descriptions-item label="文件格式">{{ doc.file_ext?.toUpperCase() || '网页链接' }}</el-descriptions-item>
            <el-descriptions-item label="文件大小" v-if="doc.file_size">{{ formatSize(doc.file_size) }}</el-descriptions-item>
            <el-descriptions-item label="来源">{{ doc.source || '-' }}</el-descriptions-item>
            <el-descriptions-item label="版本">{{ doc.version || '-' }}</el-descriptions-item>
            <el-descriptions-item label="浏览次数">{{ doc.view_count }}</el-descriptions-item>
            <el-descriptions-item label="下载次数">{{ doc.download_count }}</el-descriptions-item>
          </el-descriptions>
        </div>
      </div>

      <!-- Sidebar: Related documents -->
      <div class="doc-sidebar" v-if="relatedDocs.length">
        <h3>相关推荐</h3>
        <div v-for="r in relatedDocs" :key="r.id" class="related-item" @click="$router.push(`/document/${r.id}`)">
          <h4>{{ r.title }}</h4>
          <p>{{ r.uploader_name }} · {{ r.tags?.slice(0,2).join(', ') }}</p>
        </div>
      </div>
    </div>

    <!-- Fullscreen preview overlay -->
    <Transition name="fs-preview">
      <div v-if="fullscreenPreview" class="fullscreen-overlay" @click.self="fullscreenPreview = false">
        <button class="fs-close-btn" @click="fullscreenPreview = false">
          <el-icon :size="24"><Close /></el-icon>
        </button>
        <iframe
          :src="previewUrl"
          class="fs-iframe"
          title="全屏预览"
        ></iframe>
      </div>
    </Transition>

    <!-- OnlyOffice fullscreen preview overlay -->
    <Transition name="fs-preview">
      <div v-if="onlyOfficeFullscreen" class="fullscreen-overlay" @click.self="closeOnlyOfficeFullscreen">
        <button class="fs-close-btn" @click="closeOnlyOfficeFullscreen">
          <el-icon :size="24"><Close /></el-icon>
        </button>
        <div id="onlyoffice-editor-fs" class="oo-fs-editor"></div>
        <div v-if="fsLoading" class="fs-loading">
          <el-icon class="is-loading" :size="30"><Loading /></el-icon>
          <p>正在加载在线预览...</p>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Link, Loading, Download as DownloadIcon, Link as LinkIcon, Star as StarIcon, FullScreen, Close, ArrowRight, ArrowLeft, Search, View, Document as DocumentIcon } from '@element-plus/icons-vue'
import { get, post, del } from '@/api/client'
import MarkdownPreview from '@/components/MarkdownPreview.vue'
import { useAuthStore } from '@/stores/auth'
import dayjs from 'dayjs'
import { ElMessage } from 'element-plus'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const doc = ref<any>(null)
// 员工在 培训资料/结题项目文件备份 栏目下不可下载（后端已限制，前端隐藏按钮）
const canDownload = computed(() => doc.value?.downloadable !== false)
const loading = ref(true)
const isFavorited = ref(false)
const errorMsg = ref('')
const errorSub = ref('')
const relatedDocs = ref<any[]>([])
// First previewable attachment (docx/doc/pdf) for link-type articles
const previewableAttachment = computed(() => {
  if (doc.value?.file_type !== 'link' || !doc.value?.related_attachments?.length) return null
  const PREVIEW_EXTS = ['pdf','docx','doc','xlsx','xls','pptx','ppt']
  return doc.value.related_attachments.find((a: any) => PREVIEW_EXTS.includes(a.file_ext?.toLowerCase())) || null
})

const IMG_EXTS = ['jpg','jpeg','png','gif','tiff','tif','bmp','svg','webp']
const VID_EXTS = ['mp4','avi','mov','wmv','webm']
const AUD_EXTS = ['mp3','wav','wma','flac','ogg']
const PREVIEWABLE_EXTS = ['pdf','doc','docx','xls','xlsx','ppt','pptx','odt','odp','ods','txt','csv','md']

const isImage = computed(() => IMG_EXTS.includes(doc.value?.file_ext?.toLowerCase() || ''))
const isVideo = computed(() => VID_EXTS.includes(doc.value?.file_ext?.toLowerCase() || ''))
const isAudio = computed(() => AUD_EXTS.includes(doc.value?.file_ext?.toLowerCase() || ''))
const isPreviewSupported = computed(() => PREVIEWABLE_EXTS.includes(doc.value?.file_ext?.toLowerCase() || ''))
const showOnlyOfficeBtn = computed(() => {
  const ext = doc.value?.file_ext?.toLowerCase() || ''
  return ONLYOFFICE_EXTS.includes(ext) && ext !== 'md' && !onlyOfficeConfig.value
})

// Preview URL with short-lived scoped token (not the full JWT)
const previewUrl = ref('')
const markdownSource = ref('')
const previewToken = ref('')
const previewLoading = ref(false)
const previewTimeout = ref(false)
const fullscreenPreview = ref(false)
const onlyOfficeFullscreen = ref(false)
const fsLoading = ref(false)
const onlyOfficeConfig = ref<any>(null)
const onlyOfficeServerUrl = ref('')
const onlyOfficeLoading = ref(false)
const videoRef = ref<HTMLVideoElement | null>(null)
const playbackRate = ref(1)
let _previewTimer: ReturnType<typeof setTimeout> | null = null
let docEditor: any = null
let fsDocEditor: any = null
let _ooScriptPromise: Promise<void> | null = null
let _ooReadyTimer: ReturnType<typeof setTimeout> | null = null
let _fsReadyTimer: ReturnType<typeof setTimeout> | null = null
const ONLYOFFICE_EXTS = ['doc','docx','xls','xlsx','ppt','pptx','odt','ods','odp','txt','csv','md']

function setPlaybackRate(rate: number) {
  playbackRate.value = rate
  if (videoRef.value) videoRef.value.playbackRate = rate
}
function onVideoLoaded() {
  if (videoRef.value) videoRef.value.playbackRate = playbackRate.value
}

function destroyOnlyOffice() {
  if (docEditor?.destroyEditor) {
    try { docEditor.destroyEditor() } catch { /* ignore */ }
  }
  docEditor = null
  onlyOfficeConfig.value = null
  onlyOfficeServerUrl.value = ''
  onlyOfficeLoading.value = false
}

async function openOnlyOfficeFullscreen() {
  if (!onlyOfficeConfig.value) return
  onlyOfficeFullscreen.value = true
  fsLoading.value = true
  await nextTick()
  const win = window as any
  if (!win.DocsAPI || fsDocEditor) return
  fsDocEditor = new win.DocsAPI.DocEditor('onlyoffice-editor-fs', {
    ...onlyOfficeConfig.value,
    token: onlyOfficeConfig.value.token,
    events: {
      onAppReady: () => {
        fsLoading.value = false
        if (_fsReadyTimer) { clearTimeout(_fsReadyTimer); _fsReadyTimer = null }
      },
      onError: () => {
        fsLoading.value = false
        if (_fsReadyTimer) { clearTimeout(_fsReadyTimer); _fsReadyTimer = null }
      },
    },
  })
  _fsReadyTimer = setTimeout(() => { fsLoading.value = false }, 30000)
}

function closeOnlyOfficeFullscreen() {
  if (fsDocEditor) {
    try { fsDocEditor.destroy() } catch { /* noop */ }
    fsDocEditor = null
  }
  if (_fsReadyTimer) { clearTimeout(_fsReadyTimer); _fsReadyTimer = null }
  onlyOfficeFullscreen.value = false
}

function loadOnlyOfficeScript(url: string): Promise<void> {
  const apiUrl = `${url}/web-apps/apps/api/documents/api.js`
  const win = window as any
  if (win.DocsAPI) return Promise.resolve()
  if (_ooScriptPromise) return _ooScriptPromise
  _ooScriptPromise = new Promise((resolve, reject) => {
    const script = document.createElement('script')
    script.src = apiUrl
    script.onload = () => resolve()
    script.onerror = () => { _ooScriptPromise = null; reject(new Error('OnlyOffice script failed')) }
    document.head.appendChild(script)
  })
  return _ooScriptPromise
}

async function initOnlyOffice(config: any, serverUrl: string) {
  onlyOfficeLoading.value = true
  try {
    await loadOnlyOfficeScript(serverUrl)
    await new Promise((resolve) => setTimeout(resolve, 80))
    if (docEditor) destroyOnlyOffice()
    onlyOfficeConfig.value = { ...config }
    await nextTick()
    const container = document.getElementById('onlyoffice-editor')
    const win = window as any
    if (!container || !win.DocsAPI) throw new Error('OnlyOffice container unavailable')
    docEditor = new win.DocsAPI.DocEditor('onlyoffice-editor', {
      ...config,
      token: config.token,
      events: {
        onAppReady: () => {
          onlyOfficeLoading.value = false
          if (_ooReadyTimer) { clearTimeout(_ooReadyTimer); _ooReadyTimer = null }
        },
        onError: () => {
          onlyOfficeLoading.value = false
          if (_ooReadyTimer) { clearTimeout(_ooReadyTimer); _ooReadyTimer = null }
        },
      },
    })
    // 兜底：30 秒未就绪也收起 loading，避免永久转圈
    _ooReadyTimer = setTimeout(() => { onlyOfficeLoading.value = false }, 30000)
  } catch {
    onlyOfficeConfig.value = null
    onlyOfficeLoading.value = false
    // Fall back to the PDF conversion preview.
    await fetchPdfPreview(doc.value?.id)
  }
}

async function fetchPdfPreview(docId: string) {
  if (!docId) return
  // Document preview: use preview-token + 后台转换轮询
  previewLoading.value = true
  previewTimeout.value = false
  try {
    const resp: any = await get(`/api/documents/${docId}/preview-token`)
    previewToken.value = resp.token
    const base = `/api/documents/${docId}/preview?token=${encodeURIComponent(resp.token)}`
    let attempts = 0
    // 轮询：202=后台转换中，200=预览就绪；最多约 10 分钟
    for (;;) {
      let status = 0
      try {
        const r = await fetch(base, { method: 'GET' })
        status = r.status
        if (status === 200) {
          previewUrl.value = base
          previewLoading.value = false
          break
        }
      } catch { /* retry */ }
      if (status === 202) {
        attempts += 1
        if (attempts >= 12) {
          previewUrl.value = ''
          previewLoading.value = false
          previewTimeout.value = true
          break
        }
        await new Promise((res) => setTimeout(res, 5000))
        continue
      }
      previewUrl.value = ''
      previewLoading.value = false
      previewTimeout.value = true
      break
    }
  } catch {
    previewUrl.value = ''
    previewLoading.value = false
  }
}

async function fetchPreviewToken(docId: string) {
  if (!auth.isLoggedIn) {
    previewUrl.value = ''
    previewLoading.value = false
    return
  }

  // Video/audio/image: use stream endpoint (inline presigned URL, browser plays natively)
  const ext = doc.value?.file_ext?.toLowerCase() || ''
  if (VID_EXTS.includes(ext) || AUD_EXTS.includes(ext) || IMG_EXTS.includes(ext)) {
    previewLoading.value = false
    try {
      const resp: any = await get(`/api/documents/${docId}/download-token`)
      previewUrl.value = `/api/documents/${docId}/stream?token=${encodeURIComponent(resp.token)}`
    } catch {
      previewUrl.value = ''
    }
    return
  }

  // Markdown 文档：直接渲染排版后的内容（marked + DOMPurify）
  if (ext === 'md') {
    const md = doc.value?.markdown_content || doc.value?.content_text || ''
    if (md && md.trim().length > 10) {
      markdownSource.value = md
      return
    }
  }

  // Word/Excel/PPT：默认走 Gotenberg PDF 预览（快、单个资源），OnlyOffice 改为手动切换
  if (ONLYOFFICE_EXTS.includes(ext) && ext !== 'md') {
    await fetchPdfPreview(docId)
    return
  }

  // md 走 OnlyOffice（文本打开）
  if (ONLYOFFICE_EXTS.includes(ext)) {
    previewLoading.value = true
    try {
      const resp: any = await get(`/api/documents/${docId}/onlyoffice-config`)
      onlyOfficeServerUrl.value = resp.documentServerUrl
      await initOnlyOffice({ ...resp.config, token: resp.token }, resp.documentServerUrl)
      return
    } catch {
      onlyOfficeConfig.value = null
      onlyOfficeLoading.value = false
      // Fall through to PDF conversion preview
    }
  }

  await fetchPdfPreview(docId)
}

async function loadOnlyOffice() {
  if (onlyOfficeConfig.value) return
  const docId = doc.value?.id
  if (!docId) return
  previewUrl.value = ''
  previewLoading.value = true
  try {
    const resp: any = await get(`/api/documents/${docId}/onlyoffice-config`)
    onlyOfficeServerUrl.value = resp.documentServerUrl
    await initOnlyOffice({ ...resp.config, token: resp.token }, resp.documentServerUrl)
  } catch {
    onlyOfficeConfig.value = null
    onlyOfficeLoading.value = false
    ElMessage.error('OnlyOffice 加载失败，仍显示 PDF 预览')
    await fetchPdfPreview(docId)
  }
}

function onPreviewLoaded() {
  previewLoading.value = false
  if (_previewTimer) clearTimeout(_previewTimer)
}

const fileColors: Record<string,string> = {
  pdf:'#ef4444',doc:'#3b82f6',docx:'#3b82f6',xls:'#16a34a',xlsx:'#16a34a',ppt:'#f97316',pptx:'#f97316',
  zip:'#78716c',rar:'#78716c',sevenz:'#78716c',
}
function fileIconColor(ext: string) { return fileColors[ext?.toLowerCase()] || 'var(--color-primary)' }

function formatDate(d: string) { return dayjs(d).format('YYYY-MM-DD HH:mm') }
function formatSize(bytes: number | undefined) { if (!bytes && bytes !== 0) return '-'; return bytes > 1048576 ? `${(bytes/1048576).toFixed(1)} MB` : `${(bytes/1024).toFixed(1)} KB` }
const iconBgMap: Record<string,string> = { pdf:'#ef4444', doc:'#3b82f6', docx:'#3b82f6', xls:'#16a34a', xlsx:'#16a34a', ppt:'#f97316', link:'#0891b2', txt:'#6b7280', jpg:'#a855f7', png:'#a855f7', mp4:'#8b5cf6', zip:'#78716c' }
function iconBg(ext: string) { return iconBgMap[ext?.toLowerCase()] || '#95a5a6' }
function extLabel(ext: string) { return (ext || 'FILE').toUpperCase().slice(0, 3) }

const contentFilter = ref('')
const filteredRowCount = ref(0)
const tableFullscreen = ref(false)
const articleBodyRef = ref<HTMLElement>()
const fsBodyRef = ref<HTMLElement>()

function toggleTableFullscreen() {
  tableFullscreen.value = !tableFullscreen.value
}

function hasTable(text: string) {
  // Check if the content has a markdown table (header row + separator + data rows)
  return /\|[-:\s|]+\|/.test(text)  // has separator like |---|---|
}
function filterTableContent() {
  if (!articleBodyRef.value) return
  const filter = contentFilter.value.toLowerCase().trim()
  const rows = articleBodyRef.value.querySelectorAll('.md-table tbody tr')
  let count = 0
  rows.forEach((row) => {
    const el = row as HTMLElement
    if (!filter) {
      el.style.display = ''
      count++
    } else if (el.textContent?.toLowerCase().includes(filter)) {
      el.style.display = ''
      count++
    } else {
      el.style.display = 'none'
    }
  })
  filteredRowCount.value = count
}

function renderContent(text: string) {
  if (!text) return ''
  let html = text
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')

  // Deduplicate: docx extraction joins duplicate blocks with '---'
  const sep = /(\n-{3,}\n|\n{2}-{3,}\n{2})/
  const parts = html.split(sep)
  if (parts.length >= 2) {
    const firstBlock = parts[0].trim()
    for (let i = 2; i < parts.length; i += 2) {
      if (parts[i].trim().substring(0, 100) === firstBlock.substring(0, 100)) {
        html = parts.slice(0, i).join('')
        break
      }
    }
  }

  // Strip leading docx extraction header: 【filename.doc】
  html = html.replace(/^【[^】]+】(?:附件)?\s*/g, '')
  const lines = html.split('\n')
  const result: string[] = []
  let tableHeader: string[] = []
  let tableRows: string[][] = []
  let inTable = false
  let paraBuf: string[] = []  // accumulate lines for paragraph merging

  function flushPara() {
    const t = paraBuf.join('').trim()
    paraBuf = []
    if (!t) return
    // Chinese section heading: 一、二、三、...  1. 2. ...  （1）（2）... 第X章/节
    if (/^[一二三四五六七八九十]+[、．.]/.test(t) && t.length < 50) {
      result.push(`<h2 class="md-h2">${t}</h2>`)
    } else if (/^（[一二三四五六七八九十\d]+）/.test(t) && t.length < 50) {
      result.push(`<h3 class="md-h3">${t}</h3>`)
    } else if (/^\d+[\.、]/.test(t) && t.length < 60) {
      result.push(`<h3 class="md-h3">${t}</h3>`)
    } else {
      result.push(`<p class="md-p">${t}</p>`)
    }
  }

  function flushTable() {
    if (tableRows.length === 0) return
    let h = ''
    let b = '<tbody>'
    if (tableHeader.length > 0) {
      h = '<thead><tr>' + tableHeader.map(c => `<th>${c.trim()}</th>`).join('') + '</tr></thead>'
    }
    for (const row of tableRows) {
      b += '<tr>' + row.map(c => `<td>${c.trim()}</td>`).join('') + '</tr>'
    }
    b += '</tbody>'
    result.push(`<div class="md-table"><table>${h}${b}</table></div>`)
    tableHeader = []; tableRows = []; inTable = false
  }

  for (let i = 0; i < lines.length; i++) {
    const trimmed = lines[i].trim()

    // Table row
    if (trimmed.startsWith('|') && trimmed.endsWith('|')) {
      flushPara()
      const cells = trimmed.split('|').filter(c => c.trim())
      if (!inTable) { inTable = true; tableHeader = cells; continue }
      if (tableHeader.length > 0 && cells.length > 0) { tableRows.push(cells) }
      continue
    }
    if (inTable && /^[\|\s\-:]+$/.test(trimmed)) continue
    if (inTable) flushTable()

    // Empty line = paragraph break
    if (trimmed === '') {
      flushPara()
      continue
    }

    // Accumulate paragraph: skip lines that look like page numbers or junk
    if (/^\s*\d{1,3}\s*$/.test(trimmed)) continue  // page numbers
    if (/^-{5,}$/.test(trimmed)) { flushPara(); continue }  // separator line = new para
    paraBuf.push(trimmed)
  }
  flushPara()
  flushTable()

  const final = `<div class="md-content">${result.join('')}</div>`
  return final
}

function isEmbeddable(url: string) {
  if (!url) return false
  try {
    const parsed = new URL(url)
    return ['https:', 'http:'].includes(parsed.protocol) &&
      (url.includes('nmpa.gov.cn') || url.includes('samr.gov.cn'))
  } catch { return false }
}

function copyLink() {
  navigator.clipboard.writeText(window.location.href)
  ElMessage.success('链接已复制')
}

async function doDownload() {
  if (!doc.value) return
  try {
    // Fetch a short-lived, scoped download token (avoids exposing full JWT in URL)
    const resp: any = await get(`/api/documents/${doc.value.id}/download-token`)
    window.location.href = `/api/documents/${doc.value.id}/download?token=${encodeURIComponent(resp.token)}`
  } catch {
    // Fallback for guest users: try without token
    window.location.href = `/api/documents/${doc.value.id}/download`
  }
}

async function toggleFavorite() {
  if (!auth.isLoggedIn) {
    ElMessage.warning('请先登录')
    return
  }
  try {
    if (isFavorited.value) {
      await del(`/api/me/favorites/${doc.value.id}`)
    } else {
      await post(`/api/me/favorites/${doc.value.id}`)
    }
    isFavorited.value = !isFavorited.value
    ElMessage.success(isFavorited.value ? '已收藏' : '已取消收藏')
  } catch { ElMessage.error('操作失败') }
}

function goBack() {
  if (doc.value?.category_id) {
    router.push('/category/' + doc.value.category_id)
  } else if (window.history.length > 1) {
    router.back()
  } else {
    router.push('/')
  }
}

async function loadDoc() {
  loading.value = true
  errorMsg.value = ''
  previewUrl.value = ''
  markdownSource.value = ''
  destroyOnlyOffice()
  try {
    const data: any = await get(`/api/documents/${route.params.id}`)
    doc.value = data
    isFavorited.value = data.is_favorited || false
    // Fetch a short-lived scoped preview token (not the full JWT)
    if (data.file_type !== 'link') {
      await fetchPreviewToken(data.id)
    }
    // Load related docs from same category
    if (data.category_id) {
      const resp: any = await get('/api/documents', {
        category_id: data.category_id, size: 5, sort: 'updated_at', order: 'desc',
      })
      relatedDocs.value = (resp.items || []).filter((d: any) => d.id !== data.id).slice(0, 5)
    }
  } catch (e: any) {
    if (e?.response?.status === 403) {
      errorMsg.value = '无权访问该文档'
      errorSub.value = '该文档可能需要登录或属于其他部门'
    } else if (e?.response?.status === 404) {
      errorMsg.value = '文档不存在'
      errorSub.value = '该文档可能已被删除'
    } else {
      errorMsg.value = '加载失败'
      errorSub.value = '请检查网络连接后重试'
    }
  }
  loading.value = false
}

watch(() => route.params.id, loadDoc, { immediate: true })
onBeforeUnmount(() => {
  destroyOnlyOffice()
  if (_ooReadyTimer) { clearTimeout(_ooReadyTimer) }
  if (_fsReadyTimer) { clearTimeout(_fsReadyTimer) }
  if (fsDocEditor) { try { fsDocEditor.destroy() } catch { /* noop */ } }
})
</script>

<style scoped>
.document-page { padding: var(--spacing-md) 0; }
.doc-nav-bar { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; padding: 8px 0; border-bottom: 1px solid var(--color-border); }
.back-btn { flex-shrink: 0; padding: 6px 16px; font-size: 13px; }
.doc-layout { display: flex; gap: var(--spacing-lg); margin-top: var(--spacing-md); }
.doc-main { flex: 1; background: #fff; border-radius: var(--radius-md); box-shadow: var(--shadow-card); overflow: hidden; min-width: 0; }
.doc-sidebar { width: 260px; flex-shrink: 0; }
.doc-sidebar h3 { font-size: 15px; margin-bottom: var(--spacing-md); color: var(--color-text-primary); }
.related-item { background: #fff; border-radius: var(--radius-md); padding: var(--spacing-md); margin-bottom: var(--spacing-sm); cursor: pointer; box-shadow: var(--shadow-card); }
.related-item:hover { box-shadow: var(--shadow-hover); }
.related-item h4 { font-size: 13px; margin-bottom: 4px; }
.related-item p { font-size: 12px; color: var(--color-text-secondary); }

.doc-preview-area { min-height: 300px; }
.link-card { text-align: center; padding: var(--spacing-2xl); }
.link-card h2 { margin: var(--spacing-md) 0; font-size: 20px; }
.link-card p { color: var(--color-text-secondary); max-width: 600px; margin: 0 auto var(--spacing-lg); }
/* Content search */
.content-search {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  background: #fff;
  border: 1.5px solid #e0e4e8;
  border-radius: 8px;
  margin-bottom: 12px;
  transition: border-color .2s;
}
.content-search:focus-within {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(30,80,174,.06);
}
.content-search-input {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  font-size: 14px;
  color: var(--color-text-primary);
  font-family: inherit;
}
.content-search-input::placeholder { color: #bbb; }
.content-match-count {
  font-size: 12px;
  color: var(--color-primary);
  font-weight: 600;
  white-space: nowrap;
  background: rgba(30,80,174,.06);
  padding: 3px 10px;
  border-radius: 12px;
}

/* Article view (link-type docs with content) */
.article-view {
  text-align: left;
  padding: 0;
}
.article-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0 0 4px;
  line-height: 1.4;
}
.article-summary {
  font-size: 13px;
  color: var(--color-text-secondary);
  margin: 0 0 16px;
  line-height: 1.6;
}
.article-body {
  margin-bottom: 16px;
}
.article-actions {
  display: flex;
  gap: 8px;
  padding: 12px 0;
  border-top: 1px solid #e5e7eb;
  margin: 16px 0;
}
.article-embed {
  margin-top: 8px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  overflow: hidden;
}
.article-embed iframe {
  width: 100%;
  height: 500px;
  border: none;
}

/* Attachment cards */
.article-attachments {
  margin: 16px 0;
  padding: 14px;
  background: #f8fafc;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}
.article-attachments h3 {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-secondary);
  margin: 0 0 10px;
}
.att-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.att-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  cursor: pointer;
  transition: all .15s;
  max-width: 100%;
}
.att-card:hover {
  border-color: var(--color-primary);
  box-shadow: 0 1px 4px rgba(30,80,174,.1);
}
.att-card-icon {
  width: 28px;
  height: 28px;
  border-radius: 5px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 9px;
  font-weight: 700;
  color: #fff;
  flex-shrink: 0;
}
.att-card-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.att-card-name {
  font-size: 13px;
  color: var(--color-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.att-card-meta {
  font-size: 11px;
  color: #999;
}

/* Markdown content */
.article-body :deep(.md-content) { }
.article-body :deep(.md-h2) { font-size: 17px; font-weight: 700; margin: 16px 0 8px; color: var(--color-text-primary); }
.article-body :deep(.md-h2) { font-size: 17px; font-weight: 700; margin: 24px 0 12px; padding-bottom: 6px; border-bottom: 1px solid #e8ecf0; color: #1e50ae; }
.article-body :deep(.md-h3) { font-size: 14px; font-weight: 600; margin: 16px 0 8px; color: #2c3e50; }
.article-body :deep(.md-p) { margin: 0 0 10px; line-height: 1.85; color: #333; text-indent: 0; }
.article-body :deep(.md-list) { margin: 4px 0; padding-left: 20px; color: var(--color-text-primary); }
.article-body :deep(.md-list li) { margin: 2px 0; }
.md-table {
  overflow: auto;
  margin: 0;
  border: 1px solid #e0e4e8;
  border-radius: 8px;
  max-height: 62vh;
  box-shadow: 0 1px 2px rgba(0,0,0,.04);
}
.md-table table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  font-variant-numeric: tabular-nums;
}
.md-table th {
  background: #1e50ae;
  color: #fff;
  padding: 10px 12px;
  text-align: left;
  font-weight: 600;
  font-size: 12px;
  letter-spacing: .02em;
  white-space: nowrap;
  position: sticky;
  top: 0;
  z-index: 2;
}
.md-table th:first-child { width: 60px; text-align: center; }
.md-table th:nth-child(2) { min-width: 200px; }
.md-table th:nth-child(3) { min-width: 200px; }
.md-table th:last-child { min-width: 180px; }
.md-table td {
  padding: 7px 12px;
  border-bottom: 1px solid #eef0f2;
  color: var(--color-text-primary);
}
.md-table td:first-child {
  text-align: center;
  color: var(--color-text-secondary);
  font-size: 12px;
}
.md-table td:nth-child(2) {
  font-weight: 500;
}
.md-table td:nth-child(3) {
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 12px;
  color: #1e50ae;
}
.md-table td:last-child {
  font-size: 12px;
  color: var(--color-text-secondary);
}
.md-table tr:last-child td { border-bottom: none; }
.md-table tr:nth-child(even) td { background: #f8fafc; }
.md-table tr:hover td { background: #e8f0fe; }
.link-embed iframe { width: 100%; height: 500px; border: 1px solid var(--color-border); border-radius: var(--radius-md); }

.image-preview { text-align: center; padding: var(--spacing-lg); background: #f0f0f0; }
.video-preview { padding: 0; background: #000; border-radius: var(--radius-md); overflow: hidden; }
.video-ctrl-bar { display: flex; align-items: center; gap: 6px; padding: 8px 12px; background: #1a1a2e; }
.video-ctrl-label { color: rgba(255,255,255,.5); font-size: 12px; margin-right: 4px; }
.speed-btn { padding: 3px 8px; border: 1px solid rgba(255,255,255,.15); border-radius: 3px; background: transparent; color: rgba(255,255,255,.5); cursor: pointer; font-size: 11px; font-family: inherit; transition: all .15s; }
.speed-btn:hover { border-color: var(--color-accent); color: var(--color-accent); }
.speed-btn.active { background: var(--color-accent); color: #1a1a2e; border-color: var(--color-accent); font-weight: 600; }
.audio-preview { background: var(--color-bg-secondary); padding: var(--spacing-xl); }

.preview-placeholder { padding: var(--spacing-xl); }
.preview-loading { text-align: center; padding: var(--spacing-2xl); color: var(--color-text-secondary); }
.oo-switch-bar { margin: 0 0 10px; text-align: right; }
.preview-loading p { margin-top: var(--spacing-md); font-size: 14px; }
.preview-loading .hint { font-size: 12px; color: var(--color-text-secondary); }

.inline-preview { position: relative; min-height: 400px; }
.inline-preview iframe { height: 700px; }
.onlyoffice-editor { width: 100%; height: 700px; }
.onlyoffice-preview { position: relative; min-height: 600px; background: #fff; }
.onlyoffice-editor iframe { width: 100%; height: 700px; border: 0; display: block; }
.onlyoffice-loading {
  position: absolute; inset: 0; z-index: 2;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  background: rgba(255,255,255,.9); color: var(--color-text-secondary);
}
.onlyoffice-loading p { margin-top: var(--spacing-sm); font-size: 14px; }
.preview-loading-overlay {
  position: absolute; inset: 0; z-index: 2;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  background: rgba(255,255,255,.85); border-radius: 8px;
  color: var(--color-text-secondary);
}
.preview-loading-overlay p { margin-top: var(--spacing-md); font-size: 14px; }
.preview-loading-overlay .hint { font-size: 12px; }
.preview-error { padding: var(--spacing-lg); }
.preview-unsupported { padding: var(--spacing-lg); }
.preview-page { max-width: 800px; margin: 0 auto; min-height: 300px; border: 1px solid var(--color-border); border-radius: var(--radius-md); padding: var(--spacing-xl); }
.file-type-badge { margin-bottom: var(--spacing-md); }
.file-type-badge .el-tag { font-size: 18px; padding: 8px 16px; }
.preview-content h2 { font-size: 20px; margin-bottom: var(--spacing-lg); }
.preview-summary { line-height: 1.8; color: var(--color-text-primary); margin-bottom: var(--spacing-lg); white-space: pre-wrap; }
.preview-meta-grid { display: grid; grid-template-columns: 1fr 1fr; gap: var(--spacing-sm); margin-bottom: var(--spacing-lg); }
.meta-item { display: flex; flex-direction: column; padding: var(--spacing-sm); background: var(--color-bg-secondary); border-radius: var(--radius-sm); }
.meta-label { font-size: 12px; color: var(--color-text-secondary); }
.meta-value { font-size: 14px; color: var(--color-text-primary); margin-top: 2px; }
.preview-tags { display: flex; gap: 4px; flex-wrap: wrap; }

.doc-toolbar {
  display: flex;
  gap: var(--spacing-sm);
  padding: var(--spacing-md) var(--spacing-lg);
  border-top: 1px solid var(--color-border);
  background: #fafbfc;
}
.doc-toolbar .el-button--default {
  border-color: #d0d5dd;
  font-weight: 500;
}
.doc-toolbar .el-button--default:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
  background: #f8faff;
}
.doc-meta { padding: var(--spacing-lg); }

/* ── Fullscreen preview ── */
.preview-fullscreen-btn {
  position: absolute; top: 10px; right: 10px; z-index: 3;
  width: 34px; height: 34px; border: none; border-radius: 6px;
  background: rgba(0,0,0,.5); color: #fff; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: all .15s; opacity: 0;
}
.inline-preview:hover .preview-fullscreen-btn { opacity: 1; }
.onlyoffice-preview:hover .preview-fullscreen-btn { opacity: 1; }
.onlyoffice-preview .preview-fullscreen-btn { opacity: 1; }
.preview-fullscreen-btn:hover { background: rgba(0,0,0,.75); }

.fullscreen-overlay {
  position: fixed; inset: 0; z-index: 9999; background: rgba(0,0,0,.92);
  display: flex; align-items: center; justify-content: center;
}
.fs-close-btn {
  position: absolute; top: 16px; right: 16px; z-index: 1;
  width: 44px; height: 44px; border: none; border-radius: 8px;
  background: rgba(255,255,255,.15); color: #fff; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
}
.fs-close-btn:hover { background: rgba(255,255,255,.3); }
.fs-iframe { width: 100%; height: 100%; border: none; }

.fs-preview-enter-active { transition: all .2s ease-out; }
.fs-preview-leave-active { transition: all .15s ease-in; }
.fs-preview-enter-from, .fs-preview-leave-to { opacity: 0; }
.fs-loading {
  position: absolute; inset: 0; z-index: 2;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  background: rgba(0,0,0,.45); color: #fff;
}
.fs-loading p { margin-top: var(--spacing-sm); font-size: 14px; }

@media (max-width: 900px) {
  .doc-layout { flex-direction: column; }
  .doc-sidebar { width: 100%; }
}

@media (max-width: 900px) {
  .inline-preview iframe, .onlyoffice-editor, .onlyoffice-editor iframe { height: 62vh; }
  .doc-layout { flex-direction: column; }
  .doc-sidebar { width: 100%; }
  .doc-nav-bar { flex-wrap: wrap; }
}
</style>

<!-- OnlyOffice 动态创建的 iframe 不带 scoped 属性，尺寸规则必须放在全局样式 -->
<style>
.onlyoffice-preview > iframe {
  width: 100%;
  height: 700px;
  border: 0;
  display: block;
}
@media (max-width: 900px) {
  .onlyoffice-preview > iframe { height: 62vh; }
}
.oo-fs-editor {
  width: calc(100vw - 48px);
  height: calc(100vh - 48px);
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
}
.oo-fs-editor > iframe {
  width: 100%;
  height: 100%;
  border: 0;
}
.fullscreen-overlay > iframe {
  width: calc(100vw - 48px);
  height: calc(100vh - 48px);
  border: 0;
  border-radius: 8px;
}
</style>

<style>
.md-table { overflow: auto; margin: 8px 0; border: 1px solid #e0e4e8; border-radius: 8px; max-height: 62vh; box-shadow: 0 1px 2px rgba(0,0,0,.04); }
.md-table table { width: 100%; border-collapse: collapse; font-size: 13px; }
.md-table th { background: #1e50ae; color: #fff; padding: 10px 12px; text-align: left; font-weight: 600; font-size: 12px; white-space: nowrap; position: sticky; top: 0; z-index: 2; }
.md-table td { padding: 7px 12px; border-bottom: 1px solid #eef0f2; color: #333; }
.md-table tr:nth-child(even) td { background: #f8fafc; }
.md-table tr:hover td { background: #e8f0fe; }
.article-preview-hero { text-align: center; padding: 40px 20px; background: #f8fafc; border: 2px dashed #c0c8d0; border-radius: 12px; margin: 12px 0; }
.preview-hero-icon { color: #1e50ae; margin-bottom: 12px; }
.preview-hero-meta { font-size: 13px; color: #888; margin: 4px 0 16px; }
.reading-frame { background: #fff; border: 1px solid #e0e4e8; border-radius: 10px; padding: 28px 24px; margin: 12px 0; box-shadow: 0 1px 3px rgba(0,0,0,.04); }
.reading-frame--empty { text-align: center; color: #999; padding: 40px; }

.fs-overlay { position: fixed; inset: 0; z-index: 9999; background: rgba(0,0,0,.6); display: flex; flex-direction: column; }
.fs-toolbar { display: flex; align-items: center; gap: 12px; padding: 12px 16px; background: #fff; border-bottom: 1px solid #e5e7eb; }
.fs-title { flex: 1; font-size: 15px; font-weight: 600; color: #333; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.fs-search { display: flex; align-items: center; gap: 6px; padding: 6px 10px; background: #f0f4f8; border-radius: 6px; }
.fs-search input { border: none; outline: none; background: transparent; font-size: 13px; width: 180px; }
.fs-close { background: none; border: none; cursor: pointer; padding: 6px; color: #666; border-radius: 6px; }
.fs-close:hover { background: #f0f0f0; }
.fs-body { flex: 1; overflow: auto; padding: 16px; background: #f8fafc; }
.fs-body .md-table { max-height: none; }

.article-body-wrapper { position: relative; }
.fs-trigger {
  position: absolute; top: 6px; right: 6px; z-index: 5;
  background: rgba(255,255,255,.9); border: 1px solid #ddd; border-radius: 6px;
  cursor: pointer; padding: 6px; color: #666; display: flex;
  box-shadow: 0 1px 3px rgba(0,0,0,.08);
}
.fs-trigger:hover { color: var(--color-primary); border-color: var(--color-primary); }
</style>
