<template>
  <div class="main-layout">
    <AppHeader />
    <WorkflowSidebar v-if="showSidebar" />
    <main class="main-content" :class="{ 'with-nav': showSidebar }">
      <div class="content-wrapper">
        <router-view />
      </div>
    </main>
    <AppFooter />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import AppHeader from './AppHeader.vue'
import AppFooter from './AppFooter.vue'
import WorkflowSidebar from './WorkflowSidebar.vue'
import { useAuthStore } from '@/stores/auth'
import { onMounted } from 'vue'

const auth = useAuthStore()
onMounted(() => auth.fetchMe())

const WORKFLOW_DEPTS = ['器械注册部', '临床评价部', '临床试验部', '生产体系部', '化妆品·医美部', '特医食品部', '管理层']
const showSidebar = computed(() => {
  if (auth.isAdmin) return true
  const dept = auth.user?.department
  return dept ? WORKFLOW_DEPTS.includes(dept) : false
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
  padding-top: 60px;
}
.main-content.with-nav {
  padding-top: 108px; /* 60px header + 48px navbar */
}
.content-wrapper {
  max-width: 1300px;
  margin: 0 auto;
  padding: var(--spacing-lg);
}
.has-sidebar .content-wrapper {
  max-width: none;
}
</style>
