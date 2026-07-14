<template>
  <nav class="workflow-navbar" v-if="modules.length">
    <div class="navbar-inner">
      <!-- Department badge -->
      <div class="dept-badge" :style="{ background: deptConfig.color }">
        <span class="dept-badge-icon">{{ deptConfig.icon }}</span>
        <span class="dept-badge-text">{{ deptName }}</span>
      </div>

      <!-- Divider -->
      <div class="nav-divider" />

      <!-- Module tabs -->
      <div class="navbar-modules">
        <div
          v-for="mod in modules"
          :key="mod.id"
          class="nav-item"
          :class="{ active: isActive(mod) }"
          @mouseenter="showDropdown(mod)"
          @mouseleave="startLeaveTimer(mod)"
        >
          <!-- Tab -->
          <div class="nav-item-label" @click="navigateToModule(mod)">
            <span class="nav-item-name">{{ cleanName(mod.name) }}</span>
            <span v-if="mod.document_count" class="nav-item-count">{{ mod.document_count }}</span>
            <el-icon v-if="mod.children?.length" class="nav-item-arrow" :class="{ rotated: hoveredModule === mod.id }">
              <ArrowDown />
            </el-icon>
          </div>

          <!-- Dropdown for sub-categories -->
          <Transition name="dropdown">
            <div
              v-if="mod.children?.length && hoveredModule === mod.id"
              class="nav-dropdown"
              @mouseenter="clearLeaveTimer"
              @mouseleave="startLeaveTimer(mod)"
            >
              <div class="dropdown-header">{{ cleanName(mod.name) }}</div>
              <div
                v-for="sub in mod.children"
                :key="sub.id"
                class="dropdown-item"
                :class="{ active: activeModuleId === sub.id }"
                @click="selectSub(sub.id)"
              >
                <span class="dropdown-item-name">{{ sub.name }}</span>
                <span class="dropdown-item-count" v-if="sub.document_count">{{ sub.document_count }} 篇</span>
              </div>
              <!-- View all -->
              <div class="dropdown-footer" @click="navigateToModule(mod)">
                查看全部 →
              </div>
            </div>
          </Transition>
        </div>
      </div>
    </div>
  </nav>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowDown } from '@element-plus/icons-vue'
import { get } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import type { CategoryNode } from '@/api/client'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const modules = ref<CategoryNode[]>([])
const hoveredModule = ref('')
let _leaveTimer: ReturnType<typeof setTimeout> | null = null

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
  }, 150)
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
/* ── Navbar container ── */
.workflow-navbar {
  background: #fff;
  border-bottom: 1px solid var(--color-border);
  position: fixed;
  top: 56px;
  left: 0;
  right: 0;
  height: 46px;
  z-index: 99;
}

.navbar-inner {
  display: flex;
  align-items: center;
  height: 100%;
  padding: 0 20px;
  gap: 0;
  max-width: 1400px;
  margin: 0 auto;
}

/* ── Department badge ── */
.dept-badge {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 3px 12px 3px 6px;
  border-radius: 6px;
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  flex-shrink: 0;
  letter-spacing: .3px;
}
.dept-badge-icon {
  width: 24px; height: 24px;
  background: rgba(255,255,255,.2);
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
}
.dept-badge-text { white-space: nowrap; }

/* ── Divider ── */
.nav-divider {
  width: 1px;
  height: 22px;
  background: var(--color-border);
  margin: 0 12px;
  flex-shrink: 0;
}

/* ── Module tabs ── */
.navbar-modules {
  display: flex;
  align-items: center;
  height: 100%;
  gap: 0;
  flex: 1;
  overflow-x: auto;
  scrollbar-width: none;
}
.navbar-modules::-webkit-scrollbar { display: none; }

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
  padding: 6px 14px;
  border-radius: 6px;
  font-size: 13px;
  color: #5a6270;
  cursor: pointer;
  white-space: nowrap;
  transition: all .18s ease;
  position: relative;
}

.nav-item-label::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 50%;
  transform: translateX(-50%) scaleX(0);
  width: calc(100% - 12px);
  height: 2px;
  background: var(--color-primary);
  border-radius: 2px 2px 0 0;
  transition: transform .2s ease;
}

.nav-item-label:hover {
  color: var(--color-primary);
  background: rgba(30, 80, 174, .04);
}

.nav-item-label:hover::after {
  transform: translateX(-50%) scaleX(1);
}

.nav-item.active .nav-item-label {
  color: var(--color-primary);
  font-weight: 600;
}

.nav-item.active .nav-item-label::after {
  transform: translateX(-50%) scaleX(1);
  background: var(--color-primary);
}

.nav-item-name { position: relative; z-index: 1; }

.nav-item-count {
  font-size: 11px;
  color: var(--color-text-secondary);
  background: var(--color-bg-secondary);
  padding: 1px 5px;
  border-radius: 8px;
  font-weight: 500;
}

.nav-item-arrow {
  font-size: 10px;
  color: var(--color-text-secondary);
  transition: transform .2s ease;
}
.nav-item-arrow.rotated {
  transform: rotate(180deg);
}

/* ── Dropdown panel ── */
.nav-dropdown {
  position: absolute;
  top: calc(100% + 2px);
  left: 4px;
  min-width: 200px;
  max-width: 280px;
  background: #fff;
  border: 1px solid var(--color-border);
  border-radius: 10px;
  box-shadow: 0 12px 32px rgba(0,0,0,.1), 0 2px 8px rgba(0,0,0,.04);
  padding: 6px;
  z-index: 200;
  overflow: hidden;
}

.dropdown-header {
  padding: 7px 12px 5px;
  font-size: 11px;
  font-weight: 600;
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: .5px;
  border-bottom: 1px solid #f0f0f0;
  margin-bottom: 4px;
}

.dropdown-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 12px;
  font-size: 13px;
  color: var(--color-text-primary);
  border-radius: 6px;
  cursor: pointer;
  white-space: nowrap;
  transition: all .12s ease;
}

.dropdown-item:hover {
  background: rgba(30, 80, 174, .06);
  color: var(--color-primary);
}

.dropdown-item.active {
  color: var(--color-primary);
  font-weight: 600;
  background: rgba(30, 80, 174, .08);
}

.dropdown-item-name { overflow: hidden; text-overflow: ellipsis; }

.dropdown-item-count {
  font-size: 11px;
  color: var(--color-text-secondary);
  flex-shrink: 0;
}

.dropdown-footer {
  padding: 7px 12px;
  margin-top: 4px;
  border-top: 1px solid #f0f0f0;
  font-size: 12px;
  color: var(--color-primary);
  text-align: center;
  cursor: pointer;
  border-radius: 0 0 4px 4px;
  font-weight: 500;
  transition: background .12s;
}
.dropdown-footer:hover {
  background: rgba(30, 80, 174, .06);
}

/* ── Dropdown transition ── */
.dropdown-enter-active {
  transition: all .18s ease-out;
}
.dropdown-leave-active {
  transition: all .12s ease-in;
}
.dropdown-enter-from {
  opacity: 0;
  transform: translateY(-6px) scale(.97);
}
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-4px) scale(.98);
}
</style>
