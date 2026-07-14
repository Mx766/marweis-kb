<template>
  <aside class="workflow-sidebar">
    <div class="sidebar-title">器械注册工作台</div>
    <el-menu
      :default-active="activeModuleId"
      class="workflow-menu"
      @select="handleSelect"
    >
      <template v-for="mod in modules" :key="mod.id">
        <!-- 有子分类：可展开 -->
        <el-sub-menu v-if="mod.children?.length" :index="mod.id">
          <template #title>
            <el-icon><Folder /></el-icon>
            <span>{{ mod.name }}</span>
          </template>
          <el-menu-item
            v-for="sub in mod.children"
            :key="sub.id"
            :index="sub.id"
          >
            {{ sub.name }}
          </el-menu-item>
        </el-sub-menu>
        <!-- 无子分类：直接点击 -->
        <el-menu-item v-else :index="mod.id">
          <el-icon><Folder /></el-icon>
          <span>{{ mod.name }}</span>
        </el-menu-item>
      </template>
    </el-menu>
  </aside>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Folder } from '@element-plus/icons-vue'
import { get } from '@/api/client'
import type { CategoryNode } from '@/api/client'

const route = useRoute()
const router = useRouter()
const modules = ref<CategoryNode[]>([])

const activeModuleId = computed(() => {
  const id = route.params.moduleId as string || route.params.categoryId as string
  return id || ''
})

onMounted(async () => {
  try {
    const cats: CategoryNode[] = await get('/api/categories')
    modules.value = cats
      .filter(c => c.children?.length > 0 || !c.parent_id)
      .sort((a, b) => a.sort_order - b.sort_order)
  } catch {
    modules.value = []
  }
})

// Watch route changes to sync active state
watch(() => route.params, () => {}, { deep: true })

function handleSelect(catId: string) {
  const module = modules.value.find(m => m.id === catId)
  if (module) {
    // Top-level module click: show module page
    router.push(`/category/${catId}`)
  } else {
    // Sub-category click: find parent module
    for (const mod of modules.value) {
      const sub = mod.children?.find(s => s.id === catId)
      if (sub) {
        router.push(`/category/${catId}`)
        return
      }
    }
  }
}
</script>

<style scoped>
.workflow-sidebar {
  width: 220px;
  min-height: calc(100vh - 60px);
  background: #fff;
  border-right: 1px solid #e8e8e8;
  position: fixed;
  left: 0;
  top: 60px;
  bottom: 0;
  overflow-y: auto;
  z-index: 100;
}
.sidebar-title {
  padding: 16px 20px 8px;
  font-size: 13px;
  color: #999;
  text-transform: uppercase;
  letter-spacing: 1px;
}
.workflow-menu {
  border-right: none;
}
.workflow-menu .el-menu-item {
  height: 40px;
  line-height: 40px;
  font-size: 14px;
}
.workflow-menu .el-sub-menu .el-menu-item {
  padding-left: 52px !important;
  font-size: 13px;
}
</style>
