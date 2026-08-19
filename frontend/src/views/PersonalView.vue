<template>
  <div class="personal-page">
    <!-- 用户概览卡 -->
    <div class="user-card">
      <div class="user-avatar">{{ initials }}</div>
      <div class="user-info">
        <div class="user-name">{{ user?.display_name || user?.username || '未登录' }}</div>
        <div class="user-meta">
          {{ user?.department || '未分配部门' }} · {{ roleLabel }}
          <span v-if="user?.employee_id"> · 工号 {{ user?.employee_id }}</span>
        </div>
      </div>
      <div class="user-actions">
        <el-button size="small" :icon="Lock" @click="pwdVisible = true">修改密码</el-button>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="personal-stats">
      <div class="pstat-card" @click="switchTab('uploads')">
        <div class="pstat-icon up"><el-icon :size="24"><Upload /></el-icon></div>
        <div class="pstat-info">
          <span class="pstat-num">{{ stats.total_uploads }}</span>
          <span class="pstat-label">我的上传</span>
        </div>
        <el-icon class="pstat-arrow"><ArrowRight /></el-icon>
      </div>
      <div class="pstat-card" @click="switchTab('favorites')">
        <div class="pstat-icon fav"><el-icon :size="24"><Star /></el-icon></div>
        <div class="pstat-info">
          <span class="pstat-num">{{ stats.total_favorites }}</span>
          <span class="pstat-label">我的收藏</span>
        </div>
        <el-icon class="pstat-arrow"><ArrowRight /></el-icon>
      </div>
      <div class="pstat-card" @click="switchTab('history')">
        <div class="pstat-icon his"><el-icon :size="24"><Clock /></el-icon></div>
        <div class="pstat-info">
          <span class="pstat-num">{{ stats.total_history }}</span>
          <span class="pstat-label">最近浏览</span>
        </div>
        <el-icon class="pstat-arrow"><ArrowRight /></el-icon>
      </div>
    </div>

    <el-tabs v-model="activeTab" @tab-change="handleTabChange">
      <!-- Uploads -->
      <el-tab-pane label="我的上传" name="uploads">
        <div v-loading="loading.uploads">
        <div v-if="!loading.uploads && !uploads.length" class="empty-state">
          <div class="empty-icon"><el-icon :size="34"><Upload /></el-icon></div>
          <h3>暂无上传的文档</h3>
          <p>您还没有上传过任何文档</p>
          <el-button type="primary" @click="$router.push('/files')">去团队公盘上传</el-button>
        </div>
        <div v-else class="doc-cards">
          <div v-for="d in uploads" :key="d.id" class="doc-card" @click="$router.push(`/document/${d.id}`)">
            <div class="doc-card-icon" :style="{background: extBg(d.file_ext)}">
              <span class="doc-card-ext">{{ d.file_ext?.toUpperCase()?.substring(0,3) || 'LNK' }}</span>
            </div>
            <div class="doc-card-body">
              <h4>{{ d.title }}</h4>
              <p class="doc-card-meta">{{ formatDate(d.created_at) }} · {{ d.view_count }} 次浏览</p>
              <p class="doc-card-summary" v-if="d.summary">{{ d.summary?.substring(0, 100) }}</p>
            </div>
            <div class="doc-card-actions" @click.stop>
              <el-button size="small" @click="$router.push(`/document/${d.id}`)">查看</el-button>
            </div>
          </div>
        </div>
        </div>
      </el-tab-pane>

      <!-- Favorites -->
      <el-tab-pane label="我的收藏" name="favorites">
        <div v-loading="loading.favorites">
        <div v-if="!loading.favorites && !favorites.length" class="empty-state">
          <div class="empty-icon"><el-icon :size="34"><Star /></el-icon></div>
          <h3>暂无收藏的文档</h3>
          <p>浏览文档时点击收藏即可添加到此处</p>
          <el-button type="primary" @click="$router.push('/')">去首页发现文档</el-button>
        </div>
        <div v-else class="doc-cards">
          <div v-for="d in favorites" :key="d.id" class="doc-card" @click="$router.push(`/document/${d.id}`)">
            <div class="doc-card-icon" :style="{background: extBg(d.file_ext)}">
              <span class="doc-card-ext">{{ d.file_ext?.toUpperCase()?.substring(0,3) || 'LNK' }}</span>
            </div>
            <div class="doc-card-body">
              <h4>{{ d.title }}</h4>
              <p class="doc-card-meta">{{ d.uploader_name }} · {{ formatDate(d.updated_at) }}</p>
              <p class="doc-card-summary" v-if="d.summary">{{ d.summary?.substring(0, 100) }}</p>
            </div>
            <div class="doc-card-actions" @click.stop>
              <el-button size="small" type="warning" @click="unfavorite(d)">取消收藏</el-button>
            </div>
          </div>
        </div>
        </div>
      </el-tab-pane>

      <!-- History -->
      <el-tab-pane label="最近浏览" name="history">
        <div v-loading="loading.history">
        <div v-if="!loading.history && !history.length" class="empty-state">
          <div class="empty-icon"><el-icon :size="34"><Clock /></el-icon></div>
          <h3>暂无浏览记录</h3>
          <p>您浏览过的文档会记录在这里</p>
          <el-button @click="$router.push('/')">去首页浏览文档</el-button>
        </div>
        <template v-else>
          <div style="margin-bottom:12px;text-align:right" v-if="history.length">
            <el-button size="small" type="danger" plain @click="clearHistory">清空全部记录</el-button>
          </div>
          <div class="doc-cards">
            <div v-for="d in history" :key="d.id" class="doc-card" @click="$router.push(`/document/${d.id}`)">
              <div class="doc-card-icon" :style="{background: extBg(d.file_ext)}">
                <span class="doc-card-ext">{{ d.file_ext?.toUpperCase()?.substring(0,3) || 'LNK' }}</span>
              </div>
              <div class="doc-card-body">
                <h4>{{ d.title }}</h4>
                <p class="doc-card-meta">{{ d.uploader_name }} · {{ formatDate(d.created_at) }}</p>
              </div>
            </div>
          </div>
        </template>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- 修改密码 -->
    <el-dialog v-model="pwdVisible" title="修改密码" width="400px">
      <el-form label-width="80px">
        <el-form-item label="原密码">
          <el-input v-model="pwdForm.old_password" type="password" show-password placeholder="请输入当前密码" />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input v-model="pwdForm.new_password" type="password" show-password placeholder="至少8位，含字母和数字" />
        </el-form-item>
        <el-form-item label="确认新密码">
          <el-input v-model="pwdForm.confirm" type="password" show-password placeholder="再次输入新密码" @keyup.enter="submitPassword" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="pwdVisible = false">取消</el-button>
        <el-button type="primary" @click="submitPassword">确认修改</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive, computed } from 'vue'
