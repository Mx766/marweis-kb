<template>
  <div class="admin-page">
    <div class="page-toolbar">
      <el-button type="primary" @click="handleAdd">添加一级分类</el-button>
      <el-button @click="loadData" :loading="loading">刷新</el-button>
    </div>

    <!-- Department tabs -->
    <el-tabs v-model="activeDept" @tab-change="onDeptChange">
      <el-tab-pane label="全部" name="all" />
      <el-tab-pane
        v-for="d in sortedDepts"
        :key="d.name"
        :label="`${d.name} (${d.count})`"
        :name="d.name"
      />
    </el-tabs>

    <el-table :data="filteredCategories" stripe row-key="id" v-loading="loading">
      <el-table-column label="排序" width="60" align="center">
        <template #default="{ row }">
          <span style="color:#999;font-size:12px">{{ row.sort_order || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column label="分类名称" min-width="280">
        <template #default="{ row }">
          <span :style="{ paddingLeft: row._level * 24 + 'px' }">
            <el-icon><Folder /></el-icon>
            {{ row.name }}
            <span style="color: #999; font-size: 12px; margin-left: 8px">
              ({{ row.document_count || 0 }} 篇)
            </span>
          </span>
        </template>
      </el-table-column>
      <el-table-column label="可见部门" width="300">
        <template #default="{ row }">
          <el-tag v-if="!row.visible_departments" type="success" size="small">全员可见</el-tag>
          <template v-else>
            <el-tag v-for="d in row.visible_departments" :key="d" size="small" style="margin-right:4px">
              {{ d }}
            </el-tag>
          </template>
        </template>
      </el-table-column>
      <el-table-column label="描述" min-width="180">
        <template #default="{ row }">
          <span style="font-size:12px;color:#999">{{ row.description || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="280" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="handleAddChild(row)">添加子分类</el-button>
          <el-button size="small" @click="handleEdit(row)">编辑</el-button>
          <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- Form Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="editMode === 'add' ? '添加分类' : '编辑分类'"
      width="500px"
    >
      <el-form :model="form" label-width="100px">
        <el-form-item label="分类名称">
          <el-input v-model="form.name" placeholder="输入分类名称" />
        </el-form-item>
        <el-form-item label="父分类">
          <el-tree-select
            v-model="form.parent_id"
            :data="parentOptions"
            placeholder="不选则为一级分类"
            clearable
            check-strictly
            :props="{ label: 'name', value: 'id' }"
            style="width:100%"
          />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="form.sort_order" :min="0" placeholder="数字越小越靠前" style="width:100%" />
        </el-form-item>
        <el-form-item label="图标">
          <el-input v-model="form.icon" placeholder="图标名称（可选）" />
        </el-form-item>
        <el-form-item label="可见部门">
          <el-select v-model="form.visible_departments" multiple placeholder="不选则全员可见" style="width:100%">
            <el-option v-for="d in departments" :key="d" :label="d" :value="d" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="分类描述（可选）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Folder } from '@element-plus/icons-vue'
import { get, post, put, del } from '@/api/client'
import { ElMessage, ElMessageBox } from 'element-plus'

const departments = [
  '器械注册部', '临床评价部', '临床试验部', '生产体系部',
  '化妆品·医美部', '特医食品部', '管理层',
]

const categories = ref<any[]>([])
const loading = ref(false)
const dialogVisible = ref(false)
const editMode = ref('add')
const editingId = ref('')
const parentOptions = ref<any[]>([])
const activeDept = ref('all')

const form = ref({
  name: '', parent_id: '', sort_order: 0, icon: '', visible_departments: [] as string[], description: '',
})

// ── Department grouping ──────────────────────────────
const sortedDepts = computed(() => {
  const map: Record<string, number> = {}
  for (const d of departments) map[d] = 0
  for (const c of categories.value) {
    if (!c.visible_departments) {
      // Public categories: count for all depts
      for (const d of departments) map[d] += 1
    } else {
      for (const d of c.visible_departments) {
        if (map[d] !== undefined) map[d] += 1
      }
    }
  }
  return departments.map(d => ({ name: d, count: map[d] }))
})

const filteredCategories = computed(() => {
  if (activeDept.value === 'all') return categories.value
  return categories.value.filter(c => {
    if (!c.visible_departments) return true // public → visible to all
    return c.visible_departments.includes(activeDept.value)
  })
})

function onDeptChange() {} // reactivity handles filtering

// ── Tree flattening ──────────────────────────────────
function flatten(cats: any[], level = 0): any[] {
  let result: any[] = []
  for (const c of cats) {
    result.push({ ...c, _level: level })
    if (c.children?.length) result = result.concat(flatten(c.children, level + 1))
  }
  return result
}

async function loadData() {
  loading.value = true
  try {
    const tree: any = await get('/api/categories')
    categories.value = flatten(tree)
    parentOptions.value = tree
  } catch { categories.value = []; parentOptions.value = [] }
  loading.value = false
}

function resetForm() {
  form.value = { name: '', parent_id: '', sort_order: 0, icon: '', visible_departments: [], description: '' }
}

function handleAdd() {
  editMode.value = 'add'; editingId.value = ''; resetForm(); dialogVisible.value = true
}

function handleAddChild(row: any) {
  editMode.value = 'add'; editingId.value = ''; resetForm()
  form.value.parent_id = row.id; dialogVisible.value = true
}

function handleEdit(row: any) {
  editMode.value = 'edit'; editingId.value = row.id
  form.value = {
    name: row.name, parent_id: row.parent_id || '', sort_order: row.sort_order || 0,
    icon: row.icon || '', visible_departments: row.visible_departments || [], description: row.description || '',
  }
  dialogVisible.value = true
}

async function handleSave() {
  try {
    const payload: any = { ...form.value }
    if (!payload.parent_id) delete payload.parent_id
    if (!payload.visible_departments?.length) payload.visible_departments = null

    if (editMode.value === 'add') {
      await post('/api/categories', payload)
      ElMessage.success('分类已添加')
    } else {
      await put(`/api/categories/${editingId.value}`, payload)
      ElMessage.success('分类已更新')
    }
    dialogVisible.value = false
    loadData()
  } catch { ElMessage.error('操作失败') }
}

async function handleDelete(row: any) {
  try {
    await ElMessageBox.confirm(`确定删除"${row.name}"？子分类不会被删除。`, '确认删除', { type: 'warning' })
    await del(`/api/categories/${row.id}`)
    ElMessage.success('已删除')
    loadData()
  } catch { /* cancelled */ }
}

onMounted(loadData)
</script>

<style scoped>
.admin-page { background: #fff; border-radius: var(--radius-md); padding: var(--spacing-lg); }
.page-toolbar { margin-bottom: var(--spacing-md); display: flex; gap: var(--spacing-sm); }
</style>
