<template>
  <div class="ops-tasks">
    <div class="ops-header">
      <div>
        <h2>数据更新</h2>
        <p class="ops-sub">服务器任务直接执行；CMDE / NMPA 任务由维护机代理自动执行（需「更新代理.bat」在线）。</p>
      </div>
      <div class="ops-actions">
        <el-button v-for="t in taskTypes" :key="t.type" size="small" :type="t.type === 'cmde' || t.type === 'nmpa' ? 'warning' : 'primary'"
          :loading="creating === t.type" @click="createTask(t.type)">
          {{ t.label }}
        </el-button>
      </div>
    </div>

    <el-table :data="tasks" v-loading="loading" stripe size="small" style="width:100%">
      <el-table-column type="expand">
        <template #default="{ row }">
          <pre class="ops-log">{{ row.log || '（暂无日志）' }}</pre>
        </template>
      </el-table-column>
      <el-table-column prop="label" label="任务" width="150" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)" size="small">{{ statusText(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_by" label="创建人" width="100" />
      <el-table-column label="创建时间" width="160">
        <template #default="{ row }">{{ fmtTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="耗时" width="90">
        <template #default="{ row }">{{ duration(row) }}</template>
      </el-table-column>
      <el-table-column prop="agent" label="执行端" width="110" />
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import { get, post } from '@/api/client'

const tasks = ref<any[]>([])
const loading = ref(false)
const creating = ref('')

const taskTypes = [
  { type: 'all', label: '自动更新全流程' },
  { type: 'qa', label: '省级 Q&A' },
  { type: 'nifdc', label: 'NIFDC 增量' },
  { type: 'cmde', label: 'CMDE 更新' },
  { type: 'nmpa', label: 'NMPA 补采' },
]

function statusType(s: string) {
  return s === 'success' ? 'success' : s === 'failed' ? 'danger' : s === 'running' ? 'warning' : 'info'
}
function statusText(s: string) {
  return s === 'success' ? '成功' : s === 'failed' ? '失败' : s === 'running' ? '执行中' : '等待执行'
}
function fmtTime(t: string) {
  return t ? t.replace('T', ' ').slice(0, 19) : '-'
}
function duration(row: any) {
  if (!row.started_at) return '-'
  const end = row.finished_at ? new Date(row.finished_at).getTime() : Date.now()
  return Math.max(0, Math.round((end - new Date(row.started_at).getTime()) / 1000)) + 's'
}
async function refresh() {
  try {
    loading.value = true
    const d: any = await get('/api/admin/ops/tasks', { limit: 50 })
    tasks.value = d.items || []
  } catch { /* ignore */ } finally { loading.value = false }
}

async function createTask(type: string) {
  creating.value = type
  try {
    await post('/api/admin/ops/tasks', { task_type: type })
    ElMessage.success('任务已创建')
    refresh()
  } catch (e: any) {
    ElMessage.error(e?.detail || '创建失败')
  } finally { creating.value = '' }
}

let timer: any = null
onMounted(() => {
  refresh()
  timer = setInterval(refresh, 3000)
})
onBeforeUnmount(() => clearInterval(timer))
</script>

<style scoped>
.ops-tasks { padding: 4px; }
.ops-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; margin-bottom: 14px; flex-wrap: wrap; }
.ops-header h2 { margin: 0 0 6px; font-size: 18px; }
.ops-sub { margin: 0; font-size: 12px; color: #8a94a6; }
.ops-actions { display: flex; gap: 8px; flex-wrap: wrap; }
.ops-log {
  margin: 0; padding: 10px 14px; max-height: 320px; overflow: auto;
  background: #0f172a; color: #d1e0ff; font-size: 12px; line-height: 1.6;
  border-radius: 8px; white-space: pre-wrap; word-break: break-all;
}
</style>