import { useRoute } from 'vue-router'
import { Upload, Star, Clock, Lock, ArrowRight } from '@element-plus/icons-vue'
import { get, del, post } from '@/api/client'
import { ElMessage, ElMessageBox } from 'element-plus'
import dayjs from 'dayjs'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const auth = useAuthStore()
const user = computed(() => auth.user)
const initials = computed(() => {
  const name = user.value?.display_name || user.value?.username || '?'
  return name.charAt(0).toUpperCase()
})
const roleLabel = computed(() => {
  const map: Record<string, string> = {
    super_admin: '超级管理员', dept_admin: '部门管理员',
    editor: '编辑者', employee: '员工', guest: '访客',
  }
  return map[user.value?.role || ''] || user.value?.role || ''
})
const activeTab = ref('uploads')
const stats = ref({ total_uploads: 0, total_favorites: 0, total_history: 0 })
const uploads = ref<any[]>([])
const favorites = ref<any[]>([])
const history = ref<any[]>([])
const loading = reactive({ uploads: false, favorites: false, history: false })
const pwdVisible = ref(false)
const pwdForm = reactive({ old_password: '', new_password: '', confirm: '' })

async function submitPassword() {
  if (!pwdForm.old_password || !pwdForm.new_password) { ElMessage.warning('请填写完整'); return }
  if (pwdForm.new_password !== pwdForm.confirm) { ElMessage.warning('两次输入的新密码不一致'); return }
  try {
    await post('/api/auth/change-password', { old_password: pwdForm.old_password, new_password: pwdForm.new_password })
    ElMessage.success('密码已修改，下次登录请使用新密码')
    pwdVisible.value = false
    pwdForm.old_password = ''; pwdForm.new_password = ''; pwdForm.confirm = ''
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '修改失败')
  }
}

