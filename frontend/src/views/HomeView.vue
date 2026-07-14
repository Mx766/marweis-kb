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
        <button class="hero-search-btn" @click="search" :disabled="!query.trim()">
          搜索
        </button>
      </div>
    </div>

    <!-- Quick stats -->
    <div class="stats-row">
      <div class="stat-card" @click="$router.push('/personal')">
        <div class="stat-icon" style="background:#eef4fd;color:#1e50ae">
          <el-icon :size="20"><Document /></el-icon>
        </div>
        <div class="stat-info">
          <span class="stat-num">{{ stats.total_uploads }}</span>
          <span class="stat-label">我的上传</span>
        </div>
      </div>
      <div class="stat-card" @click="$router.push('/personal?tab=favorites')">
        <div class="stat-icon" style="background:#fef6ee;color:#fb8c00">
          <el-icon :size="20"><Star /></el-icon>
        </div>
        <div class="stat-info">
          <span class="stat-num">{{ stats.total_favorites }}</span>
          <span class="stat-label">我的收藏</span>
        </div>
      </div>
      <div class="stat-card" @click="$router.push('/personal?tab=history')">
        <div class="stat-icon" style="background:#edf7ee;color:#27ae60">
          <el-icon :size="20"><Clock /></el-icon>
        </div>
        <div class="stat-info">
          <span class="stat-num">{{ stats.total_history }}</span>
          <span class="stat-label">最近浏览</span>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background:#f0f4f8;color:#7f8c8d">
          <el-icon :size="20"><Folder /></el-icon>
        </div>
        <div class="stat-info">
          <span class="stat-num">{{ totalDocs }}</span>
          <span class="stat-label">文档总数</span>
        </div>
      </div>
    </div>

    <!-- Quick access -->
    <div class="section" v-if="quickModules.length">
      <div class="section-header">
        <h2 class="section-title">快捷入口</h2>
      </div>
      <div class="quick-grid">
        <div
          v-for="mod in quickModules"
          :key="mod.id"
          class="quick-card"
          @click="$router.push(`/category/${mod.id}`)"
        >
          <div class="quick-card-icon">
            <el-icon :size="20"><Folder /></el-icon>
          </div>
          <div class="quick-card-info">
            <span class="quick-card-name">{{ cleanName(mod.name) }}</span>
            <span class="quick-card-desc">{{ mod.children?.length || 0 }} 个子分类</span>
          </div>
          <el-icon class="quick-card-arrow" :size="14"><ArrowRight /></el-icon>
        </div>
      </div>
    </div>

    <!-- Recent documents -->
    <div class="section">
      <div class="section-header">
        <h2 class="section-title">最近更新</h2>
        <router-link to="/category" class="section-more">查看全部 →</router-link>
      </div>
      <div class="recent-list">
        <div
          v-for="doc in recentDocs"
          :key="doc.id"
          class="recent-item"
          @click="$router.push(`/document/${doc.id}`)"
        >
          <div class="recent-icon" :style="{ background: iconBg(doc.file_ext) }">
            <span class="recent-ext">{{ doc.file_ext?.toUpperCase()?.substring(0, 3) || 'LNK' }}</span>
          </div>
          <div class="recent-body">
            <h4>{{ doc.title }}</h4>
            <p class="recent-meta">
              {{ doc.uploader_name }} · {{ formatDate(doc.updated_at) }}
              <span v-if="doc.view_count" class="recent-views">· {{ doc.view_count }} 次浏览</span>
            </p>
          </div>
          <div class="recent-tags" v-if="doc.tags?.length">
            <span v-for="t in doc.tags.slice(0, 2)" :key="t" class="recent-tag">{{ t }}</span>
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
import { Search, Document, Star, Clock, Folder, ArrowRight } from '@element-plus/icons-vue'
import { get } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import dayjs from 'dayjs'

const router = useRouter()
const auth = useAuthStore()
const query = ref('')
const searchFocused = ref(false)
const recentDocs = ref<any[]>([])
const stats = ref({ total_uploads: 0, total_favorites: 0, total_history: 0 })
const totalDocs = ref(0)
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

