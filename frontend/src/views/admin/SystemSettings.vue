<template>
  <div class="admin-page">
    <el-tabs v-model="activeTab">
      <el-tab-pane label="基本设置" name="general">
        <el-form label-width="120px" style="max-width:600px">
          <el-form-item label="站点名称">
            <el-input v-model="config.site_name" />
          </el-form-item>
          <el-form-item label="站点描述">
            <el-input v-model="config.site_desc" type="textarea" :rows="2" />
          </el-form-item>
          <el-form-item label="主色调">
            <el-color-picker v-model="config.primary_color" show-alpha />
          </el-form-item>
          <el-form-item label="强调色">
            <el-color-picker v-model="config.accent_color" show-alpha />
          </el-form-item>
          <el-form-item label="页头 Slogan">
            <el-input v-model="config.slogan" placeholder="搜索框旁的标语" />
          </el-form-item>
          <el-form-item label="页脚信息">
            <el-input v-model="config.footer" type="textarea" :rows="3" />
          </el-form-item>
          <el-form-item label="Logo">
            <el-upload :auto-upload="false" :show-file-list="false" accept="image/*">
              <el-button size="small">上传 Logo</el-button>
            </el-upload>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="saveGeneral">保存设置</el-button>
          </el-form-item>
        </el-form>
      </el-tab-pane>

      <el-tab-pane label="文件与存储" name="storage">
        <el-form label-width="120px" style="max-width:600px">
          <el-form-item label="最大上传大小">
            <el-input-number v-model="config.max_upload_mb" :min="1" :max="2048" /> MB
          </el-form-item>
          <el-form-item label="MinIO 地址">
            <el-input v-model="config.minio_endpoint" placeholder="localhost:9000" />
          </el-form-item>
          <el-form-item label="存储桶">
            <el-input v-model="config.minio_bucket" placeholder="kb-documents" />
          </el-form-item>
          <el-form-item label="允许的文件类型">
            <el-checkbox-group v-model="config.allowed_exts">
              <el-checkbox v-for="ext in fileTypes" :key="ext" :label="ext" :value="ext">{{ ext }}</el-checkbox>
            </el-checkbox-group>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="saveStorage">保存设置</el-button>
          </el-form-item>
        </el-form>
      </el-tab-pane>

      <el-tab-pane label="数据库与索引" name="database">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="数据库">PostgreSQL 16</el-descriptions-item>
          <el-descriptions-item label="搜索引擎">Meilisearch</el-descriptions-item>
          <el-descriptions-item label="文档总数">{{ stats.total_docs }}</el-descriptions-item>
          <el-descriptions-item label="用户总数">{{ stats.total_users }}</el-descriptions-item>
          <el-descriptions-item label="总分类数">{{ stats.total_cats }}</el-descriptions-item>
          <el-descriptions-item label="后端版本">v0.1.0</el-descriptions-item>
        </el-descriptions>
        <div style="margin-top: var(--spacing-lg)">
          <el-button @click="rebuildIndex" :loading="rebuilding">重建搜索索引</el-button>
        </div>
      </el-tab-pane>

      <el-tab-pane label="更新公告" name="announcements">
        <div style="max-width:720px">
          <el-form label-width="90px">
            <el-form-item label="公告标题">
              <el-input v-model="annForm.title" placeholder="如：文件传输功能更新" maxlength="200" />
            </el-form-item>
            <el-form-item label="公告内容">
              <el-input v-model="annForm.content" type="textarea" :rows="5"
                placeholder="支持多行文字，登录后弹窗展示" maxlength="8000" show-word-limit />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :disabled="!annForm.title.trim() || !annForm.content.trim()" @click="publishAnnouncement">
                发布公告
              </el-button>
              <el-button @click="loadAnnouncements">刷新</el-button>
            </el-form-item>
          </el-form>
          <el-divider />
          <div v-if="annList.length === 0" style="color:#999;font-size:13px">暂无公告</div>
          <div v-for="a in annList" :key="a.id" class="ann-row">
            <div class="ann-row-info">
              <div style="font-weight:600">{{ a.title }}</div>
              <div style="color:#999;font-size:12px;margin-top:2px">{{ a.created_at ? new Date(a.created_at).toLocaleString('zh-CN', { hour12: false }) : '' }}</div>
              <div style="font-size:13px;color:#555;margin-top:4px;white-space:pre-wrap">{{ a.content }}</div>
            </div>
            <div class="ann-row-acts">
              <el-button size="small" :type="a.is_active ? 'warning' : 'success'" @click="toggleAnnouncement(a)">
                {{ a.is_active ? '停用' : '启用' }}
              </el-button>
              <el-button size="small" type="danger" @click="removeAnnouncement(a)">删除</el-button>
            </div>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue'
