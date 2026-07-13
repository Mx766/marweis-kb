<template>
  <div class="document-page" v-loading="loading">
    <el-breadcrumb separator=">">
      <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
      <el-breadcrumb-item :to="{ path: '/category' }">知识库</el-breadcrumb-item>
      <el-breadcrumb-item>{{ doc?.title }}</el-breadcrumb-item>
    </el-breadcrumb>

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
          <!-- External link -->
          <template v-if="doc.file_type === 'link'">
            <div class="link-card">
              <el-icon :size="48" color="#00bcd4"><Link /></el-icon>
              <h2>{{ doc.title }}</h2>
              <p v-if="doc.summary">{{ doc.summary }}</p>
              <div class="link-actions">
                <a :href="doc.source_url" target="_blank" rel="noopener">
                  <el-button type="primary" size="large">访问原文</el-button>
                </a>
                <el-button size="large" @click="copyLink">复制链接</el-button>
              </div>
              <div class="link-embed" v-if="isEmbeddable(doc.source_url)">
                <iframe :src="doc.source_url" frameborder="0" sandbox="allow-same-origin allow-scripts"></iframe>
              </div>
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
              <video controls style="max-width:100%">
                <source :src="previewUrl" :type="doc.mime_type" />
                您的浏览器不支持此视频格式
              </video>
            </div>
          </template>

          <!-- Audio preview -->
          <template v-else-if="isAudio">
            <div class="audio-preview">
              <audio controls style="width:100%">
                <source :src="previewUrl" :type="doc.mime_type" />
              </audio>
            </div>
          </template>

          <!-- Document placeholder with rich info — now with inline preview -->
          <template v-else>
            <div class="preview-placeholder">
              <!-- PDF Preview iframe -->
              <div v-if="previewUrl" class="inline-preview">
                <iframe
                  :src="previewUrl"
                  width="100%"
                  height="700px"
                  style="border:none;border-radius:8px"
                  title="文档预览"
                  sandbox="allow-scripts allow-same-origin"
                  referrerpolicy="no-referrer"
                ></iframe>
              </div>
              <div class="preview-page" :class="{ 'has-preview': previewUrl }">
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
                    <span class="meta-label">生效日期</span>
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
            </div>
          </template>
        </div>

        <!-- Toolbar -->
        <div class="doc-toolbar">
          <el-button
            v-if="doc.file_type !== 'link'"
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
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Link, Download as DownloadIcon, Link as LinkIcon, Star as StarIcon } from '@element-plus/icons-vue'
import { get, post, del } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import dayjs from 'dayjs'
import { ElMessage } from 'element-plus'

const route = useRoute()
const auth = useAuthStore()
const doc = ref<any>(null)
const loading = ref(true)
const isFavorited = ref(false)
const errorMsg = ref('')
const errorSub = ref('')
const relatedDocs = ref<any[]>([])

const IMG_EXTS = ['jpg','jpeg','png','gif','tiff','tif','bmp','svg','webp']
const VID_EXTS = ['mp4','avi','mov','wmv','webm']
const AUD_EXTS = ['mp3','wav','wma','flac','ogg']

const isImage = computed(() => IMG_EXTS.includes(doc.value?.file_ext?.toLowerCase() || ''))
const isVideo = computed(() => VID_EXTS.includes(doc.value?.file_ext?.toLowerCase() || ''))
const isAudio = computed(() => AUD_EXTS.includes(doc.value?.file_ext?.toLowerCase() || ''))
const previewUrl = computed(() => {
  if (!doc.value) return ''
  // Use the preview endpoint which handles Gotenberg conversion
  return `/api/documents/${doc.value.id}/preview`
})

const fileColors: Record<string,string> = {
  pdf:'#e74c3c',doc:'#2980b9',docx:'#2980b9',xls:'#27ae60',xlsx:'#27ae60',ppt:'#e67e22',pptx:'#e67e22',
  zip:'#7f8c8d',rar:'#7f8c8d',sevenz:'#7f8c8d',
}
function fileIconColor(ext: string) { return fileColors[ext?.toLowerCase()] || '#1e50ae' }

function formatDate(d: string) { return dayjs(d).format('YYYY-MM-DD HH:mm') }
function formatSize(bytes: number) { return bytes > 1048576 ? `${(bytes/1048576).toFixed(1)} MB` : `${(bytes/1024).toFixed(1)} KB` }

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

function doDownload() {
  if (!doc.value) return
  // Use direct navigation — the backend returns a 307 redirect to the presigned URL
  window.location.href = `/api/documents/${doc.value.id}/download`
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

async function loadDoc() {
  loading.value = true
  errorMsg.value = ''
  try {
    const data: any = await get(`/api/documents/${route.params.id}`)
    doc.value = data
    isFavorited.value = data.is_favorited || false
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
onMounted(loadDoc)
</script>

<style scoped>
.document-page { padding: var(--spacing-md) 0; }
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
.link-actions { display: flex; gap: var(--spacing-sm); justify-content: center; margin-bottom: var(--spacing-lg); }
.link-embed iframe { width: 100%; height: 500px; border: 1px solid var(--color-border); border-radius: var(--radius-md); }

.image-preview { text-align: center; padding: var(--spacing-lg); background: #f0f0f0; }
.video-preview, .audio-preview { padding: var(--spacing-lg); background: #000; text-align: center; border-radius: var(--radius-md); }
.audio-preview { background: var(--color-bg-secondary); padding: var(--spacing-xl); }

.preview-placeholder { padding: var(--spacing-xl); }
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

.doc-toolbar { display: flex; gap: var(--spacing-sm); padding: var(--spacing-md) var(--spacing-lg); border-top: 1px solid var(--color-border); background: var(--color-bg-secondary); }
.doc-meta { padding: var(--spacing-lg); }

@media (max-width: 900px) {
  .doc-layout { flex-direction: column; }
  .doc-sidebar { width: 100%; }
}
</style>
