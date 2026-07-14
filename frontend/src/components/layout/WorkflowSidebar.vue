<template>
  <aside class="workflow-sidebar">
    <div class="sidebar-header">
      <div class="dept-icon">M</div>
      <div class="dept-info">
        <span class="dept-name">器械注册部</span>
        <span class="dept-label">工作台</span>
      </div>
    </div>

    <div class="sidebar-nav">
      <div
        v-for="mod in modules"
        :key="mod.id"
        class="nav-module"
        :class="{ active: isActive(mod) }"
      >
        <!-- Module header -->
        <div class="module-header">
          <el-icon
            class="module-arrow"
            :class="{ expanded: expandedModules.has(mod.id) }"
            @click.stop="toggleExpand(mod)"
            v-if="mod.children?.length"
          >
            <ArrowRight />
          </el-icon>
          <span
            class="module-label"
            @click="navigateToModule(mod)"
          >
            <el-icon class="module-icon"><Folder /></el-icon>
            <span class="module-name">{{ cleanName(mod.name) }}</span>
          </span>
        </div>

        <!-- Sub-categories -->
        <div v-if="mod.children?.length && expandedModules.has(mod.id)" class="module-children">
          <div
            v-for="sub in mod.children"
            :key="sub.id"
            class="sub-item"
            :class="{ active: activeModuleId === sub.id }"
            @click="selectSub(sub.id)"
          >
            {{ sub.name }}
          </div>
        </div>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Folder, ArrowRight } from '@element-plus/icons-vue'
import { get } from '@/api/client'
import type { CategoryNode } from '@/api/client'

const route = useRoute()
const router = useRouter()
const modules = ref<CategoryNode[]>([])
const expandedModules = ref(new Set<string>())

const activeModuleId = computed(() => {
  return (route.params.moduleId as string) || (route.params.categoryId as string) || ''
})

onMounted(async () => {
  try {
    const cats: CategoryNode[] = await get('/api/categories')
    // Filter: only show categories that have children or have workflow-like structure
    modules.value = cats
      .filter(c => c.children?.length > 0 || c.name.startsWith('1.') || c.name.startsWith('2.') || c.name.startsWith('3.') || c.name.startsWith('4.') || c.name.startsWith('5.') || c.name.startsWith('6.') || c.name.startsWith('7.'))
      .sort((a, b) => a.sort_order - b.sort_order)
    // Auto-expand the module containing the active category
    for (const mod of modules.value) {
      if (mod.children?.some(s => s.id === activeModuleId.value)) {
        expandedModules.value.add(mod.id)
      }
    }
  } catch {
    modules.value = []
  }
})

function cleanName(name: string) {
  return name.replace(/^\d+\.\s*/, '')
}

function isActive(mod: CategoryNode) {
  if (activeModuleId.value === mod.id) return true
  return mod.children?.some(s => s.id === activeModuleId.value) || false
}

function toggleExpand(mod: CategoryNode) {
  if (expandedModules.value.has(mod.id)) {
    expandedModules.value.delete(mod.id)
  } else {
    expandedModules.value.add(mod.id)
  }
}

function navigateToModule(mod: CategoryNode) {
  router.push(`/category/${mod.id}`)
}

function selectSub(subId: string) {
  router.push(`/category/${subId}`)
}
</script>

<style scoped>
.workflow-sidebar {
  width: 220px;
  min-height: calc(100vh - 60px);
  background: #1e293b;
  position: fixed;
  left: 0;
  top: 60px;
  bottom: 0;
  overflow-y: auto;
  z-index: 100;
  display: flex;
  flex-direction: column;
}
.sidebar-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 16px 20px;
  border-bottom: 1px solid #334155;
}
.dept-icon {
  width: 36px; height: 36px;
  background: #c88a04;
  color: #fff;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 16px;
  flex-shrink: 0;
}
.dept-info { display: flex; flex-direction: column; }
.dept-name { font-size: 14px; font-weight: 600; color: #e2e8f0; }
.dept-label { font-size: 11px; color: #94a3b8; }
.sidebar-nav { flex: 1; padding: 8px 0; }

.nav-module { margin: 2px 8px; border-radius: 6px; overflow: hidden; }
.nav-module.active { background: #334155; }
.module-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  cursor: pointer;
  border-radius: 6px;
  color: #cbd5e1;
  font-size: 13px;
  transition: all .15s;
}
.module-header:hover { background: #334155; color: #f1f5f9; }
.nav-module.active .module-header { color: #f1f5f9; }
.module-arrow { font-size: 10px; transition: transform .2s; color: #64748b; flex-shrink: 0; width: 12px; }
.module-arrow.expanded { transform: rotate(90deg); }
.module-label {
  display: flex; align-items: center; gap: 8px; flex: 1;
  cursor: pointer; padding: 10px 0;
}
.module-icon { font-size: 16px; color: #e6a817; flex-shrink: 0; }
.module-name { flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

.module-children { }
.sub-item {
  padding: 7px 12px 7px 48px;
  font-size: 12px;
  color: #94a3b8;
  cursor: pointer;
  border-radius: 4px;
  margin: 1px 4px;
  transition: all .15s;
}
.sub-item:hover { color: #e2e8f0; background: #334155; }
.sub-item.active { color: #f5c518; background: #3d2e00; }
</style>
