<template>
  <div class="main-layout">
    <AppHeader />
    <main class="main-content">
      <div class="content-wrapper">
        <router-view />
      </div>
    </main>
    <AppFooter />
  </div>
</template>

<script setup lang="ts">
import AppHeader from './AppHeader.vue'
import AppFooter from './AppFooter.vue'
import { useAuthStore } from '@/stores/auth'
import { onMounted } from 'vue'

const auth = useAuthStore()
onMounted(() => auth.fetchMe())
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
.content-wrapper {
  max-width: 1300px;
  margin: 0 auto;
  padding: var(--spacing-lg);
}
</style>
