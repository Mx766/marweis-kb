<template>
  <div class="activity-page">
    <div class="act-head">
      <h2>访问与热度</h2>
      <p class="act-sub">活跃用户、访问流水、热门文档排行（部门管理员仅能看本部门）。</p>
    </div>

    <el-tabs v-model="tab" class="act-tabs">
      <el-tab-pane label="访问记录" name="records">
        <el-card shadow="never" class="act-card">
          <div class="act-toolbar">
            <el-input v-model="userQ" placeholder="搜索用户姓名/账号" clearable style="width: 240px"
              @keyup.enter="loadUsers" @clear="loadUsers" />
            <el-button type="primary" @click="loadUsers">查询</el-button>
          </div>
          <el-table :data="users" v-loading="usersLoading" stripe>
            <el-table-column prop="display_name" label="姓名" min-width="120" />
            <el-table-column prop="username" label="账号" min-width="160" show-overflow-tooltip />
            <el-table-column prop="department" label="部门" width="130" />
            <el-table-column label="角色" width="120">
              <template #default="{ row }">
                <el-tag size="small" :type="roleType(row.role)">{{ roleName(row.role) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="views" label="浏览次数" width="100" align="center" sortable />
            <el-table-column label="最近访问" width="170">
              <template #default="{ row }">{{ formatDate(row.last_active) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="120" fixed="right">
              <template #default="{ row }">
                <el-button size="small" type="primary" link @click="openUser(row)">查看记录</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <el-card shadow="never" class="act-card">
          <template #header>最近访问流水</template>
          <el-table :data="records" v-loading="recordsLoading" stripe size="small">
            <el-table-column prop="user_name" label="用户" width="140" show-overflow-tooltip />
            <el-table-column prop="department" label="部门" width="120" />
            <el-table-column prop="doc_title" label="文档" min-width="280" show-overflow-tooltip />
            <el-table-column prop="category" label="分类" width="140" show-overflow-tooltip>
              <template #default="{ row }">{{ row.category || '-' }}</template>
            </el-table-column>
            <el-table-column label="访问时间" width="170">
              <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
            </el-table-column>
          </el-table>
          <div class="act-pager">
            <el-pagination background layout="total, prev, pager, next" :total="recordsTotal"
              :page-size="recordsSize" :current-page="recordsPage" @current-change="loadRecords" />
          </div>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="热门浏览" name="views">
        <el-card shadow="never" class="act-card">
          <el-table :data="hotViews" v-loading="hotLoading" stripe>
            <el-table-column type="index" label="#" width="55" align="center" />
            <el-table-column prop="title" label="文档" min-width="320" show-overflow-tooltip />
            <el-table-column prop="category" label="分类" width="150" show-overflow-tooltip>
              <template #default="{ row }">{{ row.category || '-' }}</template>
            </el-table-column>
            <el-table-column prop="file_ext" label="格式" width="80" align="center" />
            <el-table-column prop="count" label="浏览量" width="100" align="center" sortable />
          </el-table>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="热门下载" name="downloads">
        <el-card shadow="never" class="act-card">
          <el-table :data="hotDownloads" v-loading="hotLoading" stripe>
            <el-table-column type="index" label="#" width="55" align="center" />
            <el-table-column prop="title" label="文档" min-width="320" show-overflow-tooltip />
            <el-table-column prop="category" label="分类" width="150" show-overflow-tooltip>
              <template #default="{ row }">{{ row.category || '-' }}</template>
            </el-table-column>
            <el-table-column prop="file_ext" label="格式" width="80" align="center" />
            <el-table-column prop="count" label="下载量" width="100" align="center" sortable />
          </el-table>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="操作日志" name="logs">
        <el-card shadow="never" class="act-card">
          <div class="act-toolbar">
            <el-input v-model="logQ" placeholder="搜索文件/用户" clearable style="width: 240px"
              @keyup.enter="loadLogs(1)" @clear="loadLogs(1)" />
          </div>
          <el-table :data="logs" v-loading="logsLoading" stripe size="small">
            <el-table-column prop="user_name" label="用户" width="140" show-overflow-tooltip />
            <el-table-column prop="department" label="部门" width="120" />
            <el-table-column label="动作" width="130">
              <template #default="{ row }">
                <el-tag size="small" :type="actionType(row.action)">{{ actionName(row.action) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="filename" label="文件" min-width="220" show-overflow-tooltip />
            <el-table-column prop="detail" label="详情" min-width="180" show-overflow-tooltip />
            <el-table-column label="时间" width="170">
              <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
            </el-table-column>
          </el-table>
          <div class="act-pager">
            <el-pagination background layout="total, prev, pager, next" :total="logsTotal"
              :page-size="logsSize" :current-page="logsPage" @current-change="loadLogs" />
          </div>
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="userDialog.open" :title="userDialog.title" width="76%" top="4vh">
      <el-table :data="userRecords" v-loading="userRecordsLoading" stripe size="small">
        <el-table-column prop="doc_title" label="文档" min-width="320" show-overflow-tooltip />
        <el-table-column prop="category" label="分类" width="150" show-overflow-tooltip>
          <template #default="{ row }">{{ row.category || '-' }}</template>
        </el-table-column>
        <el-table-column label="访问时间" width="170">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
      </el-table>
      <div class="act-pager">
        <el-pagination background layout="total, prev, pager, next" :total="userRecordsTotal"
          :page-size="userRecordsSize" :current-page="userRecordsPage" @current-change="loadUserRecords" />
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { get } from '@/api/client'

const route = useRoute()
const tab = ref('records')
const users = ref<any[]>([])
const usersLoading = ref(false)
const userQ = ref('')

const records = ref<any[]>([])
const recordsLoading = ref(false)
const recordsPage = ref(1)
const recordsSize = ref(50)
const recordsTotal = ref(0)

const hotViews = ref<any[]>([])
const hotDownloads = ref<any[]>([])
const hotLoading = ref(false)

const userDialog = ref({ open: false, title: '', userId: '' })
const userRecords = ref<any[]>([])
const userRecordsLoading = ref(false)
const userRecordsPage = ref(1)
const userRecordsSize = ref(20)
const userRecordsTotal = ref(0)
const logs = ref<any[]>([])
const logsLoading = ref(false)
const logsPage = ref(1)
const logsSize = ref(50)
const logsTotal = ref(0)
const logQ = ref('')

const ROLE_TYPES = { super_admin: 'danger', dept_admin: 'warning', editor: 'primary', employee: 'info', guest: 'info' } as const
function roleType(r: string): 'danger' | 'warning' | 'primary' | 'info' {
  return ROLE_TYPES[r as keyof typeof ROLE_TYPES] || 'info'
}
function roleName(r: string) {
  return { super_admin: '超管', dept_admin: '部门管理员', editor: '编辑者', employee: '员工', guest: '访客' }[r] || r
}
function formatDate(d: string) {
  return d ? d.replace('T', ' ').slice(0, 19) : '-'
}

async function loadUsers() {
  usersLoading.value = true
  try {
    const resp: any = await get('/api/admin/activity/users', { q: userQ.value || undefined })
    users.value = resp.items || []
  } finally {
    usersLoading.value = false
  }
}

async function loadRecords(page = 1) {
  recordsLoading.value = true
  recordsPage.value = page
  try {
    const resp: any = await get('/api/admin/activity/records', { page, size: recordsSize.value })
    records.value = resp.items || []
    recordsTotal.value = resp.total || 0
  } finally {
    recordsLoading.value = false
  }
}

async function loadHot() {
  hotLoading.value = true
  try {
    const [v, d] = await Promise.all([
      get('/api/admin/activity/hot', { sort: 'views', limit: 20 }),
      get('/api/admin/activity/hot', { sort: 'downloads', limit: 20 }),
    ])
    hotViews.value = (v as any).items || []
    hotDownloads.value = (d as any).items || []
  } finally {
    hotLoading.value = false
  }
}

function openUser(row: any) {
  userDialog.value = { open: true, title: `${row.display_name} 的访问记录`, userId: row.id }
  userRecordsPage.value = 1
  loadUserRecords(1)
}

async function loadUserRecords(page = 1) {
  if (!userDialog.value.userId) return
  userRecordsLoading.value = true
  userRecordsPage.value = page
  try {
    const resp: any = await get(`/api/admin/activity/users/${userDialog.value.userId}/records`, {
      page, size: userRecordsSize.value,
    })
    userRecords.value = resp.items || []
    userRecordsTotal.value = resp.total || 0
  } finally {
    userRecordsLoading.value = false
  }
}

const ACTION_NAMES: Record<string, string> = {
  upload: '上传', upload_overwrite: '覆盖上传', create_folder: '新建文件夹', rename: '重命名',
  move: '移动', delete: '删除', batch_trash: '批量删除', batch_restore: '恢复',
  permanent_delete: '彻底删除', empty_trash: '清空回收站',
}
function actionName(a: string) { return ACTION_NAMES[a] || a }
function actionType(a: string): 'danger' | 'warning' | 'success' | 'info' {
  if (['delete', 'batch_trash', 'permanent_delete', 'empty_trash'].includes(a)) return 'danger'
  if (a === 'upload' || a === 'upload_overwrite' || a === 'create_folder') return 'success'
  if (a === 'rename' || a === 'move') return 'warning'
  return 'info'
}

async function loadLogs(page = 1) {
  logsLoading.value = true
  logsPage.value = page
  try {
    const resp: any = await get('/api/admin/activity/logs', { page, size: logsSize.value, q: logQ.value || undefined })
    logs.value = resp.items || []
    logsTotal.value = resp.total || 0
  } finally {
    logsLoading.value = false
  }
}

const qTab = String(route.query.tab || 'records')
tab.value = ['records', 'views', 'downloads', 'logs'].includes(qTab) ? qTab : 'records'
watch(tab, (t) => {
  if (t === 'views' || t === 'downloads') loadHot()
  if (t === 'logs') loadLogs()
})

loadUsers()
loadRecords()
loadHot()
</script>

<style scoped>
.act-head { margin-bottom: 14px; }
.act-head h2 { font-size: 18px; margin: 0 0 6px; }
.act-sub { font-size: 12px; color: #888; margin: 0; }
.act-tabs { background: #fff; border-radius: 10px; padding: 4px 16px 16px; }
.act-card { border-radius: 10px; margin-top: 14px; }
.act-toolbar { display: flex; gap: 10px; margin-bottom: 12px; }
.act-pager { display: flex; justify-content: flex-end; padding-top: 12px; }
</style>
