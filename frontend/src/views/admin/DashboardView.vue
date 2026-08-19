<template>
  <div class="dashboard" v-loading="loading">
    <!-- Stat cards row -->
    <div class="stat-cards">
      <div class="stat-card clickable" style="--card-color: #1e50ae" @click="$router.push('/admin/documents')">
        <div class="sc-icon"><el-icon :size="22"><Document /></el-icon></div>
        <div class="sc-info">
          <span class="sc-num">{{ fmtNum(data.overview?.total_docs) }}</span>
          <span class="sc-label">文档总数</span>
        </div>
      </div>
      <div class="stat-card clickable" style="--card-color: #16a34a" @click="$router.push('/admin/activity')">
        <div class="sc-icon"><el-icon :size="22"><User /></el-icon></div>
        <div class="sc-info">
          <span class="sc-num">{{ fmtNum(data.overview?.total_users) }}</span>
          <span class="sc-label">活跃用户</span>
        </div>
      </div>
      <div class="stat-card clickable" style="--card-color: #f59e0b" @click="$router.push('/admin/categories')">
        <div class="sc-icon"><el-icon :size="22"><Folder /></el-icon></div>
        <div class="sc-info">
          <span class="sc-num">{{ fmtNum(data.overview?.total_categories) }}</span>
          <span class="sc-label">分类数量</span>
        </div>
      </div>
      <div class="stat-card clickable" style="--card-color: #3b82f6" @click="$router.push('/admin/activity?tab=views')">
        <div class="sc-icon"><el-icon :size="22"><View /></el-icon></div>
        <div class="sc-info">
          <span class="sc-num">{{ fmtNum(data.overview?.total_views) }}</span>
          <span class="sc-label">总浏览量</span>
        </div>
      </div>
      <div class="stat-card clickable" style="--card-color: #8b5cf6" @click="$router.push('/admin/activity?tab=downloads')">
        <div class="sc-icon"><el-icon :size="22"><Download /></el-icon></div>
        <div class="sc-info">
          <span class="sc-num">{{ fmtNum(data.overview?.total_downloads) }}</span>
          <span class="sc-label">总下载量</span>
        </div>
      </div>
    </div>

    <!-- Charts row -->
    <div class="charts-row">
      <div class="chart-card">
        <h3>每日上传趋势（近14天）</h3>
        <v-chart :option="uploadChartOption" autoresize style="height:280px" />
      </div>
      <div class="chart-card">
        <h3>文件类型分布</h3>
        <v-chart :option="fileTypeChartOption" autoresize style="height:280px" />
      </div>
    </div>

    <div class="charts-row">
      <div class="chart-card">
        <h3>分类文档数量 Top 10</h3>
        <v-chart :option="catChartOption" autoresize style="height:320px" />
      </div>
      <div class="chart-card chart-card-half">
        <h3>用户角色分布</h3>
        <v-chart :option="roleChartOption" autoresize style="height:320px" />
      </div>
    </div>

    <!-- Recent docs table -->
    <div class="recent-section">
      <h3>最近更新文档</h3>
      <el-table :data="data.recent_docs || []" stripe size="small" style="width:100%">
        <el-table-column label="文档标题" min-width="300" show-overflow-tooltip>
          <template #default="{ row }">{{ cleanTitle(row.title) }}</template>
        </el-table-column>
        <el-table-column prop="file_ext" label="格式" width="80" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="extTagType(row.file_ext)">{{ row.file_ext?.toUpperCase() || '-' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="view_count" label="浏览" width="80" align="center" sortable />
        <el-table-column prop="updated_at" label="更新时间" width="160" align="center">
          <template #default="{ row }">{{ row.updated_at?.substring(0, 10) }}</template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Document, User, Folder, View, Download } from '@element-plus/icons-vue'
import { get } from '@/api/client'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, PieChart, LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, TitleComponent } from 'echarts/components'

use([CanvasRenderer, BarChart, PieChart, LineChart, GridComponent, TooltipComponent, LegendComponent, TitleComponent])

const loading = ref(true)
const data = ref<any>({ overview: {}, file_types: [], top_categories: [], daily_uploads: [], roles: [], recent_docs: [] })

const roleNameMap: Record<string, string> = {
  super_admin: '超管', dept_admin: '部门管理员', editor: '编辑者', employee: '员工', guest: '访客'
}

function fmtNum(n: number | undefined) {
  if (!n) return '0'
  if (n >= 10000) return (n / 10000).toFixed(1) + 'w'
  if (n >= 1000) return (n / 1000).toFixed(1) + 'k'
  return String(n)
}
function cleanTitle(t: string) {
  if(!t) return ''
  return t.replace(/NMPA_标签_tagInfo[0-9a-f]+/g,'').replace(/_/g,' ').replace(/\s+/g,' ').trim().substring(0,80) || t
}

function extTagType(ext: string): 'primary' | 'success' | 'warning' | 'info' | 'danger' | undefined {
  const m: Record<string, 'primary' | 'success' | 'warning' | 'info' | 'danger'> = { pdf: 'danger', doc: 'primary', docx: 'primary', xls: 'success', xlsx: 'success', ppt: 'warning', pptx: 'warning', link: 'info' }
  return m[ext?.toLowerCase()] || undefined
}

const uploadChartOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 40, right: 20, top: 10, bottom: 30 },
  xAxis: { type: 'category', data: (data.value.daily_uploads || []).map((d: any) => d.date?.substring(5)), axisLabel: { fontSize: 11 } },
  yAxis: { type: 'value', minInterval: 1, axisLabel: { fontSize: 11 } },
  series: [{ data: (data.value.daily_uploads || []).map((d: any) => d.count), type: 'line', 临床运营部oth: true, areaStyle: { color: 'rgba(30,80,174,.1)' }, lineStyle: { color: '#1e50ae', width: 2 }, itemStyle: { color: '#1e50ae' }, symbol: 'circle', symbolSize: 4 }]
}))

