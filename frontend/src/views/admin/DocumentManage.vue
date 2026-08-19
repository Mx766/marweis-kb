<template>
  <div class="admin-page">
    <div class="page-toolbar">
      <el-button type="primary" :icon="UploadIcon" @click="openUploader">上传文档</el-button>
      <el-button :icon="LinkIcon" @click="openLinkAdder">添加外链</el-button>
      <el-select v-model="fileTypeFilter" placeholder="全部格式" clearable style="width:120px" @change="loadData">
        <el-option label="全部" value="" />
        <el-option v-for="t in ['pdf','doc','docx','xls','xlsx','ppt','link','txt']" :key="t" :label="t.toUpperCase()" :value="t" />
      </el-select>
      <el-input v-model="searchText" placeholder="搜索标题..." clearable style="width:220px" @input="onSearchInput" />
      <el-tree-select v-model="importCatId" :data="catTree" placeholder="拖拽导入分类" check-strictly
        node-key="id" :props="{ label: 'name' }" style="width:180px" clearable />
      <span class="total-hint">{{ total }} 篇文档</span>
      <el-button v-if="selected.length" type="danger" size="default" @click="batchDelete">批量删除 ({{ selected.length }})</el-button>
    </div>

    <div class="doc-table-wrap" @dragover.prevent @dragenter.prevent="onDragEnter"
      @dragleave.prevent="onDragLeave" @drop.prevent="handleDrop">
      <div v-if="dragActive" class="drop-overlay"><div class="drop-box">松开鼠标，导入文档</div></div>
    <el-table :data="documents" stripe v-loading="loading" @selection-change="onSelectionChange"
      :default-sort="{prop:'updated_at',order:'descending'}" @sort-change="onSortChange">
      <el-table-column type="selection" width="40" />
      <el-table-column label="标题" min-width="260" show-overflow-tooltip sortable="custom">
        <template #default="{ row }">{{ cleanTitle(row.title) }}</template>
      </el-table-column>
      <el-table-column label="格式" width="70" align="center">
        <template #default="{ row }">
          <span class="fmt-tag" :class="row.file_type==='link'?'link':'file'">
            {{ (row.file_ext || 'LNK').toUpperCase().substring(0,4) }}
          </span>
        </template>
      </el-table-column>
      <el-table-column prop="uploader_name" label="上传者" width="90" />
      <el-table-column label="更新时间" width="140" sortable="custom" prop="updated_at">
        <template #default="{ row }">{{ formatDate(row.updated_at) }}</template>
      </el-table-column>
      <el-table-column prop="view_count" label="浏览" width="70" align="center" sortable="custom" />
      <el-table-column label="操作" width="240" fixed="right">
        <template #default="{ row }">
          <div class="act-btns">
            <el-button size="small" type="primary" @click.stop="$router.push(`/document/${row.id}`)">查看</el-button>
            <el-button size="small" @click.stop="handleEdit(row)">编辑</el-button>
            <el-popconfirm title="确定删除？" @confirm="handleDelete(row)">
              <template #reference>
                <el-button size="small" type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </div>
        </template>
      </el-table-column>
    </el-table>
    </div>

    <div class="pagination-wrap">
      <el-pagination v-model:current-page="page" :page-size="size" :total="total"
        layout="total, sizes, prev, pager, next" :page-sizes="[20,50,100]"
        @current-change="loadData" @size-change="(s:number)=>{size=s;loadData();}" />
    </div>

    <!-- Upload Dialog -->
    <el-dialog v-model="uploadVisible" title="上传文档" width="550px">
      <el-form :model="docForm" label-width="80px">
        <el-form-item label="标题"><el-input v-model="docForm.title" placeholder="文档标题" /></el-form-item>
        <el-form-item label="分类">
          <el-tree-select v-model="docForm.category_id" :data="catTree" placeholder="选择分类" check-strictly node-key="id" :props="{ label: 'name' }" style="width:100%" />
        </el-form-item>
        <el-form-item label="标签"><el-input v-model="docForm.tags" placeholder="逗号分隔，如: 法规,2025,注册" /></el-form-item>
        <el-form-item label="摘要"><el-input v-model="docForm.summary" type="textarea" :rows="3" placeholder="文档摘要/简介" /></el-form-item>
        <el-form-item label="来源"><el-input v-model="docForm.source" placeholder="来源（如 NMPA、CMDE）" /></el-form-item>
        <el-form-item label="文件" v-if="uploadMode==='file'">
          <el-upload :auto-upload="false" :on-change="handleFileChange" :limit="1">
            <el-button type="primary">选择文件</el-button>
            <template #tip><div style="font-size:12px;margin-top:4px">支持 PDF、Word、Excel、PPT、TXT、图片等（最大 500MB）</div></template>
          </el-upload>
        </el-form-item>
        <el-form-item label="链接" v-if="uploadMode==='link'"><el-input v-model="docForm.source_url" placeholder="https://..." /></el-form-item>
      </el-form>
      <template #footer><el-button @click="uploadVisible=false">取消</el-button><el-button type="primary" @click="handleUpload" :loading="uploading">上传</el-button></template>
    </el-dialog>

    <!-- Edit Dialog -->
    <el-dialog v-model="editVisible" title="编辑文档信息" width="500px">
      <el-form :model="editForm" label-width="80px">
        <el-form-item label="标题"><el-input v-model="editForm.title" /></el-form-item>
        <el-form-item label="分类">
          <el-tree-select v-model="editForm.category_id" :data="catTree" placeholder="选择分类" check-strictly node-key="id" :props="{ label: 'name' }" style="width:100%" />
        </el-form-item>
        <el-form-item label="标签"><el-input v-model="editForm.tags" /></el-form-item>
        <el-form-item label="摘要"><el-input v-model="editForm.summary" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="来源"><el-input v-model="editForm.source" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="editVisible=false">取消</el-button><el-button type="primary" @click="handleSaveEdit" :loading="saving">保存</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Upload as UploadIcon, Link as LinkIcon } from '@element-plus/icons-vue'
