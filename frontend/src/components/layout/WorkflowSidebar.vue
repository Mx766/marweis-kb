<template>
  <nav class="workflow-navbar" v-if="modules.length">
    <div class="navbar-inner">
      <div class="dept-badge" :style="{ background: deptConfig.color }">
        <span class="dept-badge-icon">{{ deptConfig.icon }}</span>
        <span class="dept-badge-text">{{ deptName }}</span>
      </div>
      <div class="nav-divider" />

      <div class="navbar-modules">
        <template v-for="(mod, idx) in modules" :key="mod.id">
          <!-- Separator between registration (1-7) and cosmetics (8+) -->
          <div v-if="isDeptSeparator(idx)" class="nav-separator">│</div>
          <div
            class="nav-item"
            :class="{ active: isActive(mod) }"
            @mouseenter="showDropdown(mod)"
            @mouseleave="startLeaveTimer"
          >
          <div class="nav-item-label" @click="navigateToModule(mod)">
            <span class="nav-item-dot" :style="{ background: moduleColor(mod) }" v-if="moduleColor(mod)"></span>
            <span class="nav-item-name">{{ cleanName(mod.name) }}</span>
            <el-icon v-if="mod.children?.length" class="nav-item-arrow"><ArrowDown /></el-icon>
          </div>

          <!-- Hover dropdown -->
          <Transition name="dropdown">
            <div
              v-if="mod.children?.length && hoveredModule === mod.id"
              class="nav-dropdown"
              @mouseenter="clearLeaveTimer"
              @mouseleave="startLeaveTimer"
            >
              <div class="dropdown-item" v-for="sub in mod.children" :key="sub.id"
                :class="{ active: activeModuleId === sub.id }"
                @click="selectSub(sub.id)">
                <span class="dropdown-item-name">{{ sub.name }}</span>
                <span class="dropdown-item-count" v-if="sub.document_count">{{ sub.document_count }}</span>
              </div>
              <div class="dropdown-footer" @click="navigateToModule(mod)">查看全部 →</div>
            </div>
          </Transition>
          </div>
        </template>
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
let leaveTimer: ReturnType<typeof setTimeout> | null = null

const DEPT_CONFIG: Record<string, { icon: string; label: string; color: string }> = {
  '总经办':       { icon: 'E', label: '总经办', color: '#1e40af' },
  '人力资源部':   { icon: 'H', label: '人力资源部', color: '#d97706' },
  '财务部':       { icon: 'F', label: '财务部', color: '#65a30d' },
  '市场部':   { icon: 'M', label: '市场部', color: '#ec4899' },
  '注册部':       { icon: 'R', label: '注册部', color: '#1e50ae' },
  '医学部部':         { icon: 'Y', label: '医学部部', color: '#2e86c1' },
  '临床运营部':          { icon: 'S', label: '临床运营部', color: '#0891b2' },
  '临床研究部':          { icon: 'C', label: '临床研究部', color: '#059669' },
  '质量部':     { icon: 'Q', label: '质量部', color: '#a855f7' },
  '商务部':    { icon: 'B', label: '商务部', color: '#2563eb' },
  '国际部':         { icon: 'K', label: '国际部', color: '#e11d48' },
  '公共共享区':   { icon: 'S', label: '公共共享区', color: '#6366f1' },
}

const deptConfig = computed(() => {
  const dept = auth.user?.department || ''
  return DEPT_CONFIG[dept] || { icon: 'M', label: dept, color: '#1e50ae' }
})
const deptName = computed(() => {
  const d = auth.user?.department || '知识库'
  return d.replace(/（.*）/, '')
})

const activeModuleId = computed(() =>
  (route.params.moduleId as string) || (route.params.categoryId as string) || ''
)

onMounted(async () => {
  try {
    const cats: CategoryNode[] = await get('/api/categories')
    const publicZone = cats.filter(c => c.name === '公共知识区')
    const deptCats = cats.filter(c => c.name !== '公共知识区')

    // Flatten: expand department-level containers (children are also numbered, e.g. "8.化妆品·医美部" -> show its children)
    // Don't flatten workflow modules like "1.参考文件" whose children are regular categories
    const flatModules: CategoryNode[] = []
    for (const c of deptCats) {
      const hasNumberedChildren = c.children?.some(child => /^\d+\./.test(child.name))
      if (/^\d+\./.test(c.name) && c.children?.length && hasNumberedChildren) {
        for (const child of c.children) {
          flatModules.push(child)
        }
      } else {
        flatModules.push(c)
      }
    }

    const numbered = flatModules.filter(c => /^\d+\./.test(c.name))
    const others = flatModules.filter(c => !/^\d+\./.test(c.name))
    modules.value = [...numbered, ...others, ...publicZone].sort((a, b) => a.sort_order - b.sort_order)
  } catch { modules.value = [] }
})

