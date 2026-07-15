<template>
  <div class="home-page">
    <!-- Welcome + search -->
    <div class="welcome-section">
      <div class="welcome-text">
        <h1 v-if="auth.user">你好，{{ auth.user.display_name }}</h1>
        <h1 v-else>迈瑞生知识库</h1>
        <p>{{ auth.user ? (auth.user.department + ' · ' + roleLabel) : '医疗器械注册 · 临床评价 · 临床试验 · 法规库' }}</p>
      </div>
      <div class="hero-search" :class="{ focused: searchFocused }">
        <el-icon class="hero-search-icon" :size="17"><Search /></el-icon>
        <input
          v-model="query"
          type="text"
          placeholder="搜文档、查法规、找指南..."
          class="hero-search-input"
          @focus="searchFocused = true"
          @blur="searchFocused = false"
          @keydown.escape="query = ''; searchFocused = false"
          @keyup.enter="search"
        />
        <span class="hero-search-hint">按 / 聚焦搜索</span>
        <button class="hero-search-btn" @click="search" :disabled="!query.trim()">
          搜索
        </button>
      </div>
    </div>

    <!-- Data overview bar -->
    <div class="stats-row">
      <div class="stat-card">
        <div class="stat-icon" style="background:#eef4fd;color:#1e50ae">
          <el-icon :size="20"><Document /></el-icon>
        </div>
        <div class="stat-info">
          <span class="stat-num">{{ homeStats.total_docs }}</span>
          <span class="stat-label">文档总数</span>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background:#edf7ee;color:#16a34a">
          <el-icon :size="20"><Clock /></el-icon>
        </div>
        <div class="stat-info">
          <span class="stat-num">{{ homeStats.week_updates }}</span>
          <span class="stat-label">本周更新</span>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background:#fef6ee;color:#fb8c00">
          <el-icon :size="20"><Folder /></el-icon>
        </div>
        <div class="stat-info">
          <span class="stat-num">{{ homeStats.total_categories }}</span>
          <span class="stat-label">分类数量</span>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background:#f0f4f8;color:#3b82f6">
          <el-icon :size="20"><User /></el-icon>
        </div>
        <div class="stat-info">
          <span class="stat-num">{{ homeStats.active_users }}</span>
          <span class="stat-label">活跃用户</span>
        </div>
      </div>
    </div>

    <!-- Category navigation cards (4-col grid) -->
    <div class="section" v-if="quickModules.length">
      <div class="section-header">
        <h2 class="section-title">分类导览</h2>
        <router-link to="/category" class="section-more">全部分类 →</router-link>
      </div>
      <div class="category-grid">
        <div
          v-for="mod in quickModules"
          :key="mod.id"
          class="category-card"
          @click="$router.push(`/category/${mod.id}`)"
        >
          <div class="category-card-icon">
            <el-icon :size="22"><Folder /></el-icon>
          </div>
          <span class="category-card-name">{{ cleanName(mod.name) }}</span>
          <span class="category-card-count">{{ mod.document_count || mod.children?.length || 0 }} 篇</span>
        </div>
      </div>
    </div>

    <!-- Announcement bar -->
    <div class="section" v-if="announcements.length">
      <div class="section-header">
        <h2 class="section-title">最新动态</h2>
      </div>
      <div class="announce-bar">
        <div
          v-for="item in announcements"
          :key="item.id"
          class="announce-item"
          @click="$router.push(`/document/${item.id}`)"
        >
          <span class="announce-dot"></span>
          <span class="announce-title">{{ item.title }}</span>
          <el-tag v-if="isNewDoc(item)" size="small" type="danger" effect="dark" round>NEW</el-tag>
          <span class="announce-date">{{ formatDate(item.updated_at) }}</span>
        </div>
      </div>
    </div>

    <!-- Popular documents (top 6 by views, 2-col grid) -->
    <div class="section" v-if="popularDocs.length">
      <div class="section-header">
        <h2 class="section-title">热门文档</h2>
      </div>
      <div class="popular-grid">
        <div
          v-for="doc in popularDocs"
          :key="doc.id"
          class="popular-card"
          @click="$router.push(`/document/${doc.id}`)"
        >
          <div class="popular-top">
            <span class="popular-ext" :style="{ background: iconBg(doc.file_ext) }">
              {{ doc.file_ext?.toUpperCase()?.substring(0, 3) || 'LNK' }}
            </span>
            <span class="popular-views">
              <el-icon :size="12"><View /></el-icon> {{ doc.view_count }}
            </span>
          </div>
          <h4 class="popular-title">{{ doc.title }}</h4>
          <p class="popular-summary" v-if="doc.summary">{{ doc.summary }}</p>
          <div class="popular-tags" v-if="doc.tags?.length">
            <span v-for="t in doc.tags.slice(0, 3)" :key="t" class="popular-tag">{{ t }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Quick links button group -->
    <div class="section">
      <div class="section-header">
        <h2 class="section-title">快捷入口</h2>
      </div>
      <div class="quick-links">
        <button class="quick-link-btn" @click="$router.push('/category')">
          <el-icon :size="16"><Folder /></el-icon> 全部分类
        </button>
        <button class="quick-link-btn" @click="$router.push('/search')">
          <el-icon :size="16"><Search /></el-icon> 高级搜索
        </button>
        <button class="quick-link-btn" @click="$router.push('/personal')">
          <el-icon :size="16"><User /></el-icon> 个人工作台
        </button>
        <button class="quick-link-btn" @click="$router.push('/contact')">
          <el-icon :size="16"><OfficeBuilding /></el-icon> 通讯录
        </button>
      </div>
    </div>

    <!-- Recent documents (2-column grid) -->
    <div class="section">
      <div class="section-header">
        <h2 class="section-title">最近更新</h2>
        <router-link to="/category" class="section-more">查看全部 →</router-link>
      </div>
      <div class="recent-grid">
        <div
          v-for="doc in recentDocs"
          :key="doc.id"
          class="recent-card"
          @click="$router.push(`/document/${doc.id}`)"
        >
          <div class="recent-card-top">
            <div class="recent-card-icon" :style="{ background: iconBg(doc.file_ext) }">
              <span class="recent-card-ext">{{ doc.file_ext?.toUpperCase()?.substring(0, 3) || 'LNK' }}</span>
            </div>
            <div class="recent-card-meta">
              <span>{{ doc.uploader_name }}</span>
              <span>{{ formatDate(doc.updated_at) }}</span>
            </div>
          </div>
          <h4 class="recent-card-title">{{ doc.title }}</h4>
          <div class="recent-card-tags" v-if="doc.tags?.length">
            <span v-for="t in doc.tags.slice(0, 2)" :key="t" class="recent-card-tag">{{ t }}</span>
          </div>
        </div>

        <div v-if="!recentDocs.length && !loading" class="recent-empty">
          <p>暂无文档，等待管理员上传</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Search, Document, Clock, Folder, User, View, OfficeBuilding } from '@element-plus/icons-vue'
