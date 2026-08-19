<template>
  <div class="ai-knowledge">
    <div class="ai-head">
      <div>
        <h2>AI 知识库</h2>
        <p class="ai-sub">系统为每篇知识库文档生成一份 Markdown 副本，供 AI 系统调用；普通用户界面不会显示这些内容。</p>
      </div>
    </div>

    <div class="ai-tabs">
      <button :class="{ active: tab === 'docs' }" @click="tab = 'docs'">文档列表</button>
      <button :class="{ active: tab === 'keys' }" @click="tab = 'keys'; loadKeys()">密钥管理</button>
    </div>

    <div v-if="tab === 'docs'">
    <div class="ai-filters">
      <el-select v-model="filters.status" style="width: 150px" @change="load(1)">
        <el-option label="全部状态" value="any" />
        <el-option label="已完成" value="done" />
        <el-option label="待处理" value="pending" />
        <el-option label="转换失败" value="failed" />
        <el-option label="不支持" value="unsupported" />
      </el-select>
      <el-input v-model="filters.q" placeholder="搜索文档标题" clearable style="width: 240px"
        @keyup.enter="load(1)" @clear="load(1)" />
      <el-button type="primary" :icon="Search" @click="load(1)">查询</el-button>
      <el-button :icon="Refresh" @click="refreshAll">刷新状态</el-button>
    </div>

    <el-card shadow="never" class="ai-card">
      <el-table :data="items" v-loading="loading" stripe>
        <el-table-column prop="title" label="文档标题" min-width="260" show-overflow-tooltip />
        <el-table-column prop="category_name" label="分类" width="160" show-overflow-tooltip>
          <template #default="{ row }">{{ row.category_name || '-' }}</template>
        </el-table-column>
        <el-table-column prop="file_ext" label="格式" width="80">
          <template #default="{ row }">{{ (row.file_ext || 'link').toUpperCase() }}</template>
        </el-table-column>
        <el-table-column label="MD 状态" width="110">
          <template #default="{ row }">
            <el-tag :type="statusType(row.markdown_status)" size="small">
              {{ statusLabel(row.markdown_status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="MD 长度" width="100">
          <template #default="{ row }">
            {{ row.markdown_content ? formatSize(row.markdown_content.length) : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="更新时间" width="150">
          <template #default="{ row }">{{ formatDate(row.updated_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" link :disabled="row.markdown_status !== 'done'"
              @click="viewMarkdown(row)">查看</el-button>
            <el-button size="small" link :disabled="row.markdown_status !== 'done'"
              @click="copyMarkdown(row)">复制</el-button>
            <el-button size="small" link type="warning" @click="regenerate(row)">重新生成</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="ai-pager">
        <el-pagination background layout="total, prev, pager, next" :total="total"
          :page-size="filters.size" :current-page="filters.page" @current-change="load" />
      </div>
    </el-card>

    <el-dialog v-model="viewer.open" :title="viewer.title" width="72%" top="4vh">
      <div class="md-viewer">
        <div class="md-render" v-if="viewer.content" v-html="renderMarkdown(viewer.content)"></div>
        <div v-else class="md-empty">（暂无 Markdown 内容）</div>
      </div>
      <template #footer>
        <el-button @click="viewer.open = false">关闭</el-button>
        <el-button type="primary" @click="copyViewer">复制内容</el-button>
        <el-button type="success" @click="downloadMd">下载 .md</el-button>
      </template>
    </el-dialog>
    </div>

    <div v-else class="keys-panel">
      <div class="keys-head">
        <p class="ai-sub">每个数字员工/机器人一个密钥，可限定部门范围；密钥明文只在创建时显示一次。</p>
        <el-button type="primary" :icon="Plus" @click="openCreateKey">新建密钥</el-button>
      </div>
      <el-card shadow="never" class="ai-card">
        <el-table :data="keys" v-loading="keysLoading">
          <el-table-column prop="name" label="名称" min-width="180" show-overflow-tooltip />
          <el-table-column label="范围" width="110">
            <template #default="{ row }">
              <el-tag :type="row.scope === 'dept' ? 'warning' : 'success'" size="small">
                {{ row.scope === 'dept' ? (row.department || '部门') : '全库' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="key_hint" label="密钥" width="140" />
          <el-table-column label="状态" width="90">
            <template #default="{ row }">
              <el-switch :model-value="row.active" @change="(v: any) => toggleKey(row, !!v)" />
            </template>
          </el-table-column>
          <el-table-column label="最近使用" width="170">
            <template #default="{ row }">{{ formatDate(row.last_used_at) }}</template>
          </el-table-column>
          <el-table-column prop="call_count" label="调用次数" width="90" align="center" />
          <el-table-column label="创建时间" width="170">
            <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="160" fixed="right">
            <template #default="{ row }">
              <el-button size="small" link type="warning" @click="rotateKey(row)">轮换</el-button>
              <el-button size="small" link type="danger" @click="deleteKey(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </div>

    <el-dialog v-model="createKey.open" title="新建数字员工密钥" width="440px">
      <el-form label-width="90px">
        <el-form-item label="名称" required>
          <el-input v-model="createKey.name" placeholder="例如：注册部数字员工" />
        </el-form-item>
        <el-form-item label="范围">
          <el-select v-model="createKey.scope" style="width: 100%">
            <el-option label="全库（所有分类）" value="all" />
            <el-option label="指定部门" value="dept" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="createKey.scope === 'dept'" label="部门">
          <el-select v-model="createKey.department" style="width: 100%">
            <el-option v-for="d in DEPARTMENTS" :key="d" :label="d" :value="d" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createKey.open = false">取消</el-button>
        <el-button type="primary" @click="createKeySubmit">生成</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="newKey.open" title="密钥已生成（仅显示一次，请立即保存）" width="520px">
      <div class="new-key-box">
        <code>{{ newKey.value }}</code>
      </div>
      <template #footer>
        <el-button type="primary" @click="copyNewKey">复制密钥</el-button>
        <el-button @click="newKey.open = false">我已保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { Search, Refresh, Plus } from '@element-plus/icons-vue'
import { get, post, put, del } from '@/api/client'
import { ElMessage, ElMessageBox } from 'element-plus'
import { DEPARTMENTS } from '@/utils/departments'

const tab = ref('docs')
const loading = ref(false)
const items = ref<any[]>([])
const total = ref(0)
const filters = reactive({ status: 'any', q: '', page: 1, size: 20 })
const viewer = reactive({ open: false, title: '', content: '' })
const keys = ref<any[]>([])
const keysLoading = ref(false)
const createKey = reactive({ open: false, name: '', scope: 'all', department: '' })
const newKey = reactive({ open: false, value: '' })

function statusLabel(s: string) {
  return { done: '已完成', pending: '待处理', failed: '失败', unsupported: '不支持' }[s] || s
}
const STATUS_TYPES = { done: 'success', pending: 'warning', failed: 'danger', unsupported: 'info' } as const
function statusType(s: string): 'success' | 'warning' | 'danger' | 'info' {
  return STATUS_TYPES[s as keyof typeof STATUS_TYPES] || 'info'
}
function formatSize(n: number) {
  if (!n) return '0 B'
  return n > 1048576 ? `${(n / 1048576).toFixed(1)} MB` : n > 1024 ? `${(n / 1024).toFixed(1)} KB` : `${n} B`
}
function formatDate(d: string) {
  return d ? d.replace('T', ' ').slice(0, 16) : '-'
}

async function load(page = 1) {
  loading.value = true
  filters.page = page
  try {
    const resp: any = await get('/api/ai/documents', {
      status: filters.status,
      q: filters.q || undefined,
      offset: (page - 1) * filters.size,
      limit: filters.size,
      include_content: false,
    })
    items.value = resp.items || []
    total.value = resp.total || 0
  } catch (e: any) {
    if (e?.response?.status === 401) ElMessage.error('无权限访问 AI 知识库')
    else ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

async function viewMarkdown(row: any) {
  try {
    const data: any = await get(`/api/ai/documents/${row.id}/markdown`)
    viewer.title = row.title
    viewer.content = data.markdown_content || ''
    viewer.open = true
  } catch {
    ElMessage.error('获取 Markdown 内容失败')
  }
}

async function copyMarkdown(row: any) {
  try {
    const data: any = await get(`/api/ai/documents/${row.id}/markdown`)
    await navigator.clipboard.writeText(data.markdown_content || '')
    ElMessage.success('已复制到剪贴板')
  } catch {
    ElMessage.error('复制失败')
  }
}

async function copyViewer() {
  try {
    await navigator.clipboard.writeText(viewer.content || '')
    ElMessage.success('已复制到剪贴板')
  } catch {
    ElMessage.error('复制失败')
  }
}

function downloadMd() {
  if (!viewer.content) return
  const blob = new Blob([viewer.content], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = (viewer.title || 'document').replace(/[\\/:*?"<>|]/g, '_') + '.md'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

function escapeHtml(s: string) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

function renderMarkdown(md: string) {
  if (!md) return ''
  const lines = escapeHtml(md).split('\n')
  const out: string[] = []
  let i = 0
  while (i < lines.length) {
    const line = lines[i].trim()
    if (!line) { i++; continue }
    const heading = line.match(/^(#{1,6})\s+(.*)$/)
    if (heading) {
      const level = Math.min(heading[1].length + 1, 6)
      out.push(`<h${level}>${heading[2]}</h${level}>`)
      i++
      continue
    }
    if (line.startsWith('|') && line.endsWith('|')) {
      const rows: string[][] = []
      let header: string[] | null = null
      while (i < lines.length && lines[i].trim().startsWith('|') && lines[i].trim().endsWith('|')) {
        const raw = lines[i].trim()
        const cells = raw.split('|').slice(1, -1).map((c) => c.trim())
        if (/^\|[\s:\-|]+\|$/.test(raw) && header === null) { i++; continue }
        if (header === null) header = cells
        else rows.push(cells)
        i++
      }
      if (header) {
        let t = '<table><thead><tr>' + header.map((c) => `<th>${c}</th>`).join('') + '</tr></thead><tbody>'
        t += rows.map((r) => '<tr>' + r.map((c) => `<td>${c}</td>`).join('') + '</tr>').join('')
        t += '</tbody></table>'
        out.push(t)
      }
      continue
    }
    if (/^[-*•]\s+/.test(line)) {
      out.push(`<p class="md-li">${line.replace(/^[-*•]\s+/, '')}</p>`)
      i++
      continue
    }
    out.push(`<p>${line}</p>`)
    i++
  }
  return out.join('')
}

async function regenerate(row: any) {
  try {
    await post(`/api/ai/documents/${row.id}/markdown/refresh`)
    ElMessage.success('已加入重新生成队列，稍后刷新查看')
  } catch {
    ElMessage.error('操作失败')
  }
}

function refreshAll() {
  load(filters.page)
}

async function loadKeys() {
  keysLoading.value = true
  try {
    const resp: any = await get('/api/ai/keys')
    keys.value = resp.items || []
  } catch {
    ElMessage.error('加载密钥失败')
  } finally {
    keysLoading.value = false
  }
}

function openCreateKey() {
  createKey.open = true
  createKey.name = ''
  createKey.scope = 'all'
  createKey.department = ''
}

async function createKeySubmit() {
  if (!createKey.name.trim()) return ElMessage.warning('请输入名称')
  try {
    const resp: any = await post('/api/ai/keys', {
      name: createKey.name.trim(),
      scope: createKey.scope,
      department: createKey.scope === 'dept' ? createKey.department : undefined,
    })
    createKey.open = false
    newKey.value = resp.key || ''
    newKey.open = true
    loadKeys()
  } catch {
    ElMessage.error('创建失败')
  }
}

async function toggleKey(row: any, active: boolean) {
  try {
    await put(`/api/ai/keys/${row.id}`, { active })
    row.active = active
    ElMessage.success(active ? '已启用' : '已停用')
  } catch {
    ElMessage.error('操作失败')
  }
}

async function rotateKey(row: any) {
  try {
    await ElMessageBox.confirm(`确认轮换密钥「${row.name}」？旧密钥立即失效。`, '轮换密钥', { type: 'warning' })
    const resp: any = await post(`/api/ai/keys/${row.id}/rotate`)
    newKey.value = resp.key || ''
    newKey.open = true
    loadKeys()
  } catch (e: any) {
    if (e !== 'cancel' && e !== 'close') ElMessage.error('轮换失败')
  }
}

async function deleteKey(row: any) {
  try {
    await ElMessageBox.confirm(`确认删除密钥「${row.name}」？`, '删除密钥', { type: 'error' })
    await del(`/api/ai/keys/${row.id}`)
    ElMessage.success('已删除')
    loadKeys()
  } catch (e: any) {
    if (e !== 'cancel' && e !== 'close') ElMessage.error('删除失败')
  }
}

async function copyNewKey() {
  try {
    await navigator.clipboard.writeText(newKey.value)
    ElMessage.success('已复制')
  } catch {
    ElMessage.error('复制失败')
  }
}

load(1)
</script>

<style scoped>
.ai-head { margin-bottom: 14px; }
.ai-head h2 { font-size: 18px; margin: 0 0 6px; }
.ai-sub { font-size: 12px; color: #888; margin: 0; }
.ai-tabs { display: flex; gap: 4px; margin-bottom: 14px; border-bottom: 1px solid #e5e7eb; }
.ai-tabs button {
  padding: 8px 16px; border: none; background: transparent; cursor: pointer;
  font-size: 14px; color: #555; border-bottom: 2px solid transparent;
}
.ai-tabs button.active { color: var(--color-primary); border-bottom-color: var(--color-primary); font-weight: 600; }
.keys-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.new-key-box {
  background: #f8fafc; border: 1px dashed #cbd5e1; border-radius: 8px;
  padding: 14px; overflow: auto;
}
.new-key-box code { font-family: Consolas, Monaco, monospace; font-size: 13px; word-break: break-all; }
.ai-filters { display: flex; gap: 10px; margin-bottom: 14px; flex-wrap: wrap; }
.ai-card { border-radius: 10px; }
.ai-pager { display: flex; justify-content: flex-end; padding-top: 14px; }
.md-viewer {
  max-height: 62vh; overflow: auto; background: #fff; color: #1f2937;
  border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px 18px;
}
.md-viewer :deep(.md-render) { font-size: 13px; line-height: 1.75; word-break: break-word; }
.md-viewer :deep(h1), .md-viewer :deep(h2), .md-viewer :deep(h3),
.md-viewer :deep(h4), .md-viewer :deep(h5), .md-viewer :deep(h6) {
  color: #1e50ae; margin: 14px 0 6px; line-height: 1.4;
}
.md-viewer :deep(h1) { font-size: 17px; } .md-viewer :deep(h2) { font-size: 15px; }
.md-viewer :deep(h3) { font-size: 14px; }
.md-viewer :deep(h4), .md-viewer :deep(h5), .md-viewer :deep(h6) { font-size: 13px; }
.md-viewer :deep(p) { margin: 4px 0; }
.md-viewer :deep(.md-li) { margin: 2px 0 2px 14px; }
.md-viewer :deep(table) {
  border-collapse: collapse; width: 100%; margin: 10px 0;
  font-size: 12px; font-variant-numeric: tabular-nums;
}
.md-viewer :deep(th), .md-viewer :deep(td) {
  border: 1px solid #cbd5e1; padding: 5px 8px; text-align: left; vertical-align: top;
}
.md-viewer :deep(th) { background: #1e50ae; color: #fff; position: sticky; top: 0; z-index: 1; }
.md-viewer :deep(tr:nth-child(even) td) { background: #f8fafc; }
.md-empty { color: #94a3b8; padding: 20px 0; text-align: center; }
</style>