const fileTypeChartOption = computed(() => ({
  tooltip: { trigger: 'item' },
  legend: { bottom: 0, textStyle: { fontSize: 11 } },
  series: [{
    type: 'pie', radius: ['50%', '75%'], center: ['50%', '45%'],
    data: (data.value.file_types || []).map((d: any) => ({ name: (d.name || '?').toUpperCase(), value: d.count })),
    label: { fontSize: 10 }, emphasis: { label: { fontSize: 14, fontWeight: 'bold' } }
  }]
}))

const catChartOption = computed(() => ({
  tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
  grid: { left: 100, right: 30, top: 10, bottom: 20 },
  xAxis: { type: 'value', axisLabel: { fontSize: 11 } },
  yAxis: { type: 'category', data: (data.value.top_categories || []).map((d: any) => d.name).reverse(), axisLabel: { fontSize: 11, width: 90, overflow: 'truncate' } },
  series: [{ data: (data.value.top_categories || []).map((d: any) => d.count).reverse(), type: 'bar', itemStyle: { color: '#1e50ae', borderRadius: [0, 4, 4, 0] }, barMaxWidth: 20 }]
}))

const roleChartOption = computed(() => ({
  tooltip: { trigger: 'item' },
  legend: { bottom: 0, textStyle: { fontSize: 11 } },
  series: [{
    type: 'pie', radius: ['45%', '70%'], center: ['50%', '45%'],
    data: (data.value.roles || []).map((d: any) => ({ name: roleNameMap[d.name] || d.name, value: d.count })),
    label: { fontSize: 11 }
  }]
}))

onMounted(async () => {
  try {
    data.value = await get('/api/admin/dashboard')
  } catch { /* ignore */ }
  loading.value = false
})
</script>

<style scoped>
.dashboard { max-width: 1400px; }

.stat-cards { display: grid; grid-template-columns: repeat(5, 1fr); gap: 14px; margin-bottom: 20px; }
.stat-card {
  background: #fff; border-radius: 12px; padding: 18px 20px;
  display: flex; align-items: center; gap: 14px;
  box-shadow: 0 1px 3px rgba(0,0,0,.04); transition: all .2s;
  border-top: 3px solid var(--card-color);
}
.stat-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,.08); transform: translateY(-2px); }
.stat-card.clickable { cursor: pointer; position: relative; }
.stat-card.clickable::after {
  content: '›'; position: absolute; right: 14px; top: 50%;
  transform: translateY(-50%); font-size: 20px; color: #cbd5e1;
}
.stat-card.clickable:hover::after { color: var(--card-color); }
.sc-icon {
  width: 48px; height: 48px; border-radius: 12px;
  background: color-mix(in srgb, var(--card-color) 10%, #fff);
  color: var(--card-color); display: flex; align-items: center; justify-content: center;
}
.sc-info { display: flex; flex-direction: column; }
.sc-num { font-size: 24px; font-weight: 700; color: #1a1a2e; line-height: 1.1; }
.sc-label { font-size: 12px; color: #888; margin-top: 2px; }

.charts-row { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 20px; }
.chart-card {
  background: #fff; border-radius: 12px; padding: 18px 20px;
  box-shadow: 0 1px 3px rgba(0,0,0,.04);
}
.chart-card h3, .recent-section h3 { font-size: 14px; font-weight: 600; margin: 0 0 12px; color: #1a1a2e; }

.recent-section { background: #fff; border-radius: 12px; padding: 18px 20px; box-shadow: 0 1px 3px rgba(0,0,0,.04); }

@media (max-width: 1200px) {
  .stat-cards { grid-template-columns: repeat(3, 1fr); }
  .charts-row { grid-template-columns: 1fr; }
}
@media (max-width: 768px) {
  .stat-cards { grid-template-columns: repeat(2, 1fr); }
}
</style>
