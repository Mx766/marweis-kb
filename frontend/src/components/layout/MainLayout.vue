<template>
  <div class="main-layout">
    <AppHeader />
    <WorkflowSidebar v-if="showSidebar && !auth.isSuperAdmin" />
    <DeptNavBars v-if="showDeptBars" />
    <main class="main-content" :class="{ 'with-nav': showSidebar, 'admin-view': showDeptBars }">
      <div class="content-wrapper">
        <router-view />
      </div>
    </main>
    <MobileTabBar />
    <AppFooter />
  </div>
</template>

<script setup lang="ts">
// v2 - admin dept bars
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AppHeader from './AppHeader.vue'
import AppFooter from './AppFooter.vue'
import WorkflowSidebar from './WorkflowSidebar.vue'
import DeptNavBars from './DeptNavBars.vue'
import MobileTabBar from './MobileTabBar.vue'
import { useAuthStore } from '@/stores/auth'
import { DEPARTMENTS } from '@/utils/departments'
import { onMounted } from 'vue'

const auth = useAuthStore()
const route = useRoute()
onMounted(() => auth.fetchMe())

const showSidebar = computed(() => {
  if (auth.isSuperAdmin) return false  // 超管用 DeptNavBars；部门管理员走本部门侧边栏
  const dept = auth.user?.department
  return dept ? DEPARTMENTS.includes(dept) : false
})

// Only show DeptNavBars on knowledge-base pages, not on files/admin/etc
const showDeptBars = computed(() => {
  if (!auth.isSuperAdmin) return false
  const name = route.name as string || ''
  const path = route.path
  // Hide on admin, login, personal pages (show on files for department context)
  if (name.startsWith('Admin') || path.startsWith('/admin') || path.startsWith('/files')) return false
  if (path === '/login' || path === '/personal') return false
  return true
})
</script>

<style scoped>
.main-layout {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}
.main-content {
  flex: 1;
  padding-top: 56px;
}
.main-content.with-nav {
  padding-top: 126px; /* 56px header + 70px navbar (2-row wrap) */
}
.main-content.admin-view {
  padding-top: 0; /* DeptNavBars is in normal flow, already pushes content down */
}
.content-wrapper {
  max-width: 1300px;
  margin: 0 auto;
  padding: var(--spacing-lg);
}
.has-sidebar .content-wrapper {
  max-width: none;
}

@media (max-width: 768px) {
  .main-content {
    padding-bottom: 56px; /* room for mobile tab bar */
  }
  .main-content.with-nav {
    padding-top: 102px; /* 56px header + 46px single-row navbar */
  }
  .main-content.admin-view {
    padding-top: 0; /* DeptNavBars is in normal flow with its own top padding */
  }
  .content-wrapper {
    padding: 12px 14px;
  }
}
</style>