import { get } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import dayjs from 'dayjs'

const router = useRouter()
const auth = useAuthStore()
const query = ref('')
const searchFocused = ref(false)
const recentDocs = ref<any[]>([])
const popularDocs = ref<any[]>([])
const announcements = ref<any[]>([])
const homeStats = ref({ total_docs: 0, week_updates: 0, total_categories: 0, active_users: 0 })
const quickModules = ref<any[]>([])
const loading = ref(false)

const roleLabel = computed(() => {
  const map: Record<string, string> = {
    super_admin: '超级管理员', dept_admin: '部门管理员',
    editor: '编辑者', employee: '员工', guest: '访客',
  }
  return map[auth.user?.role || ''] || ''
})

const iconBgMap: Record<string, string> = {
  pdf: '#fef0f0', doc: '#eef4fd', docx: '#eef4fd',
  xls: '#edf7ee', xlsx: '#edf7ee',
  ppt: '#fef6ee', pptx: '#fef6ee',
  link: '#e6f7f9',
}
function iconBg(ext: string) { return iconBgMap[ext?.toLowerCase()] || '#f0f4f8' }

function isNewDoc(doc: any) {
  if (!doc.updated_at) return false
  return dayjs().diff(dayjs(doc.updated_at), 'day') < 7
}

function formatDate(d: string) { return dayjs(d).format('MM-DD') }
function cleanName(name: string) { return name.replace(/^\d+\.\s*/, '') }
function search() { if (query.value.trim()) router.push({ path: '/search', query: { q: query.value.trim() } }) }

onMounted(async () => {
  loading.value = true
  try {
    // Parallel: stats + recent docs + popular docs + categories
    const [statsResp, recentResp, popularResp, cats] = await Promise.all([
      get('/api/stats').catch(() => null),
      get('/api/documents', { size: 8, sort: 'updated_at', order: 'desc' }).catch(() => null),
      get('/api/documents', { size: 6, sort: 'view_count', order: 'desc' }).catch(() => null),
      get('/api/categories').catch(() => []),
    ])

    if (statsResp) homeStats.value = statsResp as any
    if (recentResp) {
      recentDocs.value = recentResp.items || []
      announcements.value = (recentResp.items || []).slice(0, 6)
    }
    if (popularResp) popularDocs.value = (popularResp.items || []).filter((d: any) => (d.view_count || 0) > 0)
    if (cats) {
      const numbered = cats.filter((c: any) => /^\d+\./.test(c.name))
      quickModules.value = numbered.length > 0 ? numbered.slice(0, 8) : cats.filter((c: any) => c.name !== '公共知识区').slice(0, 8)
    }
  } catch { /* empty */ }
  loading.value = false
})
</script>