function moduleColor(_mod: CategoryNode) {
  return 'var(--color-primary)'
}
function cleanName(name: string) { return name.replace(/^\d+\.\s*/, '') }
function isDeptSeparator(idx: number) {
  if (idx === 0) return false
  const prev = modules.value[idx - 1]?.name || ''
  const curr = modules.value[idx]?.name || ''
  // Separator between 器械注册 (1-7) and 化妆品 (8)
  if (prev.startsWith('7.') && curr.startsWith('8.')) return true
  // Separator between last numbered and first named dept
  const prevNum = /^\d+\./.test(prev)
  const currNum = /^\d+\./.test(curr)
  if (prevNum && !currNum) return true
  return false
}
function isActive(mod: CategoryNode) {
  if (activeModuleId.value === mod.id) return true
  return mod.children?.some(s => s.id === activeModuleId.value) || false
}

function showDropdown(mod: CategoryNode) {
  clearLeaveTimer()
  hoveredModule.value = mod.id
}
function startLeaveTimer() {
  leaveTimer = setTimeout(() => { hoveredModule.value = '' }, 350)
}
function clearLeaveTimer() {
  if (leaveTimer) { clearTimeout(leaveTimer); leaveTimer = null }
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
  background: #fff; border-bottom: 1px solid var(--color-border);
  position: fixed; top: 56px; left: 0; right: 0; z-index: 99;
  min-height: 46px;
}

.navbar-inner {
  display: flex; align-items: flex-start;
  padding: 6px 16px; gap: 0;
  max-width: 1400px; margin: 0 auto;
}

.dept-badge {
  display: flex; align-items: center; gap: 6px;
  padding: 3px 10px; border-radius: 5px; color: #fff;
  font-size: 11px; font-weight: 600; flex-shrink: 0; margin-top: 2px;
}
.dept-badge-icon {
  width: 20px; height: 20px; background: rgba(255,255,255,.2);
  border-radius: 4px; display: flex; align-items: center; justify-content: center;
  font-size: 10px; font-weight: 700;
}

.nav-divider { width: 1px; height: 20px; background: var(--color-border); margin: 3px 10px 0; flex-shrink: 0; }

.navbar-modules {
  display: flex; flex-wrap: wrap; align-items: center; gap: 2px; flex: 1;
}

.nav-item { position: relative; }

.nav-item-label {
  display: flex; align-items: center; gap: 5px;
  padding: 5px 10px; border-radius: 5px; font-size: 12px;
  color: #5a6270; cursor: pointer; white-space: nowrap;
  transition: all .15s ease;
}
.nav-item-label:hover { color: var(--color-primary); background: rgba(30,80,174,.05); }
.nav-item.active .nav-item-label { color: var(--color-primary); font-weight: 600; background: rgba(30,80,174,.07); }

.nav-item-dot {
  width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0;
  opacity: .35; transition: opacity .15s;
}
.nav-item.active .nav-item-dot,
.nav-item-label:hover .nav-item-dot {
  opacity: 1;
}

.nav-item-name { padding: 1px 0; }
.nav-item-arrow { font-size: 9px; color: var(--color-text-secondary); }

.nav-separator {
  color: #d0d0d0; font-size: 16px; margin: 0 4px; user-select: none;
  align-self: center; line-height: 1;
}

/* ── Dropdown ── */
.nav-dropdown {
  position: absolute; top: 100%; left: 0; min-width: 160px; max-width: 240px;
  background: #fff; border: 1px solid var(--color-border);
  border-radius: 10px; box-shadow: 0 12px 32px rgba(0,0,0,.1);
  padding: 4px; z-index: 200; overflow: hidden;
}
.dropdown-item {
  display: flex; align-items: center; justify-content: space-between; gap: 8px;
  padding: 7px 10px; font-size: 12px; color: var(--color-text-primary);
  border-radius: 6px; cursor: pointer; transition: all .12s;
}
.dropdown-item:hover { background: rgba(30,80,174,.06); color: var(--color-primary); }
.dropdown-item.active { color: var(--color-primary); font-weight: 600; background: rgba(30,80,174,.08); }
.dropdown-item-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.dropdown-item-count { font-size: 10px; color: var(--color-text-secondary); flex-shrink: 0; }
.dropdown-footer {
  padding: 6px 10px; margin-top: 2px; border-top: 1px solid #f0f0f0;
  font-size: 11px; color: var(--color-primary); text-align: center;
  cursor: pointer; border-radius: 4px; font-weight: 500;
}
.dropdown-footer:hover { background: rgba(30,80,174,.06); }

.dropdown-enter-active { transition: all .15s ease-out; }
.dropdown-leave-active { transition: all .1s ease-in; }
.dropdown-enter-from, .dropdown-leave-to { opacity: 0; transform: translateY(-4px); }

@media (max-width: 768px) {
  .workflow-navbar {
    min-height: 46px;
  }
  .navbar-inner {
    flex-wrap: nowrap;
    overflow-x: auto;
    padding: 6px 12px;
    s临床研究部llbar-width: none;
    -webkit-overflow-s临床研究部lling: touch;
  }
  .navbar-inner::-webkit-s临床研究部llbar {
    display: none;
  }
  .navbar-modules {
    flex-wrap: nowrap;
  }
  .dept-badge {
    padding: 3px 8px;
  }
  .dept-badge-text {
    display: none;
  }
  .nav-separator {
    display: none;
  }
  .nav-item-label {
    padding: 5px 9px;
    font-size: 12px;
  }
  .nav-item-arrow {
    display: none;
  }
  .nav-dropdown {
    display: none !important;
  }
}
</style>
