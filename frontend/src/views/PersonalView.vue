<template>
  <div class="personal-page">
    <h2>个人工作台</h2>
    <div class="stats-row">
      <el-statistic title="我的上传" :value="stats.total_uploads">
        <template #prefix><el-icon><Upload /></el-icon></template>
      </el-statistic>
      <el-statistic title="我的收藏" :value="stats.total_favorites">
        <template #prefix><el-icon><Star /></el-icon></template>
      </el-statistic>
      <el-statistic title="最近浏览" :value="stats.total_history">
        <template #prefix><el-icon><Clock /></el-icon></template>
      </el-statistic>
    </div>

    <el-tabs v-model="activeTab" @tab-change="handleTabChange">
      <el-tab-pane label="我的上传" name="uploads">
        <div class="item-list">
          <div v-for="d in uploads" :key="d.id" class="item-row" @click="$router.push(`/document/${d.id}`)">
            <h4>{{ d.title }}</h4>
            <p class="item-meta">
              {{ formatDate(d.created_at) }} · {{ d.view_count }} 次浏览 · {{ d.file_ext?.toUpperCase() || '链接' }}
            </p>
            <p class="item-summary" v-if="d.summary">{{ d.summary?.substring(0, 100) }}</p>
          </div>
          <el-empty v-if="!loading.uploads && !uploads.length" description="暂无上传的文档" />
        </div>
      </el-tab-pane>

      <el-tab-pane label="我的收藏" name="favorites">
        <div class="item-list">
          <div v-for="d in favorites" :key="d.id" class="item-row" @click="$router.push(`/document/${d.id}`)">
            <h4>{{ d.title }}</h4>
            <p class="item-meta">
              {{ d.uploader_name }} · {{ formatDate(d.updated_at) }}
            </p>
            <p class="item-summary" v-if="d.summary">{{ d.summary?.substring(0, 100) }}</p>
          </div>
          <el-empty v-if="!loading.favorites && !favorites.length" description="暂无收藏的文档" />
        </div>
      </el-tab-pane>

      <el-tab-pane label="最近浏览" name="history">
        <div class="item-list">
          <div v-for="d in history" :key="d.id" class="item-row" @click="$router.push(`/document/${d.id}`)">
            <h4>{{ d.title }}</h4>
            <p class="item-meta">
              {{ d.uploader_name }} · {{ formatDate(d.created_at) }} · {{ d.view_count }} 次浏览
            </p>
          </div>
          <el-empty v-if="!loading.history && !history.length" description="暂无浏览记录" />
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue'
import { Upload, Star, Clock } from '@element-plus/icons-vue'
import { get } from '@/api/client'
import dayjs from 'dayjs'

const activeTab = ref('uploads')
const stats = ref({ total_uploads: 0, total_favorites: 0, total_history: 0 })
const uploads = ref<any[]>([])
const favorites = ref<any[]>([])
const history = ref<any[]>([])
const loading = reactive({ uploads: false, favorites: false, history: false })

function formatDate(d: string) { return dayjs(d).format('YYYY-MM-DD HH:mm') }

async function loadUploads() {
  loading.uploads = true
  try {
    const resp: any = await get('/api/me/uploads')
    uploads.value = resp.items || []
  } catch { uploads.value = [] }
  loading.uploads = false
}

async function loadFavorites() {
  loading.favorites = true
  try {
    const resp: any = await get('/api/me/favorites')
    favorites.value = resp.items || []
  } catch { favorites.value = [] }
  loading.favorites = false
}

async function loadHistory() {
  loading.history = true
  try {
    const resp: any = await get('/api/me/history')
    history.value = resp.items || []
  } catch { history.value = [] }
  loading.history = false
}

function handleTabChange(tab: string | number) {
  if (tab === 'uploads') loadUploads()
  else if (tab === 'favorites') loadFavorites()
  else if (tab === 'history') loadHistory()
}

onMounted(async () => {
  try { stats.value = await get('/api/me/stats') } catch {}
  loadUploads()
})
</script>

<style scoped>
.personal-page { padding: var(--spacing-md) 0; }
.personal-page h2 { margin-bottom: var(--spacing-lg); font-size: 20px; }
.stats-row { display: flex; gap: var(--spacing-2xl); margin-bottom: var(--spacing-xl); }

.item-list { display: flex; flex-direction: column; gap: 1px; background: var(--color-border); border-radius: var(--radius-md); overflow: hidden; }
.item-row { padding: var(--spacing-md); background: #fff; cursor: pointer; }
.item-row:hover { background: #fafbfc; }
.item-row h4 { font-size: 14px; margin-bottom: 4px; }
.item-meta { font-size: 12px; color: var(--color-text-secondary); }
.item-summary { font-size: 12px; color: var(--color-text-secondary); margin-top: 4px; }
</style>
