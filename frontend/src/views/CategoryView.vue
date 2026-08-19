<template>
  <div class="category-page">
    <!-- Category header -->
    <div class="cat-header" v-if="currentCat">
      <div class="cat-header-top">
        <el-breadcrumb separator="›">
          <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
          <el-breadcrumb-item>{{ currentCat.name }}</el-breadcrumb-item>
        </el-breadcrumb>
        <el-button v-if="canUpload" type="primary" size="small" class="upload-btn" @click="uploadVisible = true">
          <el-icon style="margin-right:4px"><Upload /></el-icon>上传文档
        </el-button>
      </div>
      <h1 class="cat-title">{{ currentCat.name }}</h1>
      <div class="cat-meta" v-if="currentCat.description || total > 0">
        <span v-if="currentCat.description" class="cat-desc">{{ currentCat.description }}</span>
        <span class="cat-count">
          <span class="count-num">{{ total }}</span> 篇文档
        </span>
      </div>
    </div>

    <!-- Default category view (no specific category selected) -->
    <div class="cat-header" v-else>
      <h1 class="cat-title">知识库</h1>
      <div class="cat-meta">
        <span class="cat-desc">浏览全部可访问的文档</span>
        <span class="cat-count"><span class="count-num">{{ total }}</span> 篇文档</span>
      </div>
    </div>

    <!-- Sub-category pills -->
    <div v-if="subCategories.length" class="sub-cat-pills">
      <button
        class="pill"
        :class="{ active: !activeSubId }"
        @click="setSub('')"
      >全部</button>
      <button
        v-for="sub in subCategories"
        :key="sub.id"
        class="pill"
        :class="{ active: activeSubId === sub.id }"
        @click="setSub(sub.id)"
      >{{ sub.name }}</button>
    </div>

    <!-- Toolbar: search + filter -->
    <div class="toolbar">
      <div class="toolbar-search">
        <el-icon class="search-icon"><Search /></el-icon>
        <input
          v-model="searchKeyword"
          type="text"
          placeholder="在当前分类下搜索文档..."
          @input="onSearchInput"
          @keydown.enter="doLoad"
          class="search-input"
        />
        <button v-if="searchKeyword" class="search-clear" @click="searchKeyword=''; doLoad()">
          <el-icon><Close /></el-icon>
        </button>
      </div>
      <div class="toolbar-right">
        <el-select v-model="fileTypeFilter" placeholder="全部格式" clearable @change="doLoad" size="default" class="filter-select" popper-class="filter-popper">
          <el-option label="全部格式" value="" />
          <el-option label="PDF" value="pdf" />
          <el-option label="Word" value="doc" />
          <el-option label="Excel" value="xls" />
          <el-option label="外链" value="link" />
        </el-select>
      </div>
    </div>

    <!-- Document cards -->
    <div class="doc-list" v-loading="loading" element-loading-text="加载中...">
      <article
        v-for="doc in docs"
        :key="doc.id"
        class="doc-card"
        @click="openDoc(doc)"
      >
        <!-- File icon area -->
        <div class="doc-icon-area" :style="{ background: iconBg(doc.file_ext) }">
          <span class="doc-ext-label">{{ doc.file_ext?.toUpperCase()?.substring(0, 4) || 'LINK' }}</span>
        </div>

        <!-- Content -->
        <div class="doc-content">
          <h3 class="doc-title">{{ doc.title }}</h3>
          <div class="doc-meta-row">
            <span class="doc-author">{{ doc.uploader_name }}</span>
            <span class="doc-dot">·</span>
            <span class="doc-date">{{ formatDate(doc.updated_at) }}</span>
            <span v-if="doc.version" class="doc-version">v{{ doc.version }}</span>
          </div>
          <p v-if="searchKeyword && doc.snippet" class="doc-snippet">{{ doc.snippet }}</p>
          <p v-else-if="doc.summary" class="doc-summary">{{ doc.summary }}</p>
        </div>

        <!-- Tags & actions -->
        <div class="doc-right">
          <div class="doc-tags" v-if="doc.tags?.length">
            <span v-for="t in doc.tags.slice(0, 3)" :key="t" class="doc-tag">{{ t }}</span>
          </div>
          <div class="doc-actions">
            <span class="doc-views" title="浏览次数">
              <el-icon :size="14"><View /></el-icon> {{ doc.view_count }}
            </span>
          </div>
        </div>
      </article>

      <!-- Empty state -->
      <div v-if="docs.length === 0" class="empty-state">
        <div class="empty-icon">
          <el-icon :size="48"><DocumentCopy /></el-icon>
        </div>
        <h3>{{ searchKeyword ? '未找到匹配的文档' : '暂无文档' }}</h3>
        <p>{{ searchKeyword ? '请尝试其他关键词或清空搜索' : (canUpload ? '此分类下还没有文档，点击右上角「上传文档」添加' : '此分类下还没有文档，等待管理员上传') }}</p>
        <el-button v-if="searchKeyword" size="small" @click="searchKeyword=''; doLoad()">清空搜索</el-button>
        <el-button v-else size="small" type="primary" @click="$router.push('/')">返回首页</el-button>
      </div>

      <!-- Pagination -->
      <div class="pagination-wrap" v-if="total > size">
        <el-pagination
          v-model:current-page="page"
          :page-size="size"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          :page-sizes="[10,20,50]"
          background
          @current-change="doLoad"
          @size-change="(s: number) => { size = s; doLoad(); }"
        />
      </div>
    </div>

    <!-- Upload dialog (only for allow_upload categories) -->
    <el-dialog v-model="uploadVisible" title="上传文档" width="520px" :close-on-click-modal="false">
      <el-form label-width="88px">
        <el-form-item label="选择文件">
          <el-upload
            :auto-upload="false"
            :show-file-list="true"
            :limit="1"
            :on-change="onFileChange"
            :on-remove="onFileRemove"
          >
            <el-button size="small" type="primary" plain>
              <el-icon style="margin-right:4px"><Upload /></el-icon>选择文件
            </el-button>
            <template #tip>
              <div class="el-upload__tip">支持 Word / Excel / PDF / 图片 / 压缩包等，也可只填写来源链接</div>
            </template>
          </el-upload>
        </el-form-item>
        <el-form-item label="标题" required>
          <el-input v-model="uploadForm.title" maxlength="200" placeholder="文档标题" />
        </el-form-item>
        <el-form-item label="来源链接">
          <el-input v-model="uploadForm.source_url" placeholder="可选：外部来源链接（如官网文章地址）" />
        </el-form-item>
        <el-form-item label="摘要">
          <el-input v-model="uploadForm.summary" type="textarea" :rows="3" placeholder="可选：一句话说明内容" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="resetUpload()">取消</el-button>
        <el-button type="primary" :loading="uploading" @click="submitUpload()">上传</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Search, Close, View, DocumentCopy, Upload } from '@element-plus/icons-vue'
