<template>
  <div class="main-layout" :class="{ 'has-sidebar': showSidebar }">
    <AppHeader />
    <WorkflowSidebar v-if="showSidebar" />
    <main class="main-content" :class="{ 'with-sidebar': showSidebar }">
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

const WORKFLOW_DEPTS = ['器械注册部']
const showSidebar = computed(() => {
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
.main-content.with-sidebar {
  margin-left: 220px;
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
