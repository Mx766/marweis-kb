<template>
  <header class="app-header">
    <div class="header-inner">
      <router-link to="/" class="logo-section">
        <div class="logo-icon">M</div>
        <div class="logo-text">
          <span class="logo-title">迈瑞生知识库</span>
          <span class="logo-subtitle">Marweis Knowledge Base</span>
        </div>
      </router-link>

      <el-menu
        mode="horizontal"
        :default-active="activeMenu"
        class="header-nav"
        :ellipsis="false"
        @select="handleMenuSelect"
      >
        <el-menu-item index="/">首页</el-menu-item>
        <el-menu-item index="/category">知识库</el-menu-item>
        <el-menu-item v-if="auth.isAdmin" index="/admin">管理后台</el-menu-item>
      </el-menu>

      <div class="header-right">
        <el-input
          v-model="searchText"
          placeholder="搜索文档..."
          :prefix-icon="SearchIcon"
          class="header-search"
          size="default"
          @keyup.enter="doSearch"
        />
        <template v-if="auth.isLoggedIn">
          <el-dropdown>
            <span class="user-info">
              <el-avatar :size="32" style="background: var(--color-primary)">{{ auth.user?.display_name?.charAt(0) }}</el-avatar>
              <span class="user-name">{{ auth.user?.display_name }}</span>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="$router.push('/personal')">个人工作台</el-dropdown-item>
                <el-dropdown-item divided @click="auth.logout()">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </template>
        <template v-else>
          <el-button type="primary" size="default" @click="$router.push('/login')">登录</el-button>
        </template>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Search as SearchIcon } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const searchText = ref('')

const activeMenu = computed(() => {
  if (route.path.startsWith('/admin')) return '/admin'
  if (route.path.startsWith('/category') || route.path.startsWith('/document')) return '/category'
  return '/'
})

function handleMenuSelect(index: string) {
  router.push(index)
}

function doSearch() {
  if (searchText.value.trim()) {
    router.push({ path: '/search', query: { q: searchText.value.trim() } })
  }
}
</script>

<style scoped>
.app-header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 60px;
  background: #fff;
  border-bottom: 1px solid var(--color-border);
  z-index: 1000;
  box-shadow: 0 1px 4px rgba(0,0,0,.04);
}
.header-inner {
  max-width: 1300px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  height: 100%;
  padding: 0 var(--spacing-lg);
  gap: var(--spacing-lg);
}
.logo-section {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}
.logo-icon {
  width: 36px; height: 36px;
  background: var(--color-primary);
  color: #fff;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 18px;
}
.logo-text { display: flex; flex-direction: column; }
.logo-title { font-size: 15px; font-weight: 600; color: var(--color-text-primary); white-space: nowrap; }
.logo-subtitle { font-size: 11px; color: var(--color-text-secondary); }
.header-nav { flex: 1; border-bottom: none !important; }
.header-nav .el-menu-item { height: 60px; line-height: 60px; }
.header-nav .el-menu-item.is-active { color: var(--color-accent) !important; border-bottom-color: var(--color-accent) !important; }
.header-right { display: flex; align-items: center; gap: var(--spacing-md); }
.header-search { width: 240px; }
.user-info { display: flex; align-items: center; gap: 8px; cursor: pointer; }
.user-name { font-size: 13px; color: var(--color-text-primary); }
</style>
