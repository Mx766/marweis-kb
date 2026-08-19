<template>
  <nav class="dept-bars" v-if="bars.length">
    <!-- Coming soon placeholder for departments without content -->
    <div v-for="bar in placeholderBars" :key="'ph-'+bar.dept" class="dept-row dept-placeholder ph-row">
      <div class="dept-badge" :style="{background: bar.color, opacity:'0.7'}">
        <span class="dept-icon">{{ bar.icon }}</span>
        <span class="dept-name">{{ bar.dept }}</span>
      </div>
      <div class="dept-divider" />
      <div class="dept-items">
        <span style="color:#bbb;font-size:12px;padding:4px 10px;">🚧 知识库建设中，敬请期待</span>
      </div>
    </div>

    <div v-for="bar in bars" :key="bar.dept" class="dept-row" :class="{ 'row-current': bar.dept === activeDept }">
      <div class="dept-badge" :style="{background: bar.color}">
        <span class="dept-icon">{{ bar.icon }}</span>
        <span class="dept-name">{{ bar.dept }}</span>
      </div>
      <div class="dept-divider" />
      <div class="dept-items">
        <!-- Flat mode: single root → show children directly -->
        <template v-if="bar.flat">
          <template v-for="cat in bar.cats" :key="cat.id">
            <router-link v-if="cat.children?.length" v-for="sub in cat.children" :key="sub.id"
              :to="'/category/'+sub.id" class="dept-link"
              :class="{active: activeId===sub.id}">
              <span class="dept-dot" :style="{background: bar.color}"></span>
              {{ cleanName(sub.name) }}
            </router-link>
            <router-link v-else :to="'/category/'+cat.id" class="dept-link"
              :class="{active: activeId===cat.id}">
              <span class="dept-dot" :style="{background: bar.color}"></span>
              {{ cleanName(cat.name) }}
            </router-link>
          </template>
        </template>
        <!-- Dropdown mode: hover to show (same as WorkflowSidebar) -->
        <template v-else>
          <div v-for="cat in bar.cats" :key="cat.id" class="nav-item"
            :class="{ active: isActive(cat) }"
            @mouseenter="showDropdown(cat.id)"
            @mouseleave="startTimer">
            <div class="nav-label" @click="goCat(cat.id)">
              <span class="nav-dot" :style="{background: bar.color}"></span>
              <span class="nav-label-text">{{ cleanName(cat.name) }}</span>
              <span class="nav-arrow" v-if="cat.children?.length">▾</span>
            </div>
            <Transition name="dropdown">
              <div v-if="cat.children?.length && hovered === cat.id" class="nav-dropdown"
                @mouseenter="clearTimer()" @mouseleave="startTimer()">
                <div v-for="sub in cat.children" :key="sub.id" class="drop-item"
                  :class="{ active: activeId === sub.id }" @click="goCat(sub.id)">
                  <span class="drop-item-name">{{ sub.name }}</span>
                  <span class="drop-item-count" v-if="sub.document_count">{{ sub.document_count }}</span>
                </div>
                <div class="drop-footer" @click="goCat(cat.id)">查看全部 →</div>
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
import { get } from '@/api/client'
import type { CategoryNode } from '@/api/client'

const route = useRoute()
const router = useRouter()
const allCats = ref<CategoryNode[]>([])
const hovered = ref('')
let leaveTimer: ReturnType<typeof setTimeout> | null = null
const activeId = computed(() => (route.params.id || route.params.categoryId || '') as string)

const activeDept = computed(() => {
  const id = activeId.value
  if (!id) return bars.value[0]?.dept || ''
  return bars.value.find(bar =>
    bar.cats.some(c => c.id === id || c.children?.some((ch: any) => ch.id === id))
  )?.dept || bars.value[0]?.dept || ''
})

function clearTimer() { if (leaveTimer) { clearTimeout(leaveTimer); leaveTimer = null } }
function startTimer() { leaveTimer = setTimeout(() => { hovered.value = '' }, 350) }
function showDropdown(id: string) { clearTimer(); hovered.value = id }