function formatDate(d: string) { return dayjs(d).format('MM-DD') }
function cleanName(name: string) { return name.replace(/^\d+\.\s*/, '') }
function search() { if (query.value.trim()) router.push({ path: '/search', query: { q: query.value.trim() } }) }

onMounted(async () => {
  loading.value = true
  try {
    // Load recent docs
    const resp: any = await get('/api/documents', { size: 8, sort: 'updated_at', order: 'desc' })
    recentDocs.value = resp.items || []
    totalDocs.value = resp.total || 0

    // Load user stats
    try { stats.value = await get('/api/me/stats') } catch { /* guest user */ }

    // Load quick access modules
    try {
      const cats: any[] = await get('/api/categories')
      const numbered = cats.filter(c => /^\d+\./.test(c.name))
      if (numbered.length > 0) {
        quickModules.value = numbered.slice(0, 6)
      } else {
        quickModules.value = cats.filter(c => c.name !== '公共知识区').slice(0, 6)
      }
    } catch { quickModules.value = [] }
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
  font-size: 24px;
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0 0 4px;
}
.welcome-text p {
  font-size: 13px;
  color: var(--color-text-secondary);
  margin: 0;
}
/* 与 AppHeader 搜索框同风格，40px 高度 + 搜索按钮 */
.hero-search {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #f2f4f7;
  border: 1.5px solid transparent;
  border-radius: 10px;
  padding: 0 8px 0 14px;
  max-width: 520px;
  height: 40px;
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
  padding: 6px 16px;
  background: var(--color-primary);
  color: #fff;
  border: none;
  border-radius: 7px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  font-family: inherit;
  transition: background .15s ease;
  white-space: nowrap;
  flex-shrink: 0;
  line-height: 1.4;
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
  cursor: pointer;
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

/* ── Quick access ── */
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

.quick-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}
.quick-card {
  display: flex;
  align-items: center;
  gap: 12px;
  background: #fff;
  border-radius: 10px;
  padding: 14px 16px;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all .15s ease;
  box-shadow: 0 1px 3px rgba(0,0,0,.04);
}
.quick-card:hover {
  border-color: var(--color-border);
  box-shadow: 0 4px 12px rgba(0,0,0,.06);
}
.quick-card-icon {
  width: 38px;
  height: 38px;
  border-radius: 8px;
  background: #eef4fd;
  color: var(--color-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.quick-card-info {
  flex: 1;
  min-width: 0;
}
.quick-card-name {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.quick-card-desc {
  font-size: 11px;
  color: var(--color-text-secondary);
}
.quick-card-arrow {
  color: #ccc;
  flex-shrink: 0;
  transition: transform .15s;
}
.quick-card:hover .quick-card-arrow {
  transform: translateX(2px);
  color: var(--color-primary);
}

/* ── Recent documents ── */
.recent-list {
  display: flex;
  flex-direction: column;
  gap: 1px;
  background: var(--color-border);
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid var(--color-border);
}
.recent-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px 18px;
  background: #fff;
  cursor: pointer;
  transition: background .12s;
}
.recent-item:hover { background: #fafcff; }
.recent-item:first-child { border-radius: 11px 11px 0 0; }
.recent-item:last-child { border-radius: 0 0 11px 11px; }

.recent-icon {
  width: 38px;
  height: 38px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.recent-ext {
  font-size: 10px;
  font-weight: 700;
  color: #666;
}
.recent-body {
  flex: 1;
  min-width: 0;
}
.recent-body h4 {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.recent-meta {
  font-size: 11.5px;
  color: var(--color-text-secondary);
  margin: 0;
}
.recent-views { color: #bbb; }

.recent-tags {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}
.recent-tag {
  font-size: 10px;
  color: var(--color-text-secondary);
  background: var(--color-bg-secondary);
  padding: 2px 6px;
  border-radius: 3px;
  white-space: nowrap;
}

.recent-empty {
  background: #fff;
  padding: 32px;
  text-align: center;
  color: var(--color-text-secondary);
  font-size: 13px;
}

@media (max-width: 768px) {
  .home-page { padding: var(--spacing-md); }
  .stats-row { grid-template-columns: repeat(2, 1fr); }
  .quick-grid { grid-template-columns: 1fr 1fr; }
  .recent-tags { display: none; }
  .welcome-text h1 { font-size: 20px; }
}
</style>