<style scoped>
.home-page {
  max-width: 960px;
  margin: 0 auto;
  padding: var(--spacing-lg) 0;
}

/* ── Welcome section ── */
.welcome-section {
  margin-bottom: var(--spacing-xl);
}
.welcome-text {
  margin-bottom: var(--spacing-md);
}
.welcome-text h1 {
  font-size: 36px;
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0 0 6px;
  letter-spacing: -0.5px;
}
.welcome-text p {
  font-size: 16px;
  color: #94a3b8;
  margin: 0;
}
/* Hero 搜索框 — 52px 高度，同 AppHeader 风格 */
.hero-search {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #f2f4f7;
  border: 1.5px solid transparent;
  border-radius: 12px;
  padding: 0 8px 0 16px;
  max-width: 640px;
  height: 52px;
  transition: all .2s ease;
}
.hero-search.focused {
  background: #fff;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(30, 80, 174, .07);
}
.hero-search-icon {
  color: var(--color-text-secondary);
  flex-shrink: 0;
}
.hero-search-input {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  font-size: 14px;
  color: var(--color-text-primary);
  font-family: inherit;
}
.hero-search-input::placeholder {
  color: #b0b8c4;
}
.hero-search-btn {
  padding: 8px 20px;
  background: var(--color-primary);
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  font-family: inherit;
  transition: background .15s ease;
  white-space: nowrap;
  flex-shrink: 0;
  line-height: 1.4;
}
.hero-search-hint {
  font-size: 11px;
  color: #b0b8c4;
  white-space: nowrap;
  flex-shrink: 0;
  margin-right: 4px;
}
.hero-search-btn:hover {
  background: var(--color-primary-light);
}
.hero-search-btn:disabled {
  opacity: .5;
  cursor: not-allowed;
}
.hero-search-btn:disabled:hover {
  background: var(--color-primary);
}

/* ── Stats row ── */
.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: var(--spacing-xl);
}
.stat-card {
  display: flex;
  align-items: center;
  gap: 12px;
  background: #fff;
  border-radius: 12px;
  padding: 16px 18px;
  border: 1px solid transparent;
  transition: all .15s ease;
  box-shadow: 0 1px 3px rgba(0,0,0,.04);
}
.stat-card:hover {
  border-color: var(--color-border);
  box-shadow: 0 4px 12px rgba(0,0,0,.06);
}
.stat-icon {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.stat-info {
  display: flex;
  flex-direction: column;
}
.stat-num {
  font-size: 20px;
  font-weight: 700;
  color: var(--color-text-primary);
  line-height: 1.2;
}
.stat-label {
  font-size: 12px;
  color: var(--color-text-secondary);
}

/* ── Common section ── */
.section {
  margin-bottom: var(--spacing-xl);
}
.section-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: var(--spacing-md);
}
.section-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0;
}
.section-more {
  font-size: 12px;
  color: var(--color-primary);
  font-weight: 500;
}

