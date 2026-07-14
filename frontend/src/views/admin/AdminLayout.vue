<template>
  <div class="admin-layout">
    <!-- 横向导航栏 -->
    <header class="admin-topbar">
      <div class="topbar-inner">
        <router-link to="/" class="topbar-brand">
          <div class="brand-icon">M</div>
          <span class="brand-text">管理后台</span>
        </router-link>

        <el-menu
          mode="horizontal"
          :default-active="activeMenu"
          class="topbar-nav"
          router
          :ellipsis="false"
        >
          <el-menu-item index="/admin/documents">
            <el-icon><Document /></el-icon>
            <span>文档管理</span>
          </el-menu-item>
          <el-menu-item index="/admin/categories">
            <el-icon><Folder /></el-icon>
            <span>分类管理</span>
          </el-menu-item>
          <el-menu-item index="/admin/users">
            <el-icon><User /></el-icon>
            <span>用户管理</span>
          </el-menu-item>
          <el-menu-item index="/admin/settings">
            <el-icon><Setting /></el-icon>
            <span>系统设置</span>
          </el-menu-item>
        </el-menu>

        <div class="topbar-right">
          <el-button size="small" @click="$router.push('/')">返回前台</el-button>
        </div>
      </div>
    </header>

    <!-- 内容区 -->
    <main class="admin-main">
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { Document, Folder, User, Setting } from '@element-plus/icons-vue'

const route = useRoute()
const activeMenu = computed(() => route.path)
</script>

<style scoped>
.admin-layout {
  min-height: 100vh;
  background: var(--color-bg-secondary);
}

/* ── 横向导航栏 ── */
.admin-topbar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 56px;
  background: #fff;
  border-bottom: 1px solid var(--color-border);
  z-index: 999;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}

.topbar-inner {
  display: flex;
  align-items: center;
  height: 100%;
  padding: 0 var(--spacing-lg);
  gap: var(--spacing-md);
}

.topbar-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
  text-decoration: none;
}

.brand-icon {
  width: 32px;
  height: 32px;
  background: var(--color-primary);
  color: #fff;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 15px;
}

.brand-text {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
}

/* ── 横向菜单 ── */
.topbar-nav {
  flex: 1;
  border-bottom: none !important;
  background: transparent;
}

.topbar-nav .el-menu-item {
  height: 56px;
  line-height: 56px;
  font-size: 13px;
  color: var(--color-text-secondary);
}

.topbar-nav .el-menu-item:hover {
  color: var(--color-primary);
  background: rgba(30, 80, 174, 0.04);
}

.topbar-nav .el-menu-item.is-active {
  color: var(--color-primary) !important;
  border-bottom: 2px solid var(--color-primary) !important;
  font-weight: 600;
}

.topbar-right {
  flex-shrink: 0;
}

/* ── 内容区 ── */
.admin-main {
  padding-top: 56px;
  min-height: 100vh;
}
</style>
