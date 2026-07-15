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
        <template #append><el-button type="warning" @click="doSearch">搜索</el-button></template>
      </el-input>
    </div>

    <div v-if="results.length" class="search-meta">
      找到 <strong>{{ total }}</strong> 条结果
    </div>

    <div class="result-list" v-if="results.length">
      <div v-for="item in results" :key="item.id" class="result-item" @click="$router.push(`/document/${item.id}`)">
        <h3 v-html="highlight(item.title)"></h3>
        <p class="result-summary" v-if="item.summary" v-html="highlight(item.summary?.substring(0, 200))"></p>
        <div class="result-meta">
          <span>{{ item.uploader_name }}</span>
          <span>·</span>
          <span>{{ formatDate(item.updated_at) }}</span>
          <span>·</span>
          <span>{{ item.file_ext?.toUpperCase() || '链接' }}</span>
        </div>
        <div class="result-tags">
          <el-tag v-for="t in (item.tags || []).slice(0,3)" :key="t" size="small" type="info">{{ t }}</el-tag>
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
          @size-change="(s: number) => { size = s; doSearch(); }"
        />
      </div>
    </div>

    <el-empty v-else description="未找到相关文档" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Search } from '@element-plus/icons-vue'
import { get } from '@/api/client'
import dayjs from 'dayjs'

const route = useRoute()
const router = useRouter()
const query = ref('')
const results = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const size = ref(20)

function formatDate(d: string) { return dayjs(d).format('YYYY-MM-DD') }

function highlight(text: string) {
  if (!query.value || !text) return text
  // Escape HTML before inserting search highlight markers
  const escaped = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
  const re = new RegExp(`(${query.value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi')
  return escaped.replace(re, '<em style="background:#fff3cd;font-style:normal">$1</em>')
}

async function doSearch() {
  if (!query.value.trim()) { results.value = []; return }
  try {
    const params: any = { q: query.value.trim(), page: page.value, size: size.value }
    const resp: any = await get('/api/search', params)
    results.value = resp.items
    total.value = resp.total
  } catch { results.value = []; total.value = 0 }
}

onMounted(() => {
  if (route.query.q) {
    query.value = route.query.q as string
    doSearch()
  }
})
</script>

<style scoped>
.search-page { padding: var(--spacing-md) 0; }
.search-header { max-width: 700px; margin: 0 auto var(--spacing-lg); }
.search-meta { font-size: 14px; color: var(--color-text-secondary); margin-bottom: var(--spacing-md); }

.result-list { display: flex; flex-direction: column; gap: var(--spacing-sm); }
.result-item {
  background: #fff; border-radius: var(--radius-md); padding: var(--spacing-md) var(--spacing-lg);
  cursor: pointer; box-shadow: var(--shadow-card); transition: all .2s;
}
.result-item:hover { box-shadow: var(--shadow-hover); }
.result-item h3 { font-size: 15px; margin-bottom: 6px; color: var(--color-primary); }
.result-summary { font-size: 13px; color: var(--color-text-secondary); line-height: 1.6; margin-bottom: 8px; }
.result-meta { font-size: 12px; color: var(--color-text-secondary); margin-bottom: 6px; }
.result-tags { display: flex; gap: 4px; }

.pagination-wrap { display: flex; justify-content: center; padding: var(--spacing-lg); }
</style>