/* ── Category grid (4-col) ── */
.category-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
}
.category-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  background: #fff;
  border-radius: 12px;
  padding: 18px 12px;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all .15s ease;
  box-shadow: 0 1px 3px rgba(0,0,0,.04);
}
.category-card:hover {
  border-color: var(--color-border);
  box-shadow: 0 4px 12px rgba(0,0,0,.06);
  transform: translateY(-2px);
}
.category-card-icon {
  width: 44px; height: 44px;
  border-radius: 12px;
  background: #eef4fd;
  color: var(--color-primary);
  display: flex; align-items: center; justify-content: center;
}
.category-card-name {
  font-size: 13px; font-weight: 600;
  color: var(--color-text-primary);
  text-align: center;
  line-height: 1.3;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.category-card-count {
  font-size: 11px;
  color: var(--color-text-secondary);
}

/* ── Announcement bar ── */
.announce-bar {
  display: flex;
  gap: 0;
  background: #fff;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0,0,0,.04);
  border: 1px solid var(--color-border);
  flex-wrap: wrap;
}
.announce-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 18px;
  cursor: pointer;
  transition: background .12s;
  flex: 1 1 50%;
  min-width: 280px;
  border-bottom: 1px solid var(--color-bg-secondary);
}
.announce-item:nth-child(odd) {
  border-right: 1px solid var(--color-bg-secondary);
}
.announce-item:nth-last-child(-n+2):not(:nth-child(even):nth-last-child(-n+1)) {
  border-bottom: none;
}
.announce-item:hover { background: #fafcff; }
.announce-dot {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: var(--color-accent);
  flex-shrink: 0;
}
.announce-title {
  flex: 1;
  font-size: 13px;
  color: var(--color-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.announce-date {
  font-size: 11px;
  color: var(--color-text-secondary);
  flex-shrink: 0;
}

/* ── Popular docs (2-col) ── */
.popular-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}
.popular-card {
  background: #fff;
  border-radius: 12px;
  padding: 18px;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all .15s ease;
  box-shadow: 0 1px 3px rgba(0,0,0,.04);
}
.popular-card:hover {
  border-color: var(--color-border);
  box-shadow: 0 4px 12px rgba(0,0,0,.06);
}
.popular-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}
.popular-ext {
  padding: 3px 8px;
  border-radius: 4px;
  font-size: 10px; font-weight: 700;
  color: #555;
}
.popular-views {
  font-size: 11px;
  color: var(--color-text-secondary);
  display: flex; align-items: center; gap: 3px;
}
.popular-title {
  font-size: 13px; font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 6px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  line-height: 1.4;
}
.popular-summary {
  font-size: 12px;
  color: var(--color-text-secondary);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  line-height: 1.5;
  margin: 0 0 8px;
}
.popular-tags {
  display: flex; gap: 4px; flex-wrap: wrap;
}
.popular-tag {
  font-size: 10px;
  color: var(--color-text-secondary);
  background: var(--color-bg-secondary);
  padding: 1px 6px;
  border-radius: 3px;
}

/* ── Quick links ── */
.quick-links {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}
.quick-link-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 20px;
  background: var(--color-primary);
  border: 1px solid var(--color-primary);
  border-radius: 10px;
  font-size: 13px;
  font-weight: 500;
  color: #fff;
  cursor: pointer;
  font-family: inherit;
  transition: all .15s ease;
  box-shadow: 0 2px 6px rgba(30, 80, 174, .2);
}
.quick-link-btn:hover {
  background: var(--color-primary-light);
  border-color: var(--color-primary-light);
  box-shadow: 0 4px 12px rgba(30, 80, 174, .3);
  transform: translateY(-1px);
}
.quick-link-btn:active {
  transform: translateY(0);
}

/* ── Recent docs (2-col grid) ── */
.recent-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
  gap: 10px;
}
.recent-card {
  background: #fff;
  border-radius: 12px;
  padding: 16px 18px;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all .15s ease;
  box-shadow: 0 1px 3px rgba(0,0,0,.04);
}
.recent-card:hover {
  border-color: var(--color-border);
  box-shadow: 0 4px 12px rgba(0,0,0,.06);
}
.recent-card-top {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}
.recent-card-icon {
  width: 32px; height: 32px;
  border-radius: 6px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.recent-card-ext {
  font-size: 9px; font-weight: 700;
  color: #555;
}
.recent-card-meta {
  font-size: 11px;
  color: var(--color-text-secondary);
  display: flex; gap: 8px;
}
.recent-card-title {
  font-size: 13px; font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 6px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  line-height: 1.4;
}
.recent-card-tags {
  display: flex; gap: 4px;
}
.recent-card-tag {
  font-size: 10px;
  color: var(--color-text-secondary);
  background: var(--color-bg-secondary);
  padding: 1px 6px;
  border-radius: 3px;
}

.recent-empty {
  grid-column: 1 / -1;
  background: #fff;
  border-radius: 12px;
  padding: 32px;
  text-align: center;
  color: var(--color-text-secondary);
  font-size: 13px;
  box-shadow: 0 1px 3px rgba(0,0,0,.04);
}

/* ── Responsive ── */
@media (max-width: 1024px) {
  .category-grid { grid-template-columns: repeat(3, 1fr); }
  .popular-grid { grid-template-columns: 1fr; }
  .recent-grid { grid-template-columns: 1fr; }
}
@media (max-width: 768px) {
  .home-page { padding: var(--spacing-md); }
  .stats-row { grid-template-columns: repeat(2, 1fr); }
  .category-grid { grid-template-columns: repeat(2, 1fr); }
  .announce-item { flex: 1 1 100%; min-width: 0; }
  .announce-item:nth-child(odd) { border-right: none; }
  .welcome-text h1 { font-size: 20px; }
}
</style>
