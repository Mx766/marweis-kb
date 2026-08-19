<template>
  <nav class="mobile-tab-bar">
    <router-link to="/" class="mtab" :class="{ active: isHome }">
      <el-icon :size="20"><HomeFilled /></el-icon>
      <span>首页</span>
    </router-link>
    <router-link to="/files" class="mtab" :class="{ active: isFiles }">
      <el-icon :size="20"><FolderOpened /></el-icon>
      <span>公盘</span>
    </router-link>
    <router-link to="/oa" class="mtab" :class="{ active: isOa }">
      <el-icon :size="20"><Files /></el-icon>
      <span>OA</span>
    </router-link>
    <router-link to="/personal" class="mtab" :class="{ active: isPersonal }">
      <el-icon :size="20"><User /></el-icon>
      <span>我的</span>
    </router-link>
    <router-link v-if="auth.isAdmin" to="/admin" class="mtab" :class="{ active: isAdmin }">
      <el-icon :size="20"><Setting /></el-icon>
      <span>后台</span>
    </router-link>
  </nav>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { HomeFilled, FolderOpened, Files, User, Setting } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const auth = useAuthStore()

const isHome = computed(() => route.path === '/')
const isFiles = computed(() => route.path.startsWith('/files'))
const isOa = computed(() => route.path.startsWith('/oa'))
const isPersonal = computed(() => route.path.startsWith('/personal'))
const isAdmin = computed(() => route.path.startsWith('/admin'))
</script>

<style scoped>
.mobile-tab-bar {
  display: none;
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 999;
  height: 56px;
  background: rgba(255, 255, 255, .96);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-top: 1px solid rgba(0, 0, 0, .06);
  box-shadow: 0 -2px 12px rgba(0, 0, 0, .04);
}

@media (max-width: 768px) {
  .mobile-tab-bar {
    display: flex;
    align-items: stretch;
  }
}

.mtab {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  color: #8a93a3;
  font-size: 10px;
  text-decoration: none;
  -webkit-tap-highlight-color: transparent;
  transition: color .15s;
}
.mtab .el-icon {
  transition: transform .15s;
}
.mtab.active {
  color: var(--color-primary);
  font-weight: 600;
}
.mtab.active .el-icon {
  transform: translateY(-1px);
}
.mtab:active {
  color: var(--color-primary);
}
</style>