import { get, post, put, del } from '@/api/client'
import { ElMessage, ElMessageBox } from 'element-plus'
import dayjs from 'dayjs'

const documents = ref<any[]>([])
const loading = ref(false); const saving = ref(false); const uploading = ref(false)
const page = ref(1); const size = ref(20); const total = ref(0)
const searchText = ref(''); const fileTypeFilter = ref('')
const sortField = ref('updated_at'); const sortOrder = ref('desc')
const selected = ref<any[]>([])

const catTree = ref<any[]>([])
const importCatId = ref('')
const dragActive = ref(false)
let _dragDepth = 0
const uploadVisible = ref(false); const uploadMode = ref('file')
const editVisible = ref(false)
const docForm = ref<any>({ title:'', category_id:'', tags:'', summary:'', source:'', source_url:'' })
const editForm = ref<any>({})
const file = ref<any>(null)

let _searchTimer: any = null

function onSearchInput() { if(_searchTimer) clearTimeout(_searchTimer); _searchTimer = setTimeout(()=>{ page.value=1; loadData(); }, 400) }
function onSortChange({ prop, order }: any) { sortField.value = prop||'updated_at'; sortOrder.value = order==='ascending'?'asc':'desc'; loadData() }
function onSelectionChange(rows: any[]) { selected.value = rows }
function formatDate(d: string) { return d ? dayjs(d).format('YYYY-MM-DD HH:mm') : '' }
function cleanTitle(t: string) {
  if(!t) return ''
  // Clean NMPA scrape filenames: remove hash-like segments, restore readable parts
  return t.replace(/NMPA_标签_tagInfo[0-9a-f]{8,}/g,'NMPA-').replace(/_/g,' ').replace(/\s+/g,' ').trim().substring(0,80)
}

onMounted(loadCats)

function onDragEnter() { _dragDepth++; dragActive.value = true }
function onDragLeave() { _dragDepth--; if (_dragDepth <= 0) { _dragDepth = 0; dragActive.value = false } }

async function handleDrop(e: DragEvent) {
  _dragDepth = 0; dragActive.value = false
  const catId = importCatId.value || docForm.value.category_id
  if (!catId) { ElMessage.warning('请先选择“拖拽导入分类”'); return }
  const collected: { file: File; rel: string }[] = []
  // 事件一开始就同步捕获，拖拽会话结束后 DataTransfer 会被清空/失效
  const items = Array.from(e.dataTransfer?.items || [])
  const fl = e.dataTransfer?.files ? Array.from(e.dataTransfer.files) : []
  let entryFound = false
  for (const it of items) {
    const entry: any = it.webkitGetAsEntry?.()
    if (!entry) continue
    entryFound = true
    await Promise.race([
      walkEntry(entry, '', collected),
      new Promise((res) => setTimeout(res, 8000)),
    ])
  }
  if (fl.length) {
    for (const f of Array.from(fl)) {
      const rel = (f as any).webkitRelativePath || f.name
      // 真实拖拽文件夹时 files 里只有 0 字节占位 File，跳过（内容已由目录遍历收集）
      if (entryFound && f.size === 0 && !(f as any).webkitRelativePath) continue
      // 兜底路径下也跳过 0 字节、无扩展名的文件夹占位
      if (!entryFound && f.size === 0 && !(f as any).webkitRelativePath && !f.name.includes('.')) continue
      if (collected.some((c) => c.rel === rel && c.file.size === f.size)) continue
      collected.push({ file: f, rel })
    }
  }
  if (!collected.length) { ElMessage.warning('未识别到可导入的文件，请直接拖入文件或文件夹'); return }
  const list = collected.slice()
  uploading.value = true
  let ok = 0, fail = 0
  for (const { file: f, rel } of list) {
    const fd = new FormData()
    fd.append('file', f)
    fd.append('title', rel.replace(/\.[^.]+$/, ''))
    fd.append('category_id', catId)
    fd.append('tags', '[]')
    fd.append('summary', '拖拽导入')
    try { await post('/api/admin/documents/upload', fd); ok++ } catch { fail++ }
  }
  uploading.value = false
  loadData()
  ElMessage.success(fail ? `导入完成：${ok} 成功，${fail} 失败` : `导入完成：${ok} 个文档`)
}