const extBgMap: Record<string,string> = {
  pdf:'#ef4444',doc:'#3b82f6',docx:'#3b82f6',xls:'#16a34a',xlsx:'#16a34a',ppt:'#f97316',pptx:'#f97316',link:'#0891b2'
}
function extBg(ext: string) { return extBgMap[ext?.toLowerCase()] || '#6b7280' }
function formatDate(d: string) { return dayjs(d).format('YYYY-MM-DD HH:mm') }

async function loadUploads() {
  loading.uploads = true
  try { const r: any = await get('/api/me/uploads'); uploads.value = r.items || [] } catch { uploads.value = [] }
  loading.uploads = false
}
async function loadFavorites() {
  loading.favorites = true
  try { const r: any = await get('/api/me/favorites'); favorites.value = r.items || [] } catch { favorites.value = [] }
  loading.favorites = false
}
async function loadHistory() {
  loading.history = true
  try { const r: any = await get('/api/me/history'); history.value = r.items || [] } catch { history.value = [] }
  loading.history = false
}
function handleTabChange(tab: string | number) {
  if (tab === 'uploads') loadUploads()
  else if (tab === 'favorites') loadFavorites()
  else if (tab === 'history') loadHistory()
}
function switchTab(tab: 'uploads' | 'favorites' | 'history') {
  activeTab.value = tab
  handleTabChange(tab)
}
async function unfavorite(d: any) {
  try {
    await del(`/api/me/favorites/${d.id}`)
    ElMessage.success('已取消收藏')
    loadFavorites()
  } catch { ElMessage.error('操作失败') }
}
async function clearHistory() {
  try {
    await ElMessageBox.confirm('确定清空全部浏览记录？', '确认', { type: 'warning' })
    await del('/api/me/history')
    ElMessage.success('已清空')
    loadHistory()
  } catch { /* cancelled */ }
}
onMounted(async () => {
  try { stats.value = await get('/api/me/stats') } catch {}
  const tab = route.query.tab as string
  if (tab === 'favorites') { activeTab.value = 'favorites'; loadFavorites() }
  else if (tab === 'history') { activeTab.value = 'history'; loadHistory() }
  else { loadUploads() }
})
</script>

<style scoped>
.personal-page { padding: var(--spacing-md) 0; }

