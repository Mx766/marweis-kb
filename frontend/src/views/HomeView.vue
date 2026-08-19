<template>
  <div class="home-page">
    <!-- ═══ ADMIN HOME ═══ -->
    <template v-if="auth.isSuperAdmin">
      <div class="welcome-section admin-welcome">
        <div class="welcome-text">
          <h1>管理驾驶舱</h1>
          <p>欢迎回来，{{ auth.user?.display_name }} · {{ auth.user?.department }} · {{ roleLabel }}</p>
        </div>
      </div>

      <!-- Admin stat cards (clickable shortcuts) -->
      <div class="admin-stats-row">
        <div class="admin-stat-card" @click="$router.push('/admin/documents')">
          <div class="asc-icon" style="background:#eef4fd;color:#1e50ae"><el-icon :size="20"><Document /></el-icon></div>
          <div class="asc-info"><span class="asc-num">{{ fmtNum(adminData.total_docs) }}</span><span class="asc-label">文档总数</span></div>
        </div>
        <div class="admin-stat-card" @click="$router.push('/admin/users')">
          <div class="asc-icon" style="background:#edf7ee;color:#16a34a"><el-icon :size="20"><User /></el-icon></div>
          <div class="asc-info"><span class="asc-num">{{ fmtNum(adminData.total_users) }}</span><span class="asc-label">活跃用户</span></div>
        </div>
        <div class="admin-stat-card" @click="$router.push('/admin/categories')">
          <div class="asc-icon" style="background:#fef6ee;color:#f59e0b"><el-icon :size="20"><Folder /></el-icon></div>
          <div class="asc-info"><span class="asc-num">{{ fmtNum(adminData.total_categories) }}</span><span class="asc-label">分类数量</span></div>
        </div>
        <div class="admin-stat-card" @click="$router.push('/admin')">
          <div class="asc-icon" style="background:#f0f4f8;color:#3b82f6"><el-icon :size="20"><DataAnalysis /></el-icon></div>
          <div class="asc-info"><span class="asc-num">{{ fmtNum(adminData.total_views) }}</span><span class="asc-label">总浏览量</span></div>
        </div>
      </div>
    </template>

    <!-- ═══ EMPLOYEE HOME ═══ -->
    <template v-else>
      <div class="welcome-section">
        <div class="welcome-text">
          <h1 v-if="auth.user">你好，{{ auth.user.display_name }}</h1>
          <h1 v-else>企业知识库</h1>
          <p>{{ auth.user ? (auth.user.department + ' · ' + roleLabel) : '医疗器械注册 · 临床评价 · 临床试验 · 法规库' }}</p>
        </div>
        <div class="hero-search" :class="{ focused: searchFocused }">
          <el-icon class="hero-search-icon" :size="17"><Search /></el-icon>
          <input v-model="query" type="text" placeholder="搜文档、查法规、找指南..." class="hero-search-input"
            @focus="searchFocused = true" @blur="searchFocused = false"
            @keydown.escape="query = ''; searchFocused = false" @keyup.enter="search" />
          <span class="hero-search-hint">按 / 聚焦搜索</span>
          <button class="hero-search-btn" @click="search" :disabled="!query.trim()">搜索</button>
        </div>
      </div>
    </template>

    <!-- Data overview bar (employee) -->
    <div v-if="!auth.isSuperAdmin" class="stats-row employee-stats">
      <div class="stat-card" @click="$router.push('/category')">
        <div class="stat-icon" style="background:#eef4fd;color:#1e50ae"><el-icon :size="20"><Document /></el-icon></div>
        <div class="stat-info">
          <span class="stat-num">{{ homeStats.total_docs }}</span>
          <span class="stat-label">浏览文档 →</span>
        </div>
      </div>
      <div class="stat-card" @click="s临床研究部llToRecent">
        <div class="stat-icon" style="background:#edf7ee;color:#16a34a"><el-icon :size="20"><Clock /></el-icon></div>
        <div class="stat-info">
          <span class="stat-num">{{ homeStats.week_updates }}</span>
          <span class="stat-label">最近更新 →</span>
        </div>
      </div>
      <div class="stat-card" @click="$router.push('/personal?tab=favorites')">
        <div class="stat-icon" style="background:#fdf2f8;color:#e74c3c"><el-icon :size="20"><Star /></el-icon></div>
        <div class="stat-info">
          <span class="stat-num">{{ personalStats.total_favorites }}</span>
          <span class="stat-label">我的收藏 →</span>
        </div>
      </div>
      <div class="stat-card" @click="$router.push('/personal?tab=history')">
        <div class="stat-icon" style="background:#fef6ee;color:#fb8c00"><el-icon :size="20"><View /></el-icon></div>
        <div class="stat-info">
          <span class="stat-num">{{ personalStats.total_history }}</span>
          <span class="stat-label">浏览历史 →</span>
        </div>
      </div>
    </div>

    <!-- Popular documents (top 6 by views, 2-col grid) -->
    <div class="section" v-if="popularDocs.length && !auth.isSuperAdmin">
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
              {{ doc.file_ext?.toUpperCase()?.substring(0, 4) || 'LINK' }}
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

    <!-- Recent documents (2-column grid) -->
    <div class="section" id="recent-section" v-loading="loading">
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
              <span class="recent-card-ext">{{ doc.file_ext?.toUpperCase()?.substring(0, 4) || 'LINK' }}</span>
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
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { Search, Document, Clock, Folder, User, View, DataAnalysis, Star } from '@element-plus/icons-vue'
import { get } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import dayjs from 'dayjs'

