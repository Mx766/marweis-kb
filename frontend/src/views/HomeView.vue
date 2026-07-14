<template>
  <div class="home-page">
    <div class="hero-banner">
      <h1>迈瑞生知识库</h1>
      <p>医疗器械注册 · 临床评价 · 临床试验 · 法规库</p>
      <div class="hero-search">
        <el-input
          v-model="query"
          size="large"
          placeholder="搜文档、查法规、找指南..."
          :prefix-icon="SearchIcon"
          class="hero-search-input"
          @keyup.enter="search"
        >
          <template #append>
            <el-button type="warning" @click="search">搜索</el-button>
          </template>
        </el-input>
      </div>
    </div>

    <div class="section">
      <h2 class="section-title">最近更新</h2>
      <div class="doc-grid">
        <div v-for="doc in recentDocs" :key="doc.id" class="doc-card" @click="$router.push(`/document/${doc.id}`)">
          <div class="doc-icon-bg">
            <el-icon :size="22"><Document /></el-icon>
          </div>
          <div class="doc-body">
            <h4>{{ doc.title }}</h4>
            <p class="doc-meta">
              <span>{{ doc.uploader_name }}</span>
              <span>·</span>
              <span>{{ formatDate(doc.updated_at) }}</span>
              <span>·</span>
              <el-tag size="small">{{ doc.file_ext?.toUpperCase() || '链接' }}</el-tag>
            </p>
            <p class="doc-summary" v-if="doc.summary">{{ doc.summary?.substring(0, 100) }}{{ doc.summary?.length > 100 ? '...' : '' }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Search as SearchIcon, Document } from '@element-plus/icons-vue'
import { get } from '@/api/client'
import dayjs from 'dayjs'

const router = useRouter()
const query = ref('')
const recentDocs = ref<any[]>([])

function formatDate(d: string) { return dayjs(d).format('YYYY-MM-DD') }
function search() { if (query.value.trim()) router.push({ path: '/search', query: { q: query.value.trim() } }) }

onMounted(async () => {
  try {
    const resp: any = await get('/api/documents', { size: 10, sort: 'updated_at', order: 'desc' })
    recentDocs.value = resp.items || []
  } catch { /* empty */ }
})
</script>

<style scoped>
.hero-banner {
  background: linear-gradient(135deg, #c88a04 0%, #9a6b04 100%);
  border-radius: var(--radius-lg);
  padding: var(--spacing-xl) var(--spacing-lg);
  text-align: center;
  color: #fff;
  margin-bottom: var(--spacing-xl);
}
.hero-banner h1 { font-size: 24px; margin-bottom: 6px; font-weight: 700; }
.hero-banner p { font-size: 14px; opacity: .85; margin-bottom: var(--spacing-md); }
.hero-search { max-width: 520px; margin: 0 auto; }
.hero-search-input :deep(.el-input__wrapper) { border-radius: var(--radius-sm) 0 0 var(--radius-sm); }

.section { margin-bottom: var(--spacing-xl); }
.section-title { font-size: 16px; font-weight: 600; margin-bottom: var(--spacing-md); color: var(--color-text-primary); }

.doc-grid { display: flex; flex-direction: column; gap: var(--spacing-sm); }
.doc-card {
  display: flex; gap: var(--spacing-md); padding: var(--spacing-md);
  background: #fff; border-radius: var(--radius-md); cursor: pointer;
  box-shadow: var(--shadow-card); transition: all .15s;
}
.doc-card:hover { box-shadow: var(--shadow-hover); }
.doc-icon-bg {
  width: 44px; height: 44px;
  background: #fef3c7;
  border-radius: var(--radius-sm);
  display: flex; align-items: center; justify-content: center;
  color: #c88a04; flex-shrink: 0;
}
.doc-body { flex: 1; min-width: 0; }
.doc-body h4 { font-size: 14px; margin-bottom: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.doc-meta { font-size: 12px; color: var(--color-text-secondary); margin-bottom: 2px; display: flex; align-items: center; gap: 4px; flex-wrap: wrap; }
.doc-summary { font-size: 13px; color: var(--color-text-secondary); line-height: 1.5; }
</style>
