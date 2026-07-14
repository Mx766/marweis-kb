<template>
  <header class="app-header">
    <div class="header-inner">
      <!-- Logo -->
      <router-link to="/" class="logo-section">
        <div class="logo-icon">M</div>
        <div class="logo-text">
          <span class="logo-title">迈瑞生知识库</span>
          <span class="logo-subtitle">Marweis KB</span>
        </div>
      </router-link>

      <!-- Main nav -->
      <nav class="header-nav">
        <router-link to="/" class="nav-link" :class="{ active: isHome }">首页</router-link>
        <router-link
          v-if="auth.isAdmin"
          to="/admin"
          class="nav-link"
          :class="{ active: isAdmin }"
        >管理后台</router-link>
      </nav>

      <!-- Right area -->
      <div class="header-right">
        <!-- Search -->
        <div class="header-search" :class="{ focused: searchFocused }">
          <el-icon class="search-icon" :size="15"><Search /></el-icon>
          <input
            v-model="searchText"
            type="text"
            placeholder="搜索文档..."
            class="search-input"
            @focus="searchFocused = true"
            @blur="searchFocused = false"
            @keydown.escape="searchText = ''; searchFocused = false"
            @keyup.enter="doSearch"
          />
          <span v-if="searchText" class="search-shortcut" @click="doSearch">↵</span>
          <span v-else class="search-shortcut hint">⌘K</span>
        </div>

        <!-- User area -->
        <template v-if="auth.isLoggedIn">
          <el-dropdown trigger="click" popper-class="user-dropdown-popper">
            <div class="user-trigger">
              <div class="user-avatar">{{ auth.user?.display_name?.charAt(0) }}</div>
              <span class="user-name">{{ auth.user?.display_name }}</span>
              <el-icon class="user-arrow" :size="12"><ArrowDown /></el-icon>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <div class="dropdown-user-info">
                  <div class="dropdown-avatar">{{ auth.user?.display_name?.charAt(0) }}</div>
                  <div>
                    <div class="dropdown-name">{{ auth.user?.display_name }}</div>
                    <div class="dropdown-dept">{{ auth.user?.department }} · {{ roleLabel }}</div>
                  </div>
                </div>
                <el-dropdown-item divided @click="$router.push('/personal')">
                  <el-icon><User /></el-icon> 个人工作台
                </el-dropdown-item>
                <el-dropdown-item divided @click="auth.logout()">
                  <el-icon><SwitchButton /></el-icon> 退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </template>
        <template v-else>
          <el-button type="primary" size="default" @click="$router.push('/login')" round>登录</el-button>
        </template>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Search, ArrowDown, User, SwitchButton } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const searchText = ref('')
const searchFocused = ref(false)

const isHome = computed(() => route.path === '/')
const isAdmin = computed(() => route.path.startsWith('/admin'))

const roleLabel = computed(() => {
  const map: Record<string, string> = {
    super_admin: '超级管理员', dept_admin: '部门管理员',
    editor: '编辑者', employee: '员工', guest: '访客',
  }
  return map[auth.user?.role || ''] || ''
})

function doSearch() {
  if (searchText.value.trim()) {
    router.push({ path: '/search', query: { q: searchText.value.trim() } })
  }
}
</script>

<style scoped>
/* ── Header ── */
.app-header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 56px;
  background: rgba(255, 255, 255, .92);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(0, 0, 0, .06);
  z-index: 1000;
}

.header-inner {
  display: flex;
  align-items: center;
  height: 100%;
  padding: 0 20px;
  gap: 24px;
  max-width: 1400px;
  margin: 0 auto;
}

/* ── Logo ── */
.logo-section {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}
.logo-icon {
  width: 32px;
  height: 32px;
  background: var(--color-primary);
  color: #fff;
  border-radius: 7px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 16px;
  letter-spacing: .5px;
}
.logo-text {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}
.logo-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--color-text-primary);
  white-space: nowrap;
  letter-spacing: .3px;
}
.logo-subtitle {
  font-size: 10px;
  color: var(--color-text-secondary);
  font-weight: 500;
  letter-spacing: .5px;
}

/* ── Nav ── */
.header-nav {
  display: flex;
  align-items: center;
  gap: 4px;
  flex: 1;
}
.nav-link {
  padding: 6px 14px;
  border-radius: 7px;
  font-size: 13px;
  color: #5a6270;
  font-weight: 500;
  transition: all .15s ease;
}
.nav-link:hover {
  background: rgba(30, 80, 174, .05);
  color: var(--color-primary);
}
.nav-link.active {
  color: var(--color-primary);
  font-weight: 600;
  background: rgba(30, 80, 174, .07);
}

/* ── Search ── */
.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}
.header-search {
  display: flex;
  align-items: center;
  gap: 6px;
  background: #f2f4f7;
  border: 1.5px solid transparent;
  border-radius: 10px;
  padding: 0 10px;
  width: 220px;
  height: 36px;
  transition: all .2s ease;
}
.header-search.focused {
  background: #fff;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(30, 80, 174, .07);
  width: 280px;
}
.search-icon {
  color: var(--color-text-secondary);
  flex-shrink: 0;
}
.search-input {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  font-size: 12.5px;
  color: var(--color-text-primary);
  font-family: inherit;
}
.search-input::placeholder {
  color: #b0b8c4;
}
.search-shortcut {
  font-size: 10px;
  color: #c0c8d4;
  background: #e8ecf2;
  padding: 2px 5px;
  border-radius: 3px;
  font-weight: 600;
  cursor: pointer;
  flex-shrink: 0;
}
.search-shortcut.hint {
  letter-spacing: 1px;
  font-size: 9px;
}

/* ── User ── */
.user-trigger {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 8px;
  transition: background .12s;
}
.user-trigger:hover {
  background: #f2f4f7;
}
.user-avatar {
  width: 30px;
  height: 30px;
  border-radius: 7px;
  background: var(--color-primary);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 700;
}
.user-name {
  font-size: 13px;
  color: var(--color-text-primary);
  font-weight: 500;
  max-width: 80px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.user-arrow {
  color: var(--color-text-secondary);
}

@media (max-width: 768px) {
  .logo-subtitle { display: none; }
  .nav-link { font-size: 12px; padding: 6px 10px; }
  .header-search { width: 140px; }
  .header-search.focused { width: 180px; }
  .user-name { display: none; }
}
</style>

<!-- Global dropdown styles (unscoped) -->
<style>
.user-dropdown-popper {
  border-radius: 12px !important;
  box-shadow: 0 12px 32px rgba(0,0,0,.1), 0 2px 8px rgba(0,0,0,.04) !important;
  border: 1px solid #eee !important;
  overflow: hidden;
}
.user-dropdown-popper .el-dropdown-menu {
  padding: 4px;
}
.user-dropdown-popper .el-dropdown-menu__item {
  border-radius: 6px;
  font-size: 13px;
  padding: 8px 12px;
}

.dropdown-user-info {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px 8px;
}
.dropdown-avatar {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: var(--color-primary);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 15px;
  font-weight: 700;
  flex-shrink: 0;
}
.dropdown-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-primary);
}
.dropdown-dept {
  font-size: 11px;
  color: var(--color-text-secondary);
  margin-top: 1px;
}
</style>