import { get, upload } from '@/api/client'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import dayjs from 'dayjs'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

interface Cat { id: string; name: string; children?: Cat[]; description?: string; allow_upload?: boolean; permission_mode?: string | null }
const currentCat = ref<Cat | null>(null)
const activeSubId = ref('')
const docs = ref<any[]>([])
const loading = ref(false)
const page = ref(1)
const total = ref(0)
const size = ref(20)
const searchKeyword = ref('')
const fileTypeFilter = ref('')
const uploadVisible = ref(false)
const uploading = ref(false)
const pickedFile = ref<File | null>(null)
const uploadForm = ref({ title: '', summary: '', source_url: '' })
let _searchTimer: ReturnType<typeof setTimeout> | null = null

const subCategories = computed(() => currentCat.value?.children || [])
const isAdmin = computed(() => ['super_admin', 'dept_admin'].includes(auth.user?.role || ''))
const canUpload = computed(() => {
  const cat = currentCat.value
  if (!cat) return false
  if (isAdmin.value) return !!(cat.allow_upload || cat.permission_mode)
  return !!(cat.allow_upload || cat.permission_mode === 'member_upload')
})

function formatDate(d: string) { return dayjs(d).format('YYYY-MM-DD') }

const iconBgMap: Record<string, string> = {
  pdf: '#ef4444', doc: '#3b82f6', docx: '#3b82f6',
  xls: '#16a34a', xlsx: '#16a34a', ppt: '#f97316', pptx: '#f97316',
  link: '#0891b2', txt: '#6b7280', md: '#6b7280',
  jpg: '#a855f7', jpeg: '#a855f7', png: '#a855f7',
  zip: '#78716c', rar: '#78716c',
  mp4: '#8b5cf6', avi: '#8b5cf6',
}
function iconBg(ext: string) {
  const e = ext?.toLowerCase() || ''
  return iconBgMap[e] || '#f0f4f8'
}

// Recursive find in tree
function findByCat(tree: Cat[], id: string): Cat | null {
  for (const c of tree) {
    if (c.id === id) return c
    if (c.children?.length) {
      const found = findByCat(c.children, id)
      if (found) return found
    }
  }
  return null
}

function openDoc(doc: any) {
  // Bare link (no content) → open source URL directly
  if (doc.file_type === 'link' && doc.source_url && (!doc.content_text || doc.content_text.length < 100)) {
    window.open(doc.source_url, '_blank')
    return
  }
  router.push(`/document/${doc.id}`)
}

function setSub(subId: string) {
  activeSubId.value = subId
  page.value = 1
  doLoad()
}

