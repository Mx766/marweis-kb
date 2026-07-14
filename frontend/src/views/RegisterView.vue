<template>
  <div class="register-page">
    <div class="register-card">
      <div class="register-header">
        <div class="register-icon">M</div>
        <h2>注册账号</h2>
        <p>迈瑞生知识库</p>
      </div>
      <el-form @submit.prevent="handleRegister" :model="form" :rules="rules" ref="formRef">
        <el-form-item prop="username">
          <el-input v-model="form.username" placeholder="用户名" size="large" />
        </el-form-item>
        <el-form-item prop="display_name">
          <el-input v-model="form.display_name" placeholder="姓名" size="large" />
        </el-form-item>
        <el-form-item prop="department">
          <el-select v-model="form.department" placeholder="选择部门" size="large" style="width:100%">
            <el-option v-for="d in departments" :key="d" :label="d" :value="d" />
          </el-select>
        </el-form-item>
        <el-form-item prop="password">
          <el-input v-model="form.password" type="password" placeholder="密码 (至少8位，含字母+数字)" size="large" show-password />
        </el-form-item>
        <el-form-item prop="confirm">
          <el-input v-model="form.confirm" type="password" placeholder="确认密码" size="large" show-password />
        </el-form-item>
        <el-button type="primary" native-type="submit" size="large" :loading="loading" class="register-btn">
          注 册
        </el-button>
      </el-form>
      <div class="register-footer">
        <p>已有账号？<router-link to="/login">去登录</router-link></p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { post } from '@/api/client'
import { ElMessage } from 'element-plus'

const router = useRouter()
const loading = ref(false)
const formRef = ref()
const form = reactive({ username: '', display_name: '', department: '', password: '', confirm: '' })

const departments = [
  '器械注册部', '临床评价部', '临床试验部', '生产体系部',
  '化妆品·医美部', '特医食品部', '管理层',
]

const validateConfirm = (_rule: any, value: string, callback: any) => {
  if (value !== form.password) callback(new Error('两次密码输入不一致'))
  else callback()
}

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  display_name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  department: [{ required: true, message: '请选择部门', trigger: 'change' }],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, message: '密码至少8位', trigger: 'blur' },
    { pattern: /[A-Za-z]/, message: '密码需包含字母', trigger: 'blur' },
    { pattern: /\d/, message: '密码需包含数字', trigger: 'blur' },
  ],
  confirm: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    { validator: validateConfirm, trigger: 'blur' },
  ],
}

async function handleRegister() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  try {
    await post('/api/auth/register', {
      username: form.username,
      display_name: form.display_name,
      department: form.department,
      password: form.password,
    })
    ElMessage.success('注册成功，请登录')
    router.push('/login')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '注册失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.register-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #9a6b04 0%, #c88a04 50%, #e6a817 100%);
}
.register-card {
  width: 420px;
  background: #fff;
  border-radius: var(--radius-lg);
  padding: var(--spacing-2xl);
  box-shadow: 0 8px 32px rgba(0,0,0,.15);
}
.register-header { text-align: center; margin-bottom: var(--spacing-lg); }
.register-icon {
  width: 56px; height: 56px; border-radius: 50%;
  background: var(--color-primary);
  color: #fff; font-size: 28px; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
  margin: 0 auto var(--spacing-md);
}
.register-header h2 { font-size: 20px; margin: 0 0 4px; }
.register-header p { font-size: 13px; color: var(--color-text-secondary); margin: 0; }
.register-btn { width: 100%; }
.register-footer {
  margin-top: var(--spacing-md);
  text-align: center;
  font-size: 13px;
  color: var(--color-text-secondary);
}
.register-footer a { color: var(--color-primary); }
</style>