const DEPTS: Record<string,{icon:string;color:string;match:string[]}> = {
  '总经办':      {icon:'E',color:'#1e40af',match:['管理层','战略','月度报告','合同']},
  '人力资源部':  {icon:'H',color:'#d97706',match:['人力','行政','招聘','薪酬']},
  '财务部':      {icon:'F',color:'#65a30d',match:['财务','会计','预算']},
  '市场部':  {icon:'M',color:'#ec4899',match:['化妆品','医美','原料搜索引擎','知识图谱','杂物']},
  '注册部':      {icon:'R',color:'#1e50ae',match:['注册','审评','分类','参考文件','共性问题','技术要求','国际','标签','审核','法规','公共知识','公共文件','OA','特医食品','注册指南']},
  '医学部':        {icon:'Y',color:'#2e86c1',match:['医学部','临床评价','CER','等同','评价方法','临床试验方案库','方案库','项目模板','结题','培训资料']},
  '临床运营部':         {icon:'S',color:'#0891b2',match:['临床运营部','临床试验','GCP','方案库','数据统计','中心筛选','稽查']},
  '临床研究部':         {icon:'C',color:'#059669',match:['临床研究部','临床事务']},
  '质量部':    {icon:'Q',color:'#a855f7',match:['质量部','生产体系','ISO13485','模拟体考','体系培训','供应商','质量手册']},
  '商务部':   {icon:'B',color:'#2563eb',match:['商务','市场','本部']},
  '国际部':        {icon:'K',color:'#e11d48',match:['国际部','韩国']},
  '公共共享区':  {icon:'S',color:'#6366f1',match:['公共']},
}
// Reorder: departments with content first, then "coming soon" ones
const DEPT_NAMES = [
  '总经办','人力资源部','财务部','市场部','注册部','医学部','临床运营部','临床研究部','质量部','商务部','国际部','公共共享区'
]

// Departments with no content → show placeholder
const placeholderBars = computed(() => {
  return DEPT_NAMES
    .filter(d => !bars.value.some(b => b.dept === d))
    .map(d => ({dept: d, icon: DEPTS[d].icon, color: DEPTS[d].color}))
})

const bars = computed(() => {
  if(!allCats.value.length) return []
  const result: {dept:string;icon:string;color:string;cats:CategoryNode[];flat:boolean}[] = []
  const assigned = new Set<string>()

  for(const dept of DEPT_NAMES){
    const cfg = DEPTS[dept]
    const cats: CategoryNode[] = []
    for(const c of allCats.value){
      const name = c.name.replace(/^\d+[\.\、\s]*/,'')
      if (/OA/i.test(c.name || '')) continue
      if(cfg.match.some(kw => name.includes(kw)) && !assigned.has(c.id)){
        // Expand numbered root cats with numbered children (same as WorkflowSidebar)
        const hasNumberedChildren = c.children?.some((ch: any) => /^\d+[\.\、]/.test(ch.name || ''))
        if (/^\d+/.test(c.name) && c.children?.length && hasNumberedChildren) {
          for (const child of c.children) {
            cats.push(child)
          }
        } else {
          cats.push(c)
        }
        assigned.add(c.id)
      }
    }
    if(cats.length) {
      // Flat: single root with plain children → show children directly
      // Dropdown: multiple roots, or expanded numbered children
      const isExpanded = cats.some(c => /^\d+[\.\、]/.test(c.name || ''))
      const flat = cats.length === 1 && !isExpanded
      result.push({dept, icon:cfg.icon, color:cfg.color, cats, flat})
    }
  }
  return result
})

function isActive(cat: CategoryNode) {
  if (activeId.value === cat.id) return true
  return cat.children?.some(c => c.id === activeId.value) || false
}
function goCat(id: string) { router.push('/category/'+id) }
function cleanName(n: string){ return n.replace(/^\d+[\.\、\s]*/,'').replace(/【.*?】/g,'').trim() }

onMounted(async ()=>{
  try { allCats.value = await get('/api/categories') } catch {}
})
</script>