function onFileChange(file: any) {
  pickedFile.value = file.raw || null
  if (pickedFile.value && !uploadForm.value.title) {
    uploadForm.value.title = pickedFile.value.name.replace(/\.[^.]+$/, '')
  }
}

function onFileRemove() {
  pickedFile.value = null
}

function resetUpload() {
  uploadVisible.value = false
  uploading.value = false
  pickedFile.value = null
  uploadForm.value = { title: '', summary: '', source_url: '' }
}

async function submitUpload() {
  const catId = activeSubId.value || (currentCat.value?.id || '')
  const fd = new FormData()
  fd.append('title', uploadForm.value.title.trim())
  fd.append('category_id', catId)
  if (uploadForm.value.summary.trim()) fd.append('summary', uploadForm.value.summary.trim())
  if (uploadForm.value.source_url.trim()) fd.append('source_url', uploadForm.value.source_url.trim())
  if (pickedFile.value) fd.append('file', pickedFile.value)
  if (!fd.get('title')) {
    ElMessage.warning('请填写标题')
    return
  }
  if (!fd.get('file') && !uploadForm.value.source_url.trim()) {
    ElMessage.warning('请选择文件或填写来源链接')
    return
  }
  uploading.value = true
  try {
    await upload('/api/documents', fd)
    ElMessage.success('上传成功')
    resetUpload()
    doLoad()
  } catch (e: any) {
    uploading.value = false
    ElMessage.error(e?.response?.data?.detail || '上传失败，请重试')
  }
}

function onSearchInput() {
  if (_searchTimer) clearTimeout(_searchTimer)
  _searchTimer = setTimeout(() => { page.value = 1; doLoad() }, 300)
}

async function doLoad() {
  loading.value = true
  try {
    const catId = activeSubId.value || (currentCat.value?.id || '')
    let resp: any

    if (searchKeyword.value.trim()) {
      const params: any = { q: searchKeyword.value.trim(), page: page.value, size: size.value }
      if (catId) params.category_id = catId
      if (fileTypeFilter.value) params.file_type = fileTypeFilter.value
      resp = await get('/api/search', params)
    } else {
      const params: any = { page: page.value, size: size.value, sort: 'updated_at', order: 'desc' }
      if (catId) params.category_id = catId
      if (fileTypeFilter.value) params.file_type = fileTypeFilter.value
      resp = await get('/api/documents', params)
    }

    docs.value = resp.items || []
    total.value = resp.total || 0
  } catch { docs.value = []; total.value = 0 }
  loading.value = false
}

async function loadCategory(id: string) {
  const tree: Cat[] = await get('/api/categories')
  const cat = findByCat(tree, id)
  if (cat?.name?.includes('通讯录')) {
    router.replace({ name: 'Contact', params: { id } })
    return
  }
  if (cat?.name?.includes('原料搜索引擎')) {
    router.replace({ name: 'IngredientSearch' })
    return
  }
  if (cat?.name?.includes('知识图谱')) {
    router.replace({ name: 'KnowledgeGraph' })
    return
  }
  currentCat.value = cat
  activeSubId.value = ''
  page.value = 1
  doLoad()
}

watch(() => route.params.id, (id) => {
  if (id && typeof id === 'string') {
    loadCategory(id)
  } else {
    currentCat.value = null
    activeSubId.value = ''
    doLoad()
  }
}, { immediate: true })

onBeforeUnmount(() => {
  if (_searchTimer) clearTimeout(_searchTimer)
})
</script>

<style scoped>
.category-page {
  max-width: 960px;
  margin: 0 auto;
  padding: var(--spacing-lg) 0;
}

/* ── Category header ── */
.cat-header {
  margin-bottom: var(--spacing-lg);
}
.cat-header-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 6px;
}
.upload-btn {
  flex-shrink: 0;
}
.cat-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0 0 6px;
  line-height: 1.3;
}
.cat-meta {
  display: flex;
  align-items: center;
  gap: 16px;
  font-size: 13px;
  color: var(--color-text-secondary);
}
.cat-desc {
  flex: 1;
}
.cat-count {
  flex-shrink: 0;
  font-weight: 500;
}
.count-num {
  font-size: 16px;
  font-weight: 700;
  color: var(--color-primary);
}

/* ── Sub-category pills ── */
.sub-cat-pills {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: var(--spacing-md);
}
.pill {
  padding: 6px 16px;
  border: 1px solid var(--color-border);
  border-radius: 20px;
  background: #fff;
  font-size: 13px;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all .15s ease;
  font-family: inherit;
  outline: none;
}
.pill:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
  background: rgba(30, 80, 174, .03);
}
.pill.active {
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: #fff;
  font-weight: 600;
}

