<template>
  <div class="admin-page">
    <div class="page-toolbar">
      <el-button type="primary" :icon="UploadIcon" @click="openUploader">上传文档</el-button>
      <el-button :icon="LinkIcon" @click="openLinkAdder">添加外链</el-button>
      <el-input v-model="searchText" placeholder="搜索文档标题..." clearable style="width:260px" @change="loadData" />
    </div>

    <el-table :data="documents" stripe v-loading="loading" @row-click="viewDoc">
      <el-table-column prop="title" label="标题" min-width="280" show-overflow-tooltip />
      <el-table-column label="格式" width="80">
        <template #default="{ row }">
          <el-tag :type="row.file_type === 'link' ? 'info' : 'primary'" size="small">
            {{ row.file_ext?.toUpperCase() || '链接' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="uploader_name" label="上传者" width="100" />
      <el-table-column label="更新时间" width="150">
        <template #default="{ row }">{{ formatDate(row.updated_at) }}</template>
      </el-table-column>
      <el-table-column prop="view_count" label="浏览" width="70" />
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click.stop="$router.push(`/document/${row.id}`)">查看</el-button>
          <el-button size="small" @click.stop="handleEdit(row)">编辑</el-button>
          <el-button size="small" type="danger" @click.stop="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination-wrap">
      <el-pagination
        v-model:current-page="page"
        :page-size="size"
        :total="total"
        layout="total, sizes, prev, pager, next, jumper" :page-sizes="[10,20,50]"
        @current-change="loadData"
        @size-change="(s: number) => { size = s; loadData(); }"
      />
    </div>

    <!-- Upload Dialog -->
    <el-dialog v-model="uploadVisible" title="上传文档" width="550px">
      <el-form :model="docForm" label-width="80px">
        <el-form-item label="标题">
          <el-input v-model="docForm.title" placeholder="文档标题" />
        </el-form-item>
        <el-form-item label="分类">
          <el-tree-select
            v-model="docForm.category_id"
            :data="catTree"
            placeholder="选择分类"
            check-strictly
            :props="{ label: 'name' }"
            style="width:100%"
          />
        </el-form-item>
        <el-form-item label="标签">
          <el-input v-model="docForm.tags" placeholder="逗号分隔，如: 法规,2025,注册" />
        </el-form-item>
        <el-form-item label="摘要">
          <el-input v-model="docForm.summary" type="textarea" :rows="3" placeholder="文档摘要/简介" />
        </el-form-item>
        <el-form-item label="来源">
          <el-input v-model="docForm.source" placeholder="来源（如 NMPA、CMDE）" />
        </el-form-item>
        <el-form-item label="文件" v-if="uploadMode === 'file'">
          <el-upload
            :auto-upload="false"
            :on-change="handleFileChange"
            :limit="1"
          >
            <el-button type="primary">选择文件</el-button>
            <template #tip>
              <div style="font-size:12px;margin-top:4px">
                支持 PDF、Word、Excel、PPT、TXT、图片、音视频等（最大 500MB）
              </div>
            </template>
          </el-upload>
        </el-form-item>
        <el-form-item label="链接" v-if="uploadMode === 'link'">
          <el-input v-model="docForm.source_url" placeholder="https://..." />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="uploadVisible = false">取消</el-button>
        <el-button type="primary" @click="handleUpload" :loading="uploading">上传</el-button>
      </template>
    </el-dialog>

    <!-- Edit Metadata Dialog -->
    <el-dialog v-model="editVisible" title="编辑文档信息" width="500px">
      <el-form :model="editForm" label-width="80px">
        <el-form-item label="标题">
          <el-input v-model="editForm.title" />
        </el-form-item>
        <el-form-item label="分类">
          <el-tree-select
            v-model="editForm.category_id"
            :data="catTree"
            placeholder="选择分类"
            check-strictly
            :props="{ label: 'name' }"
            style="width:100%"
          />
        </el-form-item>
        <el-form-item label="标签">
          <el-input v-model="editForm.tags" placeholder="逗号分隔" />
        </el-form-item>
        <el-form-item label="摘要">
          <el-input v-model="editForm.summary" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="版本">
          <el-input v-model="editForm.version" placeholder="如 v3.2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSaveEdit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Upload as UploadIcon, Link as LinkIcon } from '@element-plus/icons-vue'
import { get, post, put, del, client } from '@/api/client'
import dayjs from 'dayjs'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()
const documents = ref<any[]>([])
const loading = ref(false)
const page = ref(1)
const size = ref(20)
const total = ref(0)
const searchText = ref('')
const catTree = ref<any[]>([])

const uploadVisible = ref(false)
const uploadMode = ref('file')
const uploading = ref(false)
const selectedFile = ref<any>(null)

const editVisible = ref(false)
const editingId = ref('')

const docForm = ref({ title: '', category_id: '', tags: '', summary: '', source: '', source_url: '' })
const editForm = ref({ title: '', category_id: '', tags: '', summary: '', version: '' })

function formatDate(d: string) { return dayjs(d).format('YYYY-MM-DD HH:mm') }

async function loadData() {
  loading.value = true
  try {
    const params: any = { page: page.value, size: size.value, sort: 'updated_at', order: 'desc' }
    let resp: any
    if (searchText.value) {
      resp = await get('/api/search', { q: searchText.value, page: page.value, size: size.value })
    } else {
      resp = await get('/api/documents', params)
    }
    documents.value = resp.items || []
    total.value = resp.total || 0
  } catch { documents.value = []; total.value = 0 }
  loading.value = false
}

async function loadCats() {
  const tree = await get('/api/categories')
  catTree.value = tree
}

function viewDoc(row: any) { router.push(`/document/${row.id}`) }

function openUploader() { uploadMode.value = 'file'; resetDocForm(); uploadVisible.value = true }
function openLinkAdder() { uploadMode.value = 'link'; resetDocForm(); uploadVisible.value = true }

function resetDocForm() {
  docForm.value = { title: '', category_id: '', tags: '', summary: '', source: '', source_url: '' }
  selectedFile.value = null
}

function handleFileChange(uploadFile: any) {
  selectedFile.value = uploadFile.raw
}

async function handleUpload() {
  if (!docForm.value.title.trim()) { ElMessage.warning('请输入标题'); return }
  uploading.value = true
  try {
    const fd = new FormData()
    fd.append('title', docForm.value.title)
    if (docForm.value.category_id) fd.append('category_id', docForm.value.category_id)
    fd.append('tags', JSON.stringify(docForm.value.tags.split(',').map(t => t.trim()).filter(Boolean)))
    if (docForm.value.summary) fd.append('summary', docForm.value.summary)
    if (docForm.value.source) fd.append('source', docForm.value.source)
    if (docForm.value.source_url) fd.append('source_url', docForm.value.source_url)
    if (uploadMode.value === 'file' && selectedFile.value) {
      fd.append('file', selectedFile.value)
    }

    await client.post('/api/documents', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
    ElMessage.success('上传成功')
    uploadVisible.value = false
    loadData()
  } catch { ElMessage.error('上传失败') }
  uploading.value = false
}

function handleEdit(row: any) {
  editingId.value = row.id
  editForm.value = {
    title: row.title || '',
    category_id: row.category_id || '',
    tags: (row.tags || []).join(', '),
    summary: row.summary || '',
    version: row.version || '',
  }
  editVisible.value = true
}

async function handleSaveEdit() {
  try {
    const payload: any = {
      title: editForm.value.title,
      category_id: editForm.value.category_id || null,
      tags: editForm.value.tags.split(',').map(t => t.trim()).filter(Boolean),
      summary: editForm.value.summary,
      version: editForm.value.version,
    }
    await put(`/api/documents/${editingId.value}`, payload)
    ElMessage.success('更新成功')
    editVisible.value = false
    loadData()
  } catch { ElMessage.error('更新失败') }
}

async function handleDelete(row: any) {
  try {
    await ElMessageBox.confirm(`确定删除 "${row.title}"？`, '确认删除', { type: 'warning' })
    await del(`/api/documents/${row.id}`)
    ElMessage.success('已删除')
    loadData()
  } catch { /* cancelled */ }
}

onMounted(async () => { await loadCats(); loadData() })
</script>

<style scoped>
.admin-page { background: #fff; border-radius: var(--radius-md); padding: var(--spacing-lg); }
.page-toolbar { display: flex; gap: var(--spacing-sm); margin-bottom: var(--spacing-md); }
.pagination-wrap { display: flex; justify-content: center; padding: var(--spacing-lg); }
</style>