function walkEntry(entry: any, path: string, out: { file: File; rel: string }[]): Promise<void> {
  return new Promise((resolve) => {
    if (!entry) { resolve(); return }
    if (entry.isFile) {
      entry.file((f: File) => {
        out.push({ file: f, rel: path ? `${path}/${f.name}` : f.name })
        resolve()
      }, resolve)
      return
    }
    if (entry.isDirectory) {
      const reader = entry.createReader()
      const readAll = () => {
        reader.readEntries(async (entries: any[]) => {
          if (!entries.length) { resolve(); return }
          const nextPath = path ? `${path}/${entry.name}` : entry.name
          for (const en of entries) {
            await walkEntry(en, nextPath, out)
          }
          readAll()
        }, resolve)
      }
      readAll()
      return
    }
    resolve()
  })
}

async function loadData() {
  loading.value = true
  try {
    const p: any = { page: page.value, size: size.value, sort: sortField.value, order: sortOrder.value }
    if(searchText.value) p.q = searchText.value
    if(fileTypeFilter.value) p.file_type = fileTypeFilter.value
    const resp: any = await get('/api/admin/documents', p)
    documents.value = resp.items || []; total.value = resp.total || 0
  } catch { documents.value = [] }
  loading.value = false
}

async function loadCats() { try { catTree.value = await get('/api/categories') } catch {} }

function openUploader() { uploadMode.value = 'file'; docForm.value = { title:'', category_id:'', tags:'', summary:'', source:'', source_url:'' }; uploadVisible.value = true; loadCats() }
function openLinkAdder() { uploadMode.value = 'link'; docForm.value = { title:'', category_id:'', tags:'', summary:'', source:'', source_url:'' }; uploadVisible.value = true; loadCats() }
function handleFileChange(f: any) { file.value = f.raw }

async function handleUpload() {
  if(!docForm.value.title) { ElMessage.warning('请输入标题'); return }
  uploading.value = true
  try {
    if(uploadMode.value === 'file' && file.value){
      const fd = new FormData(); fd.append('file', file.value)
      fd.append('title', docForm.value.title); fd.append('category_id', docForm.value.category_id||'')
      if(docForm.value.tags) fd.append('tags', docForm.value.tags)
      if(docForm.value.summary) fd.append('summary', docForm.value.summary)
      if(docForm.value.source) fd.append('source', docForm.value.source)
      await post('/api/admin/documents/upload', fd)
    } else {
      await post('/api/admin/documents/link', { ...docForm.value })
    }
    uploadVisible.value = false; ElMessage.success('上传成功'); loadData()
  } catch { ElMessage.error('上传失败') }
  uploading.value = false
}

function handleEdit(row: any) {
  editForm.value = { ...row, tags: (row.tags||[]).join(',') }
  editVisible.value = true; loadCats()
}
async function handleSaveEdit() {
  saving.value = true
  try {
    const body = { ...editForm.value, tags: editForm.value.tags?.split(',').map((s:string)=>s.trim()).filter(Boolean) }
    await put(`/api/admin/documents/${editForm.value.id}`, body)
    editVisible.value = false; ElMessage.success('已保存'); loadData()
  } catch { ElMessage.error('保存失败') }
  saving.value = false
}

async function handleDelete(row: any) { try { await del(`/api/admin/documents/${row.id}`); ElMessage.success('已删除'); loadData() } catch { ElMessage.error('删除失败') } }
async function batchDelete() {
  try {
    await ElMessageBox.confirm(`确定删除选中的 ${selected.value.length} 篇文档？`,'批量删除',{type:'warning'})
    for(const d of selected.value) await del(`/api/admin/documents/${d.id}`)
    selected.value = []; ElMessage.success('已删除'); loadData()
  } catch {}
}

onMounted(loadData)
</script>

<style scoped>
.doc-table-wrap { position: relative; }
.drop-overlay {
  position: absolute; inset: 0; z-index: 20;
  display: flex; align-items: center; justify-content: center;
  background: rgba(30, 80, 174, .12); border: 2px dashed var(--color-primary);
  border-radius: 8px;
}
.drop-box {
  background: var(--color-primary); color: #fff;
  padding: 16px 32px; border-radius: 8px; font-size: 15px;
  box-shadow: 0 8px 24px rgba(30, 80, 174, .3);
}
.admin-page { padding: 16px 20px; }
.page-toolbar { display:flex; align-items:center; gap:10px; margin-bottom:16px; flex-wrap:wrap; }
.total-hint { font-size:13px; color:#888; margin-left:auto; }
.pagination-wrap { display:flex; justify-content:center; padding:16px 0 0; }

.fmt-tag { font-size:11px; font-weight:600; padding:2px 6px; border-radius:4px; }
.fmt-tag.file { background:#e8f0fe; color:#1e50ae; }
.fmt-tag.link { background:#e8faf0; color:#0891b2; }
.act-btns { display:flex; align-items:center; gap:6px; white-space:nowrap; }
</style>
