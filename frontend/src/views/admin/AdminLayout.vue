<template>
  <div class="admin-layout">
    <el-container>
      <el-aside width="200px">
        <div class="admin-logo">
          <router-link to="/">
            <strong>管理后台</strong>
          </router-link>
        </div>
        <el-menu :default-active="activeMenu" router>
          <el-menu-item index="/admin/documents">
            <el-icon><Document /></el-icon> 文档管理
          </el-menu-item>
          <el-menu-item index="/admin/categories">
            <el-icon><Folder /></el-icon> 分类管理
          </el-menu-item>
          <el-menu-item index="/admin/users">
            <el-icon><User /></el-icon> 用户管理
          </el-menu-item>
          <el-menu-item index="/admin/settings">
            <el-icon><Setting /></el-icon> 系统设置
          </el-menu-item>
        </el-menu>
      </el-aside>
      <el-container>
        <el-header class="admin-header">
          <span>{{ pageTitle }}</span>
          <div>
            <el-button size="small" @click="$router.push('/')">返回前台</el-button>
          </div>
        </el-header>
        <el-main>
          <router-view />
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { Document, Folder, User, Setting } from '@element-plus/icons-vue'

const route = useRoute()
const activeMenu = computed(() => route.path)
const pageTitle = computed(() => {
  const m: Record<string, string> = {
    '/admin/documents': '文档管理',
    '/admin/categories': '分类管理',
    '/admin/users': '用户管理',
    '/admin/settings': '系统设置',
  }
  return m[route.path] || '管理后台'
})
</script>

<style scoped>
.admin-layout { min-height: 100vh; }
.el-aside { background: #304156; min-height: 100vh; }
.admin-logo { padding: 16px 20px; }
.admin-logo a { color: #fff; font-size: 15px; }
.el-menu { border-right: none; background: transparent; }
.el-menu .el-menu-item { color: #bfcbd9; }
.el-menu .el-menu-item:hover { background: rgba(255,255,255,.05); color: #fff; }
.el-menu .el-menu-item.is-active { color: #ffc001; }
.admin-header { display: flex; align-items: center; justify-content: space-between; background: #fff; border-bottom: 1px solid var(--color-border); font-size: 15px; font-weight: 500; }
</style>