<style scoped>
.dept-bars { padding-top:56px; border-bottom:1px solid #e8ecf0; }
.dept-row { display:flex; align-items:center; min-height:40px; padding:5px 16px; background:#fff; border-bottom:1px solid #f0f0f0; }
.dept-row.dept-placeholder { background:#fafafa; }
.dept-badge { display:flex; align-items:center; gap:6px; padding:3px 10px; border-radius:5px; color:#fff; font-size:11px; font-weight:600; flex-shrink:0; }
.dept-icon { width:18px; height:18px; background:rgba(255,255,255,.2); border-radius:4px; display:flex; align-items:center; justify-content:center; font-size:9px; font-weight:700; }
.dept-divider { width:1px; height:18px; background:#e0e4e8; margin:0 10px; flex-shrink:0; }
.dept-items { display:flex; flex-wrap:wrap; gap:2px; flex:1; }

.dept-link { display:flex; align-items:center; gap:4px; padding:4px 10px; border-radius:5px; font-size:12px; color:#5a6270; text-decoration:none; white-space:nowrap; transition:all .1s; }
.dept-link:hover { color:var(--color-primary); background:rgba(30,80,174,.05); }
.dept-link.active { color:var(--color-primary); font-weight:600; background:rgba(30,80,174,.07); }
.dept-dot { width:5px; height:5px; border-radius:50%; flex-shrink:0; opacity:.35; }
.dept-link.active .dept-dot, .dept-link:hover .dept-dot { opacity:1; }

.nav-item { position:relative; }
.nav-label { display:flex; align-items:center; gap:4px; padding:4px 10px; border-radius:5px; font-size:12px; color:#5a6270; cursor:pointer; white-space:nowrap; transition:all .1s; }
.nav-label:hover { color:var(--color-primary); background:rgba(30,80,174,.05); }
.nav-item.active .nav-label { color:var(--color-primary); font-weight:600; background:rgba(30,80,174,.07); }
.nav-dot { width:5px; height:5px; border-radius:50%; flex-shrink:0; opacity:.35; }
.nav-item.active .nav-dot, .nav-label:hover .nav-dot { opacity:1; }
.nav-arrow { font-size:9px; color:#999; margin-left:2px; }

.nav-dropdown { position:absolute; top:100%; left:0; min-width:150px; max-width:240px; background:#fff; border:1px solid #e0e4e8; border-radius:10px; box-shadow:0 12px 32px rgba(0,0,0,.1); padding:4px; z-index:200; overflow:hidden; }
.drop-item { display:flex; align-items:center; justify-content:space-between; gap:8px; padding:7px 10px; font-size:12px; color:#333; border-radius:6px; cursor:pointer; transition:all .12s; }
.drop-item:hover { background:rgba(30,80,174,.06); color:var(--color-primary); }
.drop-item.active { color:var(--color-primary); font-weight:600; background:rgba(30,80,174,.08); }
.drop-item-name { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.drop-item-count { font-size:10px; color:#999; flex-shrink:0; }
.drop-footer { display:block; padding:6px 10px; margin-top:2px; border-top:1px solid #f0f0f0; font-size:11px; color:var(--color-primary); text-align:center; cursor:pointer; border-radius:4px; font-weight:500; }
.drop-footer:hover { background:rgba(30,80,174,.06); }

.dropdown-enter-active { transition:all .15s ease-out; }
.dropdown-leave-active { transition:all .1s ease-in; }
.dropdown-enter-from, .dropdown-leave-to { opacity:0; transform:translateY(-4px); }

@media (max-width: 768px) {
  .dept-row:not(.row-current),
  .ph-row {
    display: none;
  }
  .dept-row {
    padding: 4px 10px;
    min-height: 38px;
  }
  .dept-items {
    flex-wrap: nowrap;
    overflow-x: auto;
    s临床研究部llbar-width: none;
    -webkit-overflow-s临床研究部lling: touch;
  }
  .dept-items::-webkit-s临床研究部llbar {
    display: none;
  }
  .dept-name {
    display: none;
  }
  .dept-divider {
    margin: 0 6px;
  }
  .dept-link, .nav-label {
    padding: 4px 8px;
    font-size: 12px;
  }
  .nav-arrow {
    display: none;
  }
  .nav-dropdown {
    display: none !important;
  }
}
</style>
