<template>
  <div class="admin-layout">
    <!-- Top bar -->
    <header class="admin-topbar">
      <div class="topbar-logo" @click="$router.push('/admin')">
        <el-icon :size="18"><Monitor /></el-icon>
        <span>管理后台</span>
      </div>
      <div class="topbar-right">
        <el-button size="small" @click="$router.push('/')">返回前台</el-button>
      </div>
    </header>

    <!-- Body -->
    <div class="admin-body">
      <!-- 管理功能入口 -->
      <nav class="admin-toolbar">
        <router-link to="/admin" class="tool-link" :class="{active: route.path==='/admin'}">
          <el-icon :size="14"><DataAnalysis /></el-icon> 仪表盘
        </router-link>
        <router-link to="/admin/documents" class="tool-link" :class="{active: route.path==='/admin/documents'}">
          <el-icon :size="14"><Document /></el-icon> 文档管理
        </router-link>
        <router-link to="/admin/categories" class="tool-link" :class="{active: route.path==='/admin/categories'}">
          <el-icon :size="14"><Folder /></el-icon> 分类管理
        </router-link>
        <router-link to="/admin/users" class="tool-link" :class="{active: route.path==='/admin/users'}">
          <el-icon :size="14"><User /></el-icon> 用户管理
        </router-link>
        <router-link to="/admin/activity" class="tool-link" :class="{active: route.path==='/admin/activity'}">
          <el-icon :size="14"><Clock /></el-icon> 访问记录
        </router-link>
        <router-link v-if="isSuperAdmin" to="/admin/settings" class="tool-link" :class="{active: route.path==='/admin/settings'}">
          <el-icon :size="14"><Setting /></el-icon> 系统设置
        </router-link>
        <router-link v-if="isSuperAdmin" to="/admin/ai" class="tool-link" :class="{active: route.path==='/admin/ai'}">
          <el-icon :size="14"><Cpu /></el-icon> AI知识库
        </router-link>
        <router-link v-if="isSuperAdmin" to="/admin/ops" class="tool-link" :class="{active: route.path==='/admin/ops'}">
          <el-icon :size="14"><Refresh /></el-icon> 数据更新
        </router-link>
      </nav>

      <main class="admin-main">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { Monitor, DataAnalysis, Document, Folder, FolderOpened, User, Setting, ArrowDown, Cpu, Clock, Refresh } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { get } from '@/api/client'
import { DEPARTMENTS, DEPT_META } from '@/utils/departments'

const route = useRoute()
const auth = useAuthStore()
const isSuperAdmin = computed(() => auth.user?.role === 'super_admin')
const deptOpen = ref('')

const departments = DEPARTMENTS
const deptCats = ref<Record<string,any[]>>({})

const deptColors: Record<string,string> = Object.fromEntries(departments.map((d: string) => [d, DEPT_META[d]?.color || '#666']))
const deptIcons: Record<string,string> = Object.fromEntries(departments.map((d: string) => [d, DEPT_META[d]?.icon || 'D']))
const itemColors = ['#1e50ae','#2e86c1','#27ae60','#8e44ad','#e74c3c','#fb8c00','#333','#0891b2','#f59e0b','#16a34a']
function itemColor(idx: number) { return itemColors[idx % itemColors.length] }

onMounted(async () => {
  try {
    const tree: any[] = await get('/api/categories')
    // Group first-level categories by department name pattern
    const map: Record<string,any[]> = {}
    for(const c of tree){
      for(const dept of departments){
        if(c.name?.includes(dept) || dept.includes(c.name?.substring(0,4))){
          if(!map[dept]) map[dept] = []
          map[dept].push(...(c.children||[]))
        }
      }
    }
    // Fallback: first few root categories assigned to first dept
    if(!Object.keys(map).length && tree.length){
      map[departments[0]] = tree.filter((c:any)=>c.children?.length).flatMap((c:any)=>c.children)
    }
    deptCats.value = map
  } catch {}
})
</script>

<style scoped>
.admin-layout { min-height: 100vh; background: #f0f2f5; }

.admin-topbar {
  position: fixed; top: 0; left: 0; right: 0; height: 48px; z-index: 1000;
  background: #fff; color: #333; border-bottom: 1px solid #e8e8e8;
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 20px;
}
.topbar-logo { display: flex; align-items: center; gap: 8px; font-size: 14px; font-weight: 600; cursor: pointer; }
.topbar-right { display:flex; gap:8px; }
.topbar-right .el-button { background: #f0f4f8; color: #333; border: 1px solid #d0d5dd; font-weight:500; }
.topbar-right .el-button:hover { background: #e0e4e8; border-color: #b0b8c4; }

.admin-body { padding-top: 48px; min-height: 100vh; }

/* 管理功能入口 */
.admin-toolbar {
  display: flex; gap: 4px; padding: 8px 20px; background: #fff;
  border-bottom: 1px solid #e8e8e8; flex-wrap: wrap;
}
.tool-link {
  display: flex; align-items: center; gap: 4px; padding: 6px 12px;
  border-radius: 6px; font-size: 13px; color: #555; text-decoration: none; transition: all .1s;
}
.tool-link:hover { background: #f0f4f8; color: var(--color-primary); }
.tool-link.active { background: #e8f0fe; color: var(--color-primary); font-weight: 600; }

/* 部门导航 — 完全复刻 WorkflowSidebar */
.dept-navs { padding: 0; }
.dept-navbar { border-bottom: 1px solid #e8ecf0; background: #fff; }
.dept-bar { display:flex; align-items:center; height:44px; padding:0 20px; gap:0; max-width:100%; overflow:hidden; }
.dept-badge { display:flex; align-items:center; gap:6px; padding:5px 14px; border-radius:6px; color:#fff; flex-shrink:0; }
.dept-badge-icon { font-size:14px; font-weight:700; width:22px; height:22px; border-radius:4px; background:rgba(255,255,255,.2); display:flex; align-items:center; justify-content:center; }
.dept-badge-text { font-size:12px; font-weight:600; white-space:nowrap; }
.dept-divider { width:1px; height:24px; background:#e0e4e8; margin:0 12px; flex-shrink:0; }
.dept-modules { display:flex; align-items:center; gap:2px; overflow-x:auto; flex:1; }
.dept-nav-item { display:flex; align-items:center; gap:4px; padding:6px 12px; border-radius:6px; font-size:12px; color:#5a6270; text-decoration:none; white-space:nowrap; transition:all .12s; }
.dept-nav-item:hover { background:rgba(30,80,174,.05); color:var(--color-primary); }
.dept-nav-item.active { background:rgba(30,80,174,.07); color:var(--color-primary); font-weight:600; }
.dept-nav-dot { width:7px; height:7px; border-radius:50%; flex-shrink:0; }
.dept-nav-name { white-space:nowrap; }
.dept-empty { font-size:11px; color:#ccc; padding:0 8px; }

.admin-main { padding: 16px 20px; }
</style>
