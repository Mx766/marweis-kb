<template>
  <div class="category-page">
    <!-- Breadcrumb -->
    <el-breadcrumb separator=">">
      <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
      <el-breadcrumb-item v-if="currentCat">{{ currentCat.name }}</el-breadcrumb-item>
    </el-breadcrumb>

    <!-- Sub-category filter tabs -->
    <div v-if="subCategories.length" class="sub-cat-tabs">
      <el-button :type="!activeSubId ? 'primary' : ''" size="small" @click="setSub('')">全部</el-button>
      <el-button
        v-for="sub in subCategories"
        :key="sub.id"
        :type="activeSubId === sub.id ? 'primary' : ''"
        size="small"
        @click="setSub(sub.id)"
      >{{ sub.name }}</el-button>
    </div>

    <!-- Search / Filter Row -->
    <div class="filter-row">
      <el-input v-model="searchKeyword" placeholder="在当前分类下搜索..." clearable @change="doLoad" style="width:280px" />
      <el-select v-model="fileTypeFilter" placeholder="文件格式" clearable @change="doLoad" style="width:130px">
        <el-option label="全部" value="" />
        <el-option label="链接" value="link" />
        <el-option label="文件" value="file" />
      </el-select>
    </div>

    <!-- Document List -->
    <div class="doc-list" v-loading="loading">
      <div
        v-for="doc in docs" :key="doc.id"
        class="doc-row"
        @click="$router.push(`/document/${doc.id}`)"
      >
        <div class="doc-row-icon">
          <el-icon :size="22" :color="fileIconColor(doc.file_ext)"><Document /></el-icon>
        </div>
        <div class="doc-row-body">
          <h4>{{ doc.title }}</h4>
          <p class="doc-row-meta">
            <span>{{ doc.uploader_name }}</span><span>·</span>
            <span>{{ formatDate(doc.updated_at) }}</span><span>·</span>
            <span>{{ doc.file_ext?.toUpperCase() || '链接' }}</span>
            <span v-if="doc.version">· v{{ doc.version }}</span>
          </p>
          <p class="doc-row-summary" v-if="doc.summary">{{ doc.summary?.substring(0, 120) }}{{ doc.summary?.length > 120 ? '...' : '' }}</p>
        </div>
        <div class="doc-row-tags">
          <el-tag v-for="t in (doc.tags || []).slice(0,3)" :key="t" size="small" type="info">{{ t }}</el-tag>
        </div>
      </div>

      <el-empty v-if="!loading && docs.length === 0" description="暂无文档" />

      <div class="pagination-wrap" v-if="total > size">
        <el-pagination v-model:current-page="page" :page-size="size" :total="total" layout="prev, pager, next" @current-change="doLoad" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Document } from '@element-plus/icons-vue'
import { get } from '@/api/client'
import dayjs from 'dayjs'

const route = useRoute()

interface Cat { id: string; name: string; children?: Cat[] }
const currentCat = ref<Cat | null>(null)
const activeSubId = ref('')
const docs = ref<any[]>([])
const loading = ref(false)
const page = ref(1)
const total = ref(0)
const size = ref(20)
const searchKeyword = ref('')
const fileTypeFilter = ref('')

const subCategories = computed(() => currentCat.value?.children || [])

function formatDate(d: string) { return dayjs(d).format('YYYY-MM-DD') }

const fileColors: Record<string,string> = { pdf:'#e74c3c',doc:'#2980b9',docx:'#2980b9',xls:'#27ae60',xlsx:'#27ae60',ppt:'#e67e22',pptx:'#e67e22',link:'#00bcd4' }
function fileIconColor(ext: string) { return fileColors[ext?.toLowerCase()] || '#7f8c8d' }

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

function setSub(subId: string) {
  activeSubId.value = subId
  page.value = 1
  doLoad()
}

async function doLoad() {
  loading.value = true
  try {
    const catId = activeSubId.value || (currentCat.value?.id || '')
    const params: any = { page: page.value, size: size.value, sort: 'updated_at', order: 'desc' }
    if (catId) params.category_id = catId
    if (searchKeyword.value) params.keyword = searchKeyword.value
    if (fileTypeFilter.value) params.file_type = fileTypeFilter.value
    const resp: any = await get('/api/documents', params)
    docs.value = resp.items || []
    total.value = resp.total || 0
  } catch { docs.value = []; total.value = 0 }
  loading.value = false
}

async function loadCategory(id: string) {
  const tree: Cat[] = await get('/api/categories')
  currentCat.value = findByCat(tree, id) || null
  activeSubId.value = ''
  page.value = 1
  doLoad()
}

// Watch route param changes
watch(() => route.params.id, (id) => {
  if (id && typeof id === 'string') {
    loadCategory(id)
  } else {
    currentCat.value = null
    activeSubId.value = ''
    doLoad()
  }
}, { immediate: true })
</script>

<style scoped>
.category-page { padding: 0; }
.el-breadcrumb { margin-bottom: var(--spacing-md); }

.sub-cat-tabs { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: var(--spacing-md); }
.filter-row { display: flex; gap: var(--spacing-sm); margin-bottom: var(--spacing-md); }

.doc-list { }
.doc-row {
  display: flex; gap: var(--spacing-md); padding: var(--spacing-md);
  background: #fff; cursor: pointer; transition: background .15s; align-items: flex-start;
  border-bottom: 1px solid #f0f0f0;
}
.doc-row:first-child { border-radius: var(--radius-md) var(--radius-md) 0 0; }
.doc-row:last-child { border-radius: 0 0 var(--radius-md) var(--radius-md); border-bottom: none; }
.doc-row:hover { background: #fafbfc; }
.doc-row-icon { width: 40px; height: 40px; background: var(--color-bg-secondary); border-radius: var(--radius-sm); display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.doc-row-body { flex: 1; min-width: 0; }
.doc-row-body h4 { font-size: 14px; margin-bottom: 4px; }
.doc-row-meta { font-size: 12px; color: var(--color-text-secondary); margin-bottom: 2px; }
.doc-row-summary { font-size: 13px; color: var(--color-text-secondary); }
.doc-row-tags { display: flex; gap: 4px; flex-shrink: 0; }
.pagination-wrap { padding: var(--spacing-md); display: flex; justify-content: center; }
</style>