const router = useRouter()
const auth = useAuthStore()
const query = ref('')
const searchFocused = ref(false)
const recentDocs = ref<any[]>([])
const popularDocs = ref<any[]>([])
const homeStats = ref({ total_docs: 0, week_updates: 0, total_categories: 0, active_users: 0 })
const adminData = ref({ total_docs: 0, total_users: 0, total_categories: 0, total_views: 0 })
const personalStats = ref({ total_uploads: 0, total_favorites: 0, total_history: 0 })
const loading = ref(false)

function fmtNum(n: number | undefined) {
  if (!n) return '0'
  if (n >= 10000) return (n / 10000).toFixed(1) + 'w'
  if (n >= 1000) return (n / 1000).toFixed(1) + 'k'
  return String(n)
}

import { getRoleLabel } from '@/utils/roles'
const roleLabel = computed(() => getRoleLabel(auth.user?.role))

import { getFileIconBg } from '@/utils/fileTypes'
function iconBg(ext: string) { return getFileIconBg(ext) }

function formatDate(d: string) { return dayjs(d).format('MM-DD') }
function cleanName(name: string) { return name.replace(/^\d+\.\s*/, '') }
function search() { if (query.value.trim()) router.push({ path: '/search', query: { q: query.value.trim() } }) }
function s临床研究部llToRecent() {
  const el = document.getElementById('recent-section')
  if (el) el.s临床研究部llIntoView({ behavior: '临床运营部oth', block: 'start' })
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === '/' && !auth.isSuperAdmin) {
    const active = document.activeElement
    if (!active || active.tagName === 'BODY' || (active as HTMLElement).closest?.('.hero-search')) return
    e.preventDefault()
    const input = document.querySelector('.hero-search-input') as HTMLInputElement
    input?.focus()
  }
}

onMounted(async () => {
  document.addEventListener('keydown', handleKeydown)
  loading.value = true
  try {
    // Parallel: stats + recent docs + popular docs + categories
    const [statsResp, recentResp, popularResp] = await Promise.all([
      get('/api/stats').catch(() => null),
      get('/api/documents', { size: 8, sort: 'updated_at', order: 'desc' }).catch(() => null),
      get('/api/documents', { size: 6, sort: 'view_count', order: 'desc' }).catch(() => null),
    ])

    if (statsResp) homeStats.value = statsResp as any

    // Admin: load dashboard overview
    if (auth.isSuperAdmin) {
      try {
        const dash: any = await get('/api/admin/dashboard')
        adminData.value = dash.overview || adminData.value
      } catch { console.error('dashboard load failed') }
    } else {
      // Employee: load personal favorites count
      try {
        personalStats.value = await get('/api/me/stats')
      } catch { /* guest user, leave at 0 */ }
    }
    // Filter: exclude bare links (no content, link type) from homepage
    const hasContent = (d: any) => d.file_type !== 'link' || (d.content_text && d.content_text.length >= 100)
    if (recentResp) {
      recentDocs.value = (recentResp.items || []).filter(hasContent)
    }
    if (popularResp) popularDocs.value = (popularResp.items || []).filter((d: any) => (d.view_count || 0) > 0 && hasContent(d))
  } catch { /* empty */ }
  loading.value = false
})

onBeforeUnmount(() => {
  document.removeEventListener('keydown', handleKeydown)
})
</script>

<style scoped>
.home-page {
  max-width: 960px;
  margin: 0 auto;
  padding: var(--spacing-lg) 0;
}

/* ── Admin home ── */
.admin-welcome {
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
  padding: 32px;
  border-radius: 16px;
  color: #fff;
  margin-bottom: var(--spacing-xl);
}
.admin-welcome h1 { color: #fff !important; }
.admin-welcome p { color: rgba(255,255,255,.7) !important; }

.admin-stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: var(--spacing-xl);
}
.admin-stat-card {
  display: flex; align-items: center; gap: 12px;
  background: #fff; border-radius: 12px; padding: 18px 20px;
  box-shadow: 0 1px 3px rgba(0,0,0,.04); transition: all .15s;
  cursor: pointer;
}
.admin-stat-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,.06); transform: translateY(-2px); }
.asc-icon { width: 44px; height: 44px; border-radius: 10px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.asc-info { display: flex; flex-direction: column; }
.asc-num { font-size: 22px; font-weight: 700; color: var(--color-text-primary); line-height: 1.1; }
.asc-label { font-size: 12px; color: var(--color-text-secondary); margin-top: 2px; }

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
  gap: 12px;
  margin-bottom: var(--spacing-xl);
}
.stats-row {
  grid-template-columns: repeat(4, 1fr);
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
  cursor: pointer;
}
.stat-card:hover {
  border-color: var(--color-border);
  box-shadow: 0 4px 12px rgba(0,0,0,.06);
  transform: translateY(-1px);
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

/* ── Recent docs (2-col grid) ── */
.recent-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
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
  display: flex; flex-direction: column;
  min-height: 110px;
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
  margin-right: 2px;
}
.recent-card-ext {
  font-size: 10px; font-weight: 700;
  color: #555;
}
.recent-card-meta {
  font-size: 11px;
  color: #6b7280;
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
@media (max-width: 1024px) {
  .stats-row { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 768px) {
  .home-page { padding: 0; }
  .welcome-text h1 { font-size: 20px; }
  .welcome-text p { font-size: 13px; }
  .hero-search { height: 46px; padding: 0 6px 0 12px; }
  .hero-search-hint { display: none; }
  .hero-search-btn { padding: 0 14px; font-size: 13px; }
  .admin-stats-row { grid-template-columns: repeat(2, 1fr); gap: 10px; }
  .admin-stat-card { padding: 14px 12px; gap: 10px; }
  .asc-icon { width: 38px; height: 38px; }
  .asc-num { font-size: 18px; }
}
</style>
