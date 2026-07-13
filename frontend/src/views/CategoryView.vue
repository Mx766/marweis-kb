<template>
  <div class="category-page">
    <el-breadcrumb separator=">">
      <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
      <el-breadcrumb-item :to="{ path: '/category' }">知识库</el-breadcrumb-item>
      <el-breadcrumb-item v-if="currentCat">{{ currentCat.name }}</el-breadcrumb-item>
    </el-breadcrumb>

    <div class="category-layout">
      <!-- Left Sidebar: Category Tree -->
      <aside class="category-sidebar">
        <el-menu :default-active="activeCatId" class="cat-menu" @select="handleCatSelect">
          <el-menu-item
            v-for="cat in categoryTree"
            :key="cat.id"
            :index="cat.id"
          >
            <el-icon><Folder /></el-icon>
            <span>{{ cat.name }}</span>
          </el-menu-item>
        </el-menu>
      </aside>

      <!-- Right Content: Sub-categories + Document List -->
      <div class="category-content">
        <!-- Sub-category Tags -->
        <div v-if="subCategories.length" class="sub-cat-tags">
          <el-button
            :type="activeSubId ? '' : 'primary'"
            size="small"
            @click="activeSubId = ''; loadDocs()"
          >全部</el-button>
          <el-button
            v-for="sub in subCategories"
            :key="sub.id"
            :type="activeSubId === sub.id ? 'primary' : ''"
            size="small"
            @click="activeSubId = sub.id; loadDocs()"
          >{{ sub.name }}</el-button>
        </div>

        <!-- Search / Filter Row -->
        <div class="filter-row">
          <el-input v-model="searchKeyword" placeholder="在当前分类下搜索..." clearable size="default" style="width:300px" @change="loadDocs" />
          <el-select v-model="fileTypeFilter" placeholder="文件格式" clearable size="default" style="width:140px" @change="loadDocs">
            <el-option label="全部格式" value="" />
            <el-option label="链接 / 网页" value="link" />
            <el-option label="文档" value="file" />
          </el-select>
        </div>

        <!-- Document List -->
        <div class="doc-list">
          <div
            v-for="doc in docs"
            :key="doc.id"
            class="doc-row"
            @click="$router.push(`/document/${doc.id}`)"
          >
            <div class="doc-row-icon">
              <el-icon :size="22" :color="fileIconColor(doc.file_ext)"><Document /></el-icon>
            </div>
            <div class="doc-row-body">
              <h4>{{ doc.title }}</h4>
              <p class="doc-row-meta">
                <span>{{ doc.uploader_name }}</span>
                <span>·</span>
                <span>{{ formatDate(doc.updated_at) }}</span>
                <span>·</span>
                <span>{{ doc.file_ext.toUpperCase() || '链接' }}</span>
                <span v-if="doc.version">· v{{ doc.version }}</span>
              </p>
              <p class="doc-row-summary">{{ doc.summary?.substring(0, 120) }}{{ doc.summary?.length > 120 ? '...' : '' }}</p>
            </div>
            <div class="doc-row-tags">
              <el-tag v-for="t in (doc.tags || []).slice(0,3)" :key="t" size="small" type="info">{{ t }}</el-tag>
            </div>
          </div>

          <el-empty v-if="!loading && docs.length === 0" description="暂无文档" />

          <div class="pagination-wrap" v-if="total > size">
            <el-pagination
              v-model:current-page="page"
              :page-size="size"
              :total="total"
              layout="prev, pager, next"
              @current-change="loadDocs"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Folder, Document } from '@element-plus/icons-vue'
import { get } from '@/api/client'
import dayjs from 'dayjs'

const route = useRoute()
const router = useRouter()
const categoryTree = ref<any[]>([])
const currentCat = ref<any>(null)
const activeCatId = ref('')
const activeSubId = ref('')
const docs = ref<any[]>([])
const loading = ref(false)
const page = ref(1)
const total = ref(0)
const size = ref(20)
const searchKeyword = ref('')
const fileTypeFilter = ref('')

