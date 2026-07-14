<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-header">
        <div class="login-icon">M</div>
        <h2>迈瑞生知识库</h2>
        <p>Marweis Knowledge Base</p>
      </div>
      <el-form @submit.prevent="handleLogin" :model="form" :rules="rules" ref="formRef">
        <el-form-item prop="username">
          <el-input v-model="form.username" placeholder="用户名" size="large" />
        </el-form-item>
        <el-form-item prop="password">
          <el-input v-model="form.password" type="password" placeholder="密码" size="large" show-password />
        </el-form-item>
        <el-button type="primary" native-type="submit" size="large" :loading="loading" class="login-btn">
          登 录
        </el-button>
      </el-form>
      <div class="login-hint">
        <p>没有账号？<router-link to="/register">立即注册</router-link></p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { ElMessage } from 'element-plus'

const auth = useAuthStore()
const loading = ref(false)
const formRef = ref()
const form = reactive({ username: '', password: '' })
const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function handleLogin() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  try {
    await auth.login(form.username, form.password)
    ElMessage.success('登录成功')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1e50ae 0%, #3a6fc4 50%, #667eea 100%);
}
.login-card {
  width: 400px;
  background: #fff;
  border-radius: var(--radius-lg);
  padding: var(--spacing-2xl);
  box-shadow: 0 8px 32px rgba(0,0,0,.15);
}
.login-header { text-align: center; margin-bottom: var(--spacing-xl); }
.login-icon {
  width: 56px; height: 56px; border-radius: 50%;
  background: var(--color-primary);
  color: #fff; font-size: 28px; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
  margin: 0 auto var(--spacing-md);
}
.login-header h2 { font-size: 20px; margin: 0 0 4px; }
.login-header p { font-size: 13px; color: var(--color-text-secondary); margin: 0; }
.login-btn { width: 100%; }
.login-hint {
  margin-top: var(--spacing-lg);
  padding: var(--spacing-md);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-sm);
  font-size: 12px; color: var(--color-text-secondary); text-align: center;
}
.login-hint p { margin: 2px 0; }
</style>
