<template>
  <nav class="workflow-navbar" v-if="modules.length">
    <div class="navbar-inner">
      <!-- Department badge -->
      <div class="dept-badge" :style="{ background: deptConfig.color }">
        <span class="dept-badge-icon">{{ deptConfig.icon }}</span>
        <span class="dept-badge-text">{{ deptName }}</span>
      </div>

      <!-- Module items -->
      <div class="navbar-modules">
        <div
          v-for="mod in modules"
          :key="mod.id"
          class="nav-item"
          :class="{ active: isActive(mod) }"
          @mouseenter="showDropdown(mod)"
          @mouseleave="startLeaveTimer(mod)"
        >
          <div class="nav-item-label" @click="navigateToModule(mod)">
            <el-icon class="nav-item-icon"><Folder /></el-icon>
            <span>{{ cleanName(mod.name) }}</span>
            <el-icon v-if="mod.children?.length" class="nav-item-arrow"><ArrowDown /></el-icon>
          </div>

          <!-- Dropdown panel -->
          <div
            v-if="mod.children?.length && hoveredModule === mod.id"
            class="nav-dropdown"
            @mouseenter="clearLeaveTimer"
            @mouseleave="startLeaveTimer(mod)"
          >
            <div
              v-for="sub in mod.children"
              :key="sub.id"
              class="dropdown-item"
              :class="{ active: activeModuleId === sub.id }"
              @click="selectSub(sub.id)"
            >
              <span>{{ sub.name }}</span>
              <span class="dropdown-item-count" v-if="sub.document_count">({{ sub.document_count }})</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </nav>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Folder, ArrowDown } from '@element-plus/icons-vue'
import { get } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import type { CategoryNode } from '@/api/client'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const modules = ref<CategoryNode[]>([])
const hoveredModule = ref('')
let _leaveTimer: ReturnType<typeof setTimeout> | null = null

// Department config: icon, label, color, accent
const DEPT_CONFIG: Record<string, { icon: string; label: string; color: string; accentColor: string }> = {
  '器械注册部':   { icon: 'M', label: '工作台',     color: '#1e50ae', accentColor: '#ffc001' },
  '临床评价部':   { icon: 'C', label: 'CER工作台',  color: '#2e86c1', accentColor: '#5dade2' },
  '临床试验部':   { icon: 'T', label: 'CRO工作台',  color: '#27ae60', accentColor: '#58d68d' },
  '生产体系部':   { icon: 'Q', label: '质量工作台', color: '#8e44ad', accentColor: '#af7ac5' },
  '化妆品·医美部': { icon: 'B', label: '美妆工作台', color: '#e74c3c', accentColor: '#f1948a' },
  '特医食品部':   { icon: 'F', label: '食品工作台', color: '#fb8c00', accentColor: '#f8c471' },
  '管理层':       { icon: 'A', label: '管理驾驶舱', color: '#333333', accentColor: '#9e9e9e' },
}

const deptConfig = computed(() => {
  const dept = auth.user?.department || ''
  if (auth.isAdmin) return DEPT_CONFIG['器械注册部']
  return DEPT_CONFIG[dept] || DEPT_CONFIG['器械注册部']
})

const deptName = computed(() => {
  if (auth.isAdmin) return '器械注册部'
  return auth.user?.department || '器械注册部'
})

const activeModuleId = computed(() => {
  return (route.params.moduleId as string) || (route.params.categoryId as string) || ''
})

onMounted(async () => {
  try {
    const cats: CategoryNode[] = await get('/api/categories')
    const publicZone = cats.filter(c => c.name === '公共知识区')
    const deptCats = cats.filter(c => c.name !== '公共知识区')
    const numberedModules = deptCats.filter(c => /^\d+\./.test(c.name))
    if (numberedModules.length > 0) {
      modules.value = [...numberedModules, ...publicZone].sort((a, b) => a.sort_order - b.sort_order)
    } else {
      modules.value = [...deptCats, ...publicZone].sort((a, b) => a.sort_order - b.sort_order)
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

function showDropdown(mod: CategoryNode) {
  clearLeaveTimer()
  hoveredModule.value = mod.id
}

function startLeaveTimer(_mod: CategoryNode) {
  _leaveTimer = setTimeout(() => {
    hoveredModule.value = ''
  }, 200)
}

function clearLeaveTimer() {
  if (_leaveTimer) { clearTimeout(_leaveTimer); _leaveTimer = null }
}

function navigateToModule(mod: CategoryNode) {
  hoveredModule.value = ''
  router.push(`/category/${mod.id}`)
}

function selectSub(subId: string) {
  hoveredModule.value = ''
  router.push(`/category/${subId}`)
}
</script>

<style scoped>
.workflow-navbar {
  background: #fff;
  border-bottom: 1px solid var(--color-border);
  position: fixed;
  top: 60px;
  left: 0;
  right: 0;
  height: 48px;
  z-index: 99;
  box-shadow: 0 1px 3px rgba(0,0,0,.04);
}

.navbar-inner {
  display: flex;
  align-items: center;
  height: 100%;
  padding: 0 var(--spacing-lg);
  gap: 4px;
}

/* ── Department badge ── */
.dept-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 14px 4px 8px;
  border-radius: 6px;
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  flex-shrink: 0;
  margin-right: 8px;
}
.dept-badge-icon {
  width: 26px; height: 26px;
  background: rgba(255,255,255,.25);
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
}
.dept-badge-text { white-space: nowrap; }

/* ── Module items ── */
.navbar-modules {
  display: flex;
  align-items: center;
  height: 100%;
  gap: 2px;
  flex: 1;
  overflow-x: auto;
}

.nav-item {
  position: relative;
  height: 100%;
  display: flex;
  align-items: center;
}

.nav-item-label {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 13px;
  color: var(--color-text-primary);
  cursor: pointer;
  white-space: nowrap;
  transition: all .15s;
}
.nav-item-label:hover { background: var(--color-bg-secondary); color: var(--color-primary); }
.nav-item.active .nav-item-label {
  color: var(--color-primary);
  font-weight: 600;
}
.nav-item-icon { font-size: 15px; color: var(--color-text-secondary); }
.nav-item.active .nav-item-icon { color: var(--color-primary); }
.nav-item-arrow { font-size: 10px; color: var(--color-text-secondary); transition: transform .2s; }

/* ── Dropdown ── */
.nav-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  min-width: 180px;
  background: #fff;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: 0 8px 24px rgba(0,0,0,.1);
  padding: 6px;
  z-index: 200;
}

.dropdown-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 14px;
  font-size: 13px;
  color: var(--color-text-primary);
  border-radius: 4px;
  cursor: pointer;
  white-space: nowrap;
  transition: all .12s;
}
.dropdown-item:hover { background: var(--color-bg-secondary); color: var(--color-primary); }
.dropdown-item.active { color: var(--color-primary); font-weight: 600; background: #e8edf5; }
.dropdown-item-count { font-size: 11px; color: var(--color-text-secondary); }

/* ── Scrollbar hide ── */
.navbar-modules::-webkit-scrollbar { height: 0; }
</style>
