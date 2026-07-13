<template>
  <div class="admin-page">
    <div class="page-toolbar">
      <el-button type="primary" @click="handleAdd">添加用户</el-button>
      <el-select v-model="filterDept" placeholder="按部门筛选" clearable style="width:180px" @change="loadData">
        <el-option v-for="d in departments" :key="d" :label="d" :value="d" />
      </el-select>
    </div>

    <el-table :data="users" stripe v-loading="loading">
      <el-table-column prop="username" label="用户名" width="110" />
      <el-table-column prop="display_name" label="姓名" width="100" />
      <el-table-column prop="employee_id" label="工号" width="80" />
      <el-table-column prop="department" label="部门" width="140" />
      <el-table-column label="角色" width="120">
        <template #default="{ row }">
          <el-tag
            :type="row.role === 'super_admin' ? 'danger' : row.role === 'dept_admin' ? 'warning' : 'info'"
            size="small"
          >{{ roleLabel(row.role) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="email" label="邮箱" min-width="180" />
      <el-table-column label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">
            {{ row.is_active ? '启用' : '停用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="handleEdit(row)">编辑</el-button>
          <el-button size="small" :type="row.is_active ? 'danger' : 'success'" @click="handleToggle(row)">
            {{ row.is_active ? '停用' : '启用' }}
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination-wrap">
      <el-pagination
        v-model:current-page="page"
        :page-size="size"
        :total="total"
        layout="prev, pager, next"
        @current-change="loadData"
      />
    </div>

    <!-- User Form Dialog -->
    <el-dialog v-model="dialogVisible" :title="editMode === 'add' ? '添加用户' : '编辑用户'" width="500px">
      <el-form :model="userForm" label-width="100px">
        <el-form-item label="用户名">
          <el-input v-model="userForm.username" placeholder="登录用户名" :disabled="editMode === 'edit'" />
        </el-form-item>
        <el-form-item label="密码" v-if="editMode === 'add'">
          <el-input v-model="userForm.password" type="password" placeholder="默认密码 123456" show-password />
        </el-form-item>
        <el-form-item label="姓名">
          <el-input v-model="userForm.display_name" placeholder="真实姓名" />
        </el-form-item>
        <el-form-item label="工号">
          <el-input v-model="userForm.employee_id" placeholder="员工工号（可选）" />
        </el-form-item>
        <el-form-item label="部门">
          <el-select v-model="userForm.department" placeholder="选择部门" style="width:100%">
            <el-option v-for="d in departments" :key="d" :label="d" :value="d" />
          </el-select>
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="userForm.role" placeholder="选择角色" style="width:100%">
            <el-option v-for="(label, value) in roleOptions" :key="value" :label="label" :value="value" />
          </el-select>
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="userForm.email" placeholder="邮箱（可选）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSaveUser">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { get, post, put } from '@/api/client'
import { ElMessage } from 'element-plus'

const departments = [
  '器械注册部', '临床评价部', '临床试验部', '生产体系部',
  '化妆品·医美部', '特医食品部', '管理层',
]
const roleOptions: Record<string, string> = {
  super_admin: '超级管理员',
  dept_admin: '部门管理员',
  editor: '编辑者',
  employee: '普通员工',
  guest: '访客',
}
const roleLabels: Record<string, string> = {
  super_admin: '超管', dept_admin: '部门管理员', editor: '编辑者', employee: '员工', guest: '访客',
}
function roleLabel(r: string) { return roleLabels[r] || r }

const users = ref<any[]>([])
const loading = ref(false)
const page = ref(1)
const size = ref(20)
const total = ref(0)
const filterDept = ref('')
const dialogVisible = ref(false)
const editMode = ref('add')
const editingId = ref('')

const userForm = ref({
  username: '', password: '123456', display_name: '', employee_id: '',
  department: '', role: 'employee', email: '',
})

async function loadData() {
  loading.value = true
  try {
    const params: any = { page: page.value, size: size.value }
    if (filterDept.value) params.department = filterDept.value
    const resp: any = await get('/api/admin/users', params)
    users.value = resp.items || []
    total.value = resp.total || 0
  } catch { users.value = []; total.value = 0 }
  loading.value = false
}

function resetForm() {
  userForm.value = {
    username: '', password: '123456', display_name: '', employee_id: '',
    department: '', role: 'employee', email: '',
  }
}

function handleAdd() {
  editMode.value = 'add'
  editingId.value = ''
  resetForm()
  dialogVisible.value = true
}

function handleEdit(row: any) {
  editMode.value = 'edit'
  editingId.value = row.id
  userForm.value = {
    username: row.username,
    password: '',
    display_name: row.display_name || '',
    employee_id: row.employee_id || '',
    department: row.department || '',
    role: row.role || 'employee',
    email: row.email || '',
  }
  dialogVisible.value = true
}

async function handleSaveUser() {
  try {
    if (editMode.value === 'add') {
      await post('/api/admin/users', { ...userForm.value, password: userForm.value.password || '123456' })
      ElMessage.success('用户已创建')
    } else {
      const payload: any = { ...userForm.value }
      if (!payload.password) delete payload.password
      await put(`/api/admin/users/${editingId.value}`, payload)
      ElMessage.success('用户已更新')
    }
    dialogVisible.value = false
    loadData()
  } catch { ElMessage.error('操作失败') }
}

async function handleToggle(row: any) {
  try {
    await put(`/api/admin/users/${row.id}`, { is_active: !row.is_active })
    ElMessage.success(row.is_active ? '已停用' : '已启用')
    loadData()
  } catch { ElMessage.error('操作失败') }
}

onMounted(loadData)
</script>

<style scoped>
.admin-page { background: #fff; border-radius: var(--radius-md); padding: var(--spacing-lg); }
.page-toolbar { display: flex; gap: var(--spacing-sm); margin-bottom: var(--spacing-md); }
.pagination-wrap { display: flex; justify-content: center; padding: var(--spacing-lg); }
</style>