/* ── Toolbar ── */
.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: var(--spacing-md);
}
.toolbar-search {
  flex: 1;
  position: relative;
  display: flex;
  align-items: center;
  background: #fff;
  border: 1px solid var(--color-border);
  border-radius: 10px;
  padding: 0 12px;
  transition: all .2s ease;
}
.toolbar-search:focus-within {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(30, 80, 174, .08);
}
.search-icon {
  font-size: 16px;
  color: var(--color-text-secondary);
  flex-shrink: 0;
}
.search-input {
  flex: 1;
  border: none;
  outline: none;
  padding: 10px 8px;
  font-size: 13px;
  color: var(--color-text-primary);
  background: transparent;
  font-family: inherit;
}
.search-input::placeholder {
  color: #c0c4cc;
}
.search-clear {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--color-text-secondary);
  padding: 2px;
  display: flex;
  align-items: center;
  font-size: 14px;
}
.search-clear:hover { color: var(--color-text-primary); }

.toolbar-right {
  flex-shrink: 0;
}
.filter-select {
  width: 130px;
}

/* ── Document cards ── */
.doc-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: var(--spacing-lg);
}

.doc-card {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 16px 20px;
  background: #fff;
  cursor: pointer;
  border-radius: 12px;
  border: 1px solid transparent;
  transition: all .2s ease;
  box-shadow: 0 1px 3px rgba(0,0,0,.04);
}
.doc-card:hover {
  border-color: var(--color-border);
  box-shadow: 0 6px 20px rgba(0,0,0,.07);
  transform: translateY(-1px);
}
.doc-card:active {
  transform: translateY(0);
  box-shadow: 0 1px 3px rgba(0,0,0,.04);
}

/* Icon */
.doc-icon-area {
  width: 48px;
  height: 48px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.doc-ext-label {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: .5px;
  color: #fff;
  text-shadow: 0 1px 2px rgba(0,0,0,.2);
}

/* Content */
.doc-content {
  flex: 1;
  min-width: 0;
}
.doc-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 4px;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.doc-card:hover .doc-title {
  color: var(--color-primary);
}
.doc-meta-row {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--color-text-secondary);
  margin-bottom: 4px;
}
.doc-author { font-weight: 500; }
.doc-dot { color: #d0d0d0; }
.doc-date { }
.doc-version {
  background: #f0f4f8;
  color: var(--color-primary);
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 8px;
  font-weight: 600;
}
.doc-summary {
  font-size: 12.5px;
  color: #666;
  line-height: 1.5;
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.doc-snippet {
  font-size: 12.5px;
  color: var(--color-text-secondary);
  line-height: 1.5;
  margin: 0;
  background: var(--color-bg-secondary);
  padding: 8px 12px;
  border-radius: 6px;
  border-left: 3px solid var(--color-primary);
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* Right side */
.doc-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 8px;
  flex-shrink: 0;
}
.doc-tags {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
  justify-content: flex-end;
}
.doc-tag {
  font-size: 11px;
  color: var(--color-text-secondary);
  background: var(--color-bg-secondary);
  padding: 2px 8px;
  border-radius: 4px;
  white-space: nowrap;
}
.doc-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #bbb;
}
.doc-actions .el-icon { vertical-align: -2px; }

/* ── Empty state ── */
.empty-state {
  background: #fff;
  padding: 64px 24px;
  text-align: center;
}
.empty-icon {
  color: #d0d8e4;
  margin-bottom: 16px;
}
.empty-state h3 {
  font-size: 16px;
  color: var(--color-text-primary);
  margin: 0 0 6px;
  font-weight: 600;
}
.empty-state p {
  font-size: 13px;
  color: var(--color-text-secondary);
  margin: 0;
}

/* ── Pagination ── */
.pagination-wrap {
  background: #fff;
  padding: 16px;
  display: flex;
  justify-content: center;
}

@media (max-width: 768px) {
  .category-page { padding: var(--spacing-md); }
  .doc-right { display: none; }
  .doc-card { padding: 12px 16px; }
  .toolbar { flex-direction: column; }
  .toolbar-right { width: 100%; }
  .filter-select { width: 100%; }
  .sub-cat-pills {
    flex-wrap: nowrap;
    overflow-x: auto;
    s临床研究部llbar-width: none;
    -webkit-overflow-s临床研究部lling: touch;
    padding-bottom: 2px;
  }
  .sub-cat-pills::-webkit-s临床研究部llbar { display: none; }
  .pill { flex-shrink: 0; }
  .pagination-wrap {
    overflow-x: auto;
    justify-content: flex-start;
    -webkit-overflow-s临床研究部lling: touch;
    padding: 10px 6px;
  }
  .pagination-wrap :deep(.el-pagination) {
    flex-wrap: nowrap;
    min-width: max-content;
  }
  .pagination-wrap :deep(.el-pagination__sizes),
  .pagination-wrap :deep(.el-pagination__jump),
  .pagination-wrap :deep(.el-pagination__total) {
    display: none;
  }
  .toolbar-search { min-height: 44px; }
}
</style>