/* 用户概览卡 */
.user-card {
  display: flex; align-items: center; gap: 16px;
  background: linear-gradient(135deg, #ffffff 0%, #f7faff 100%);
  border: 1px solid #e7ecf5; border-radius: 14px;
  padding: 20px 24px; margin-bottom: 20px;
  box-shadow: 0 2px 10px rgba(30, 80, 174, .05);
}
.user-avatar {
  width: 56px; height: 56px; border-radius: 14px; flex-shrink: 0;
  background: linear-gradient(135deg, #2b6de8 0%, #1e50ae 100%);
  color: #fff; font-size: 24px; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 4px 12px rgba(30, 80, 174, .25);
}
.user-info { flex: 1; min-width: 0; }
.user-name { font-size: 18px; font-weight: 700; color: #1f2937; line-height: 1.3; }
.user-meta { font-size: 12px; color: #6b7280; margin-top: 4px; }
.user-actions { flex-shrink: 0; }

/* 统计卡片 */
.personal-stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 24px; }
.pstat-card {
  display: flex; align-items: center; gap: 14px;
  background: #fff; border: 1px solid #eef1f6; border-radius: 14px;
  padding: 18px 20px; cursor: pointer;
  box-shadow: 0 1px 4px rgba(15, 23, 42, .04);
  transition: transform .15s ease, box-shadow .15s ease, border-color .15s ease;
}
.pstat-card:hover { transform: translateY(-2px); box-shadow: 0 8px 20px rgba(30, 80, 174, .10); border-color: #d6e1f8; }
.pstat-icon { width: 48px; height: 48px; border-radius: 12px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; color: #fff; }
.pstat-icon.up { background: linear-gradient(135deg, #4c8dff, #1e50ae); box-shadow: 0 4px 10px rgba(30,80,174,.22); }
.pstat-icon.fav { background: linear-gradient(135deg, #ffb45c, #f28b1e); box-shadow: 0 4px 10px rgba(242,139,30,.22); }
.pstat-icon.his { background: linear-gradient(135deg, #46c98b, #1d9e68); box-shadow: 0 4px 10px rgba(29,158,104,.22); }
.pstat-info { flex: 1; display: flex; flex-direction: column; }
.pstat-num { font-size: 28px; font-weight: 700; color: #111827; line-height: 1.1; letter-spacing: -.5px; }
.pstat-label { font-size: 13px; color: #6b7280; margin-top: 4px; }
.pstat-arrow { color: #c3cad6; font-size: 14px; transition: transform .15s ease, color .15s ease; }
.pstat-card:hover .pstat-arrow { transform: translateX(3px); color: #1e50ae; }

.doc-cards { display: flex; flex-direction: column; gap: 10px; }
.doc-card {
  display: flex; align-items: center; gap: 14px; background: #fff; border-radius: 12px;
  padding: 14px 18px; cursor: pointer; border: 1px solid transparent;
  box-shadow: 0 1px 3px rgba(0,0,0,.04); transition: all .2s;
}
.doc-card:hover { border-color: var(--color-border); box-shadow: 0 4px 12px rgba(0,0,0,.06); }
.doc-card:hover h4 { color: var(--color-primary); }
.doc-card-icon { width: 40px; height: 40px; border-radius: 8px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.doc-card-ext { font-size: 10px; font-weight: 700; color: #fff; }
.doc-card-body { flex: 1; min-width: 0; }
.doc-card-body h4 { font-size: 13px; font-weight: 600; margin: 0 0 3px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; transition: color .15s; word-break: break-all; max-width: 100%; }
.doc-card-meta { font-size: 11px; color: #6b7280; margin: 0; }
.doc-card-summary { font-size: 11px; color: var(--color-text-secondary); margin: 4px 0 0; display: -webkit-box; -webkit-line-clamp: 1; -webkit-box-orient: vertical; overflow: hidden; }
.doc-card-actions { flex-shrink: 0; }

.empty-state { text-align: center; padding: 48px 20px; color: var(--color-text-secondary); }
.empty-icon {
  width: 64px; height: 64px; margin: 0 auto; border-radius: 50%;
  background: #f0f4fb; color: #9db4dc;
  display: flex; align-items: center; justify-content: center;
}
.empty-state h3 { font-size: 15px; margin: 12px 0 4px; color: var(--color-text-primary); }
.empty-state p { font-size: 13px; margin-bottom: 16px; }

@media (max-width: 768px) {
  .personal-stats { grid-template-columns: 1fr; }
  .doc-card-actions { display: none; }
}
</style>
