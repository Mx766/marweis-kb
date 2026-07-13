<template>
  <div class="home-page">
    <!-- Hero Banner -->
    <div class="hero-banner">
      <h1>迈瑞生知识库</h1>
      <p>医疗器械注册 · 临床评价 · 临床试验 · 法规库 — 一站式专业知识管理平台</p>
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

    <!-- Category Grid -->
    <div class="section">
      <h2 class="section-title">知识库导航</h2>
      <div class="category-grid">
        <div
          v-for="cat in categoryTree"
          :key="cat.id"
          class="category-card"
          @click="$router.push(`/category/${cat.id}`)"
        >
          <el-icon :size="32" :color="getIconColor(cat.name)"><Folder /></el-icon>
          <h3>{{ cat.name }}</h3>
          <p v-if="cat.children?.length">{{ cat.children.length }} 个子分类</p>
        </div>
      </div>
    </div>

    <!-- Recent Documents -->
    <div class="section">
      <div class="section-header">
        <h2 class="section-title">最近更新</h2>
        <router-link to="/category" class="more-link">查看全部 →</router-link>
      </div>
      <div class="doc-grid">
        <div v-for="doc in recentDocs" :key="doc.id" class="doc-card" @click="$router.push(`/document/${doc.id}`)">
          <div class="doc-icon">
            <el-icon :size="24"><Document /></el-icon>
          </div>
          <div class="doc-body">
            <h4>{{ doc.title }}</h4>
            <p class="doc-meta">
              <span>{{ doc.uploader_name }}</span>
              <span>·</span>
              <span>{{ formatDate(doc.created_at) }}</span>
            </p>
            <p class="doc-summary">{{ doc.summary?.substring(0, 80) }}{{ doc.summary?.length > 80 ? '...' : '' }}</p>
            <div class="doc-tags">
              <el-tag v-for="t in (doc.tags || []).slice(0, 3)" :key="t" size="small" type="info">{{ t }}</el-tag>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Search as SearchIcon, Folder, Document } from '@element-plus/icons-vue'
import { get } from '@/api/client'
import dayjs from 'dayjs'

const router = useRouter()
const query = ref('')
const categoryTree = ref<any[]>([])
const recentDocs = ref<any[]>([])

const colors = ['#1e50ae','#e74c3c','#27ae60','#e67e22','#9b59b6','#3498db','#1abc9c','#e91e63']
function getIconColor(name: string) {
  // Hash the category name to get a consistent color
  let hash = 0
  for (let i = 0; i < name.length; i++) hash = ((hash << 5) - hash + name.charCodeAt(i)) | 0
  return colors[Math.abs(hash) % colors.length]
}

function formatDate(d: string) { return dayjs(d).format('YYYY-MM-DD') }
function search() { if (query.value.trim()) router.push({ path: '/search', query: { q: query.value.trim() } }) }

onMounted(async () => {
  try {
    categoryTree.value = await get('/api/categories')
    const resp: any = await get('/api/documents', { size: 8, sort: 'updated_at', order: 'desc' })
    recentDocs.value = resp.items || []
  } catch { /* use seed data */ }
})
</script>

<style scoped>
.hero-banner {
  background: linear-gradient(135deg, #1e50ae 0%, #153b82 100%);
  border-radius: var(--radius-lg);
  padding: var(--spacing-2xl) var(--spacing-xl);
  text-align: center;
  color: #fff;
  margin-bottom: var(--spacing-xl);
}
.hero-banner h1 { font-size: 28px; margin-bottom: 8px; }
.hero-banner p { font-size: 15px; opacity: .85; margin-bottom: var(--spacing-lg); }
.hero-search { max-width: 560px; margin: 0 auto; }
.hero-search-input :deep(.el-input__wrapper) { border-radius: var(--radius-sm) 0 0 var(--radius-sm); }

.section { margin-bottom: var(--spacing-xl); }
.section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--spacing-md); }
.section-title { font-size: 18px; font-weight: 600; margin-bottom: var(--spacing-md); }
.more-link { font-size: 13px; color: var(--color-text-secondary); }
.more-link:hover { color: var(--color-primary); }

.category-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--spacing-md);
}
.category-card {
  background: #fff;
  border-radius: var(--radius-md);
  padding: var(--spacing-lg);
  text-align: center;
  cursor: pointer;
  box-shadow: var(--shadow-card);
  transition: all .2s;
}
.category-card:hover { transform: translateY(-2px); box-shadow: var(--shadow-hover); }
.category-card h3 { font-size: 14px; margin: 8px 0 4px; }
.category-card p { font-size: 12px; color: var(--color-text-secondary); }

.doc-grid { display: flex; flex-direction: column; gap: var(--spacing-sm); }
.doc-card {
  display: flex; gap: var(--spacing-md); padding: var(--spacing-md);
  background: #fff; border-radius: var(--radius-md); cursor: pointer;
  box-shadow: var(--shadow-card); transition: all .2s;
}
.doc-card:hover { box-shadow: var(--shadow-hover); }
.doc-icon { width: 48px; height: 48px; background: var(--color-bg-secondary); border-radius: var(--radius-sm); display: flex; align-items: center; justify-content: center; color: var(--color-primary); flex-shrink: 0; }
.doc-body { flex: 1; min-width: 0; }
.doc-body h4 { font-size: 14px; margin-bottom: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.doc-meta { font-size: 12px; color: var(--color-text-secondary); margin-bottom: 4px; }
.doc-summary { font-size: 13px; color: var(--color-text-secondary); margin-bottom: 6px; }
.doc-tags { display: flex; gap: 4px; }

@media (max-width: 1024px) { .category-grid { grid-template-columns: repeat(3, 1fr); } }
@media (max-width: 768px) { .category-grid { grid-template-columns: repeat(2, 1fr); } }
</style>