const subCategories = computed(() => {
  if (!currentCat.value?.children) return []
  return currentCat.value.children
})

function formatDate(d: string) { return dayjs(d).format('YYYY-MM-DD') }

const fileColors: Record<string, string> = { pdf: '#e74c3c', doc: '#2980b9', docx: '#2980b9', xls: '#27ae60', xlsx: '#27ae60', ppt: '#e67e22', pptx: '#e67e22', link: '#00bcd4' }
function fileIconColor(ext: string) { return fileColors[ext?.toLowerCase()] || '#7f8c8d' }

async function loadCategories() {
  categoryTree.value = await get('/api/categories')
}

async function loadDocs() {
  loading.value = true
  try {
    const catId = activeSubId.value || activeCatId.value
    const queryParams: any = { page: page.value, size: size.value, sort: 'updated_at', order: 'desc' }
    if (catId) queryParams.category_id = catId
    if (searchKeyword.value) queryParams.keyword = searchKeyword.value
    if (fileTypeFilter.value) queryParams.file_type = fileTypeFilter.value
    const resp: any = await get('/api/documents', queryParams)
    docs.value = resp.items
    total.value = resp.total
  } catch { docs.value = []; total.value = 0 }
  loading.value = false
}

function handleCatSelect(id: string) {
  activeCatId.value = id
  activeSubId.value = ''
  currentCat.value = categoryTree.value.find((c: any) => c.id === id)
  page.value = 1
  loadDocs()
}

watch(() => route.params.id, (id) => {
  if (id) {
    loadCategories().then(() => {
      activeCatId.value = id as string
      currentCat.value = categoryTree.value.find((c: any) => c.id === id)
      page.value = 1
      loadDocs()
    })
  } else {
    activeCatId.value = ''
    activeSubId.value = ''
    currentCat.value = null
    page.value = 1
    loadDocs()
  }
})

onMounted(async () => {
  await loadCategories()
  if (route.params.id) {
    activeCatId.value = route.params.id as string
    currentCat.value = categoryTree.value.find((c: any) => c.id === route.params.id)
  }
  loadDocs()
})
</script>

<style scoped>
.category-page { padding: var(--spacing-md) 0; }
.category-layout { display: flex; gap: var(--spacing-lg); margin-top: var(--spacing-md); }
.category-sidebar { width: 220px; flex-shrink: 0; background: #fff; border-radius: var(--radius-md); box-shadow: var(--shadow-card); }
.cat-menu { border-right: none; }
.cat-menu .el-menu-item { height: 42px; line-height: 42px; font-size: 14px; }
.cat-menu .el-menu-item.is-active { color: var(--color-accent); background: #fff7ed; }

.category-content { flex: 1; min-width: 0; }
.sub-cat-tags { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: var(--spacing-md); }
.filter-row { display: flex; gap: var(--spacing-sm); margin-bottom: var(--spacing-md); }

.doc-list { display: flex; flex-direction: column; gap: 1px; background: var(--color-border); border-radius: var(--radius-md); overflow: hidden; }
.doc-row {
  display: flex; gap: var(--spacing-md); padding: var(--spacing-md);
  background: #fff; cursor: pointer; transition: background .15s; align-items: flex-start;
}
.doc-row:hover { background: #fafbfc; }
.doc-row-icon { width: 40px; height: 40px; background: var(--color-bg-secondary); border-radius: var(--radius-sm); display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.doc-row-body { flex: 1; min-width: 0; }
.doc-row-body h4 { font-size: 14px; margin-bottom: 4px; }
.doc-row-meta { font-size: 12px; color: var(--color-text-secondary); margin-bottom: 2px; }
.doc-row-summary { font-size: 13px; color: var(--color-text-secondary); }
.doc-row-tags { display: flex; gap: 4px; flex-shrink: 0; }

.pagination-wrap { padding: var(--spacing-md); background: #fff; display: flex; justify-content: center; }
</style>
