<template>
  <div class="search-page">
    <div class="search-header">
      <el-input
        v-model="query"
        size="large"
        placeholder="搜索文档、法规、指南..."
        clearable
        @keyup.enter="doSearch"
        @clear="doSearch"
      >
        <template #prefix><el-icon><Search /></el-icon></template>
        <template #append><el-button type="primary" @click="doSearch">搜索</el-button></template>
      </el-input>
      <div class="search-filters">
        <el-select v-model="fileTypeFilter" placeholder="全部格式" clearable @change="doSearch" size="small">
          <el-option label="全部格式" value="" />
          <el-option label="PDF" value="pdf" />
          <el-option label="Word" value="doc" />
          <el-option label="Excel" value="xls" />
          <el-option label="外链" value="link" />
        </el-select>
      </div>
    </div>

    <div v-if="results.length" class="search-meta">
      找到 <strong>{{ total }}</strong> 条结果
      <span v-if="fileTypeFilter" class="filter-hint">（已筛选：{{ fileTypeLabel }}）</span>
    </div>

    <div class="result-list" v-if="results.length" v-loading="loading">
      <div v-for="item in results" :key="item.id" class="result-item" @click="openResult(item)">
        <div class="result-item-row">
          <div class="result-icon" :style="{ background: iconBg(item.file_ext) }">
            <span class="result-ext-label">{{ (item.file_ext || 'LNK').toUpperCase().substring(0, 4) }}</span>
          </div>
          <div class="result-content">
            <h3 v-html="highlight(item.title)"></h3>
            <p class="result-snippet" v-if="item.snippet" v-html="highlight(item.snippet)"></p>
            <div class="result-meta">
              <span>{{ item.uploader_name }}</span>
              <span>·</span>
              <span v-if="item.effective_date">发布于 {{ item.effective_date }}</span>
              <span v-else>更新于 {{ formatDate(item.updated_at) }}</span>
              <span v-if="isNew(item.effective_date)" class="result-new">新</span>
              <span>·</span>
              <span>{{ item.file_ext?.toUpperCase() || '链接' }}</span>
            </div>
            <div class="result-tags">
              <el-tag v-for="t in (item.tags || []).slice(0,3)" :key="t" size="small" type="info">{{ t }}</el-tag>
            </div>
          </div>
        </div>
      </div>

      <div class="pagination-wrap" v-if="total > size">
        <el-pagination
          v-model:current-page="page"
          :page-size="size"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          :page-sizes="[10,20,50]"
          @current-change="doSearch"
          @size-change="(s: number) => { size = s; page = 1; doSearch(); }"
        />
      </div>
    </div>

    <el-empty v-else-if="searched" description="未找到相关文档">
      <template #extra><el-button @click="$router.push('/category')">浏览全部分类</el-button></template>
    </el-empty>
    <div v-else class="search-placeholder">
      <el-icon :size="48" color="#d0d5dd"><Search /></el-icon>
      <p>输入关键词搜索文档、法规、指南</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Search } from '@element-plus/icons-vue'
import { get, client } from '@/api/client'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'

const route = useRoute()
const router = useRouter()
const query = ref('')
const results = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const size = ref(20)
const loading = ref(false)
const searched = ref(false)
const fileTypeFilter = ref('')

const iconBgMap: Record<string, string> = {
  pdf: '#ef4444', doc: '#3b82f6', docx: '#3b82f6',
  xls: '#16a34a', xlsx: '#16a34a', ppt: '#f97316', pptx: '#f97316',
  link: '#0891b2', txt: '#6b7280', md: '#6b7280',
}
function iconBg(ext: string) {
  const e = ext?.toLowerCase() || ''
  return iconBgMap[e] || '#6b7280'
}

function openResult(item: any) {
  // Bare link → open source URL directly
  if (item.file_type === 'link' && item.source_url && (!item.content_text || item.content_text.length < 100)) {
    window.open(item.source_url, '_blank')
    return
  }
  router.push(`/document/${item.id}`)
}