import { get, put, post, del } from '@/api/client'
import { ElMessage, ElMessageBox } from 'element-plus'

function hexToHsl(hex: string): [number, number, number] {
  let r = parseInt(hex.slice(1, 3), 16) / 255, g = parseInt(hex.slice(3, 5), 16) / 255, b = parseInt(hex.slice(5, 7), 16) / 255
  const max = Math.max(r, g, b), min = Math.min(r, g, b)
  let h = 0, s = 0, l = (max + min) / 2
  if (max !== min) {
    const d = max - min; s = l > 0.5 ? d / (2 - max - min) : d / (max + min)
    h = max === r ? ((g - b) / d + (g < b ? 6 : 0)) / 6 : max === g ? ((b - r) / d + 2) / 6 : ((r - g) / d + 4) / 6
  }
  return [Math.round(h * 360), Math.round(s * 100), Math.round(l * 100)]
}
function hslToHex(h: number, s: number, l: number): string {
  s /= 100; l /= 100; const a = s * Math.min(l, 1 - l)
  const f = (n: number) => { const k = (n + h / 30) % 12; return Math.round((l - a * Math.max(Math.min(k - 3, 9 - k, 1), -1)) * 255) }
  return '#' + [f(0), f(8), f(4)].map(v => v.toString(16).padStart(2, '0')).join('')
}
function lighten(h: string, a: number) { const [x,y,z] = hexToHsl(h); return hslToHex(x, y, Math.min(100, z + a)) }
function darken(h: string, a: number) { const [x,y,z] = hexToHsl(h); return hslToHex(x, y, Math.max(5, z - a)) }

function applyTheme(primary: string, accent: string) {
  const root = document.documentElement
  const items: [string, string][] = [
    ['--color-primary', primary],
    ['--color-primary-light', lighten(primary, 12)],
    ['--color-primary-dark', darken(primary, 18)],
    ['--color-accent', accent],
    ['--color-accent-light', lighten(accent, 15)],
    ['--el-color-primary', primary],
    ['--el-color-primary-light-3', lighten(primary, 12)],
    ['--el-color-primary-light-5', lighten(primary, 25)],
    ['--el-color-primary-light-7', lighten(primary, 38)],
    ['--el-color-primary-light-8', lighten(primary, 45)],
    ['--el-color-primary-light-9', lighten(primary, 52)],
    ['--el-color-primary-dark-2', darken(primary, 10)],
  ]
  for (const [key, val] of items) {
    root.style.setProperty(key, val)
  }
}

const activeTab = ref('general')
const rebuilding = ref(false)
const annList = ref<any[]>([])
const annForm = reactive({ title: '', content: '' })

const config = reactive({
  site_name: '企业知识库',
  site_desc: '医疗器械注册 · 临床评价 · 临床试验 · 法规库',
  primary_color: '#1e50ae',
  accent_color: '#ffc001',
  slogan: '专业法规知识管理平台',
  footer: '©2026 企业知识库团队 版权所有 | 400-000-0000',
  max_upload_mb: 500,
  minio_endpoint: 'localhost:9000',
  minio_bucket: 'kb-documents',
  allowed_exts: ['pdf','doc','docx','xls','xlsx','ppt','pptx','txt','md','jpg','png','gif','mp4','zip','rar'],
})

const stats = reactive({ total_docs: '-', total_users: '-', total_cats: '-' })
const fileTypes = ['pdf','doc','docx','xls','xlsx','ppt','pptx','txt','md','csv','jpg','jpeg','png','gif','tiff','bmp','mp4','avi','mov','mp3','wav','zip','rar','7z','dwg','epub','mobi']