const fileTypeLabel = computed(() => {
  const m: Record<string, string> = { pdf: 'PDF', doc: 'Word', xls: 'Excel', link: '外链/文献' }
  return m[fileTypeFilter.value] || fileTypeFilter.value
})

function formatDate(d: string) { return dayjs(d).format('YYYY-MM-DD') }
function isNew(d: string | null | undefined) {
  if (!d) return false
  const days = dayjs().startOf('day').diff(dayjs(d).startOf('day'), 'day')
  return days >= 0 && days <= 14
}

function highlight(text: string) {
  if (!query.value || !text) return text
  // Escape HTML before inserting search highlight markers
  const escaped = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
  const re = new RegExp(`(${query.value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi')
  return escaped.replace(re, '<em style="background:#fef3c7;color:#b45309;font-style:normal;font-weight:600;padding:1px 3px;border-radius:3px">$1</em>')
}

async function doSearch() {
  if (!query.value.trim()) { results.value = []; total.value = 0; return }
  loading.value = true
  searched.value = true
  try {
    const params: any = { q: query.value.trim(), page: page.value, size: size.value }
    if (fileTypeFilter.value) params.file_type = fileTypeFilter.value
    // 搜索接口在磁盘繁忙/导入期间可能很慢，超时放宽到 120s，避免误显示“未找到”
    const resp: any = await client.get('/api/search', { params, timeout: 120000 })
    results.value = resp.items
    total.value = resp.total
    // Sync URL for bookmarking
    const q: Record<string,string> = { q: query.value.trim() }
    if (fileTypeFilter.value) q.file_type = fileTypeFilter.value
    router.replace({ query: q })
  } catch {
    results.value = []; total.value = 0
    ElMessage.error('搜索失败或超时，请稍后重试')
  }
  loading.value = false
}

onMounted(() => {
  if (route.query.q) {
    query.value = route.query.q as string
    if (route.query.file_type) fileTypeFilter.value = route.query.file_type as string
    doSearch()
  }
})

// 已在搜索页时，header 搜索框改变 query 也能触发搜索
watch(() => route.query.q, (newQ) => {
  if (newQ && newQ !== query.value) {
    query.value = newQ as string
    page.value = 1
    doSearch()
  }
})
</script>

<style scoped>
.search-page { padding: var(--spacing-md) 0; }
.search-header { max-width: 700px; margin: 0 auto var(--spacing-lg); }
.search-filters { margin-top: 10px; display: flex; justify-content: flex-end; }
.search-meta { font-size: 14px; color: var(--color-text-secondary); margin-bottom: var(--spacing-md); }
.filter-hint { color: var(--color-primary); font-weight: 500; margin-left: 8px; }

.result-list { display: flex; flex-direction: column; gap: var(--spacing-sm); }
.result-item {
  background: #fff; border-radius: var(--radius-md); padding: var(--spacing-md) var(--spacing-lg);
  cursor: pointer; box-shadow: var(--shadow-card); transition: all .2s;
}
.result-item:hover { box-shadow: var(--shadow-hover); transform: translateY(-1px); }
.result-item-row { display: flex; gap: 14px; align-items: flex-start; }
.result-icon {
  width: 44px; height: 44px; border-radius: 10px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
}
.result-ext-label { font-size: 10px; font-weight: 700; color: #fff; text-shadow: 0 1px 2px rgba(0,0,0,.2); }
.result-content { flex: 1; min-width: 0; }
.result-item h3 { font-size: 15px; margin-bottom: 6px; color: var(--color-primary); }
.result-snippet {
  font-size: 13px; color: var(--color-text-secondary); line-height: 1.6; margin-bottom: 8px;
  background: var(--color-bg-secondary); padding: 10px 14px; border-radius: 6px;
  border-left: 3px solid var(--color-primary);
  display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden;
}
.result-meta { font-size: 12px; color: var(--color-text-secondary); margin-bottom: 6px; }
.result-new {
  background: var(--color-primary);
  color: #fff;
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 8px;
  font-weight: 600;
  margin-left: 4px;
}
.result-tags { display: flex; gap: 4px; flex-wrap: wrap; }

.pagination-wrap { display: flex; justify-content: center; padding: var(--spacing-lg); }
</style>