async function loadAnnouncements() {
  try {
    const r: any = await get('/api/announcements', { include_inactive: 1 })
    annList.value = (r as any).items || []
  } catch { annList.value = [] }
}

async function publishAnnouncement() {
  try {
    await post('/api/announcements', {
      title: annForm.title.trim(),
      content: annForm.content.trim(),
      is_active: true,
    })
    ElMessage.success('公告已发布，用户下次登录/刷新会看到弹窗')
    annForm.title = ''
    annForm.content = ''
    await loadAnnouncements()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '发布失败')
  }
}

async function toggleAnnouncement(a: any) {
  try {
    await put(`/api/announcements/${a.id}`, {
      title: a.title, content: a.content, is_active: !a.is_active,
    })
    a.is_active = !a.is_active
    ElMessage.success(a.is_active ? '已启用' : '已停用')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '操作失败')
  }
}

async function removeAnnouncement(a: any) {
  try {
    await ElMessageBox.confirm(`删除公告「${a.title}」？`, '确认', { type: 'warning' })
    await del(`/api/announcements/${a.id}`)
    await loadAnnouncements()
    ElMessage.success('已删除')
  } catch { /* 取消或失败 */ }
}

async function saveGeneral() {
  try {
    await put('/api/admin/settings', {
      site_name: config.site_name,
      site_desc: config.site_desc,
      primary_color: config.primary_color,
      accent_color: config.accent_color,
      slogan: config.slogan,
      footer: config.footer,
    })
    ElMessage.success('设置已保存')
    applyTheme(config.primary_color, config.accent_color)
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '保存失败') }
}

async function saveStorage() {
  try {
    await put('/api/admin/settings', {
      max_upload_mb: String(config.max_upload_mb),
      minio_endpoint: config.minio_endpoint,
      minio_bucket: config.minio_bucket,
      allowed_exts: config.allowed_exts.join(','),
    })
    ElMessage.success('存储设置已保存（需重启后端生效）')
  } catch (e: any) { ElMessage.error(e?.response?.data?.detail || '保存失败') }
}

async function rebuildIndex() {
  rebuilding.value = true
  try {
    await get('/api/search/stats')  // trigger sync check
    ElMessage.success('索引重建已触发')
  } catch { ElMessage.error('重建失败') }
  rebuilding.value = false
}

onMounted(async () => {
  loadAnnouncements()
  try {
    const resp: any = await get('/api/admin/settings')
    if (resp && Object.keys(resp).length > 0) {
      if (resp.site_name) config.site_name = resp.site_name
      if (resp.site_desc) config.site_desc = resp.site_desc
      if (resp.primary_color) config.primary_color = resp.primary_color
      if (resp.accent_color) config.accent_color = resp.accent_color
      if (resp.primary_color) applyTheme(resp.primary_color, resp.accent_color || '#ffc001')
      if (resp.slogan) config.slogan = resp.slogan
      if (resp.footer) config.footer = resp.footer
      if (resp.max_upload_mb) config.max_upload_mb = Number(resp.max_upload_mb)
    }
    // Also load stats
    try {
      const dash: any = await get('/api/admin/dashboard')
      if (dash?.overview) {
        stats.total_docs = dash.overview.total_docs
        stats.total_users = dash.overview.total_users
        stats.total_cats = dash.overview.total_categories
      }
    } catch { /* non-admin */ }
    try {
      const health: any = await get('/api/health')
      if (health?.version) stats.total_cats = stats.total_cats || '-'
    } catch { /* ignore */ }
  } catch { /* non-admin users get 403, show defaults */ }
})
</script>

<style scoped>
.admin-page { background: #fff; border-radius: var(--radius-md); padding: var(--spacing-lg); }
.ann-row {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px dashed #e5e7eb;
}
.ann-row:last-child { border-bottom: none; }
.ann-row-info { flex: 1; min-width: 0; }
.ann-row-acts { flex-shrink: 0; display: flex; gap: 6px; }
</style>
