<template>
  <div class="kg-page">
    <div class="kg-header">
      <h1>化妆品知识体系</h1>
      <p class="kg-subtitle">{{ totalDocs }} 篇文档 · {{ catCount }} 个分类节点</p>
      <div class="kg-tabs">
        <button :class="{ active: viewMode === 'tree' }" @click="viewMode='tree'">树形结构</button>
        <button :class="{ active: viewMode === 'treemap' }" @click="viewMode='treemap'">矩形分布</button>
      </div>
    </div>

    <div class="kg-chart-wrap" v-loading="loading">
      <div v-if="!treeData && !loading" style="text-align:center;padding:60px 20px;color:var(--color-text-secondary)">
        <p>暂无知识图谱数据</p>
        <p style="font-size:12px;margin-top:8px">请确认分类结构已正确配置</p>
      </div>
      <div ref="chartEl" class="kg-chart" v-show="treeData"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { get } from '@/api/client'
import * as echarts from 'echarts'

const router = useRouter()
const loading = ref(true)
const chartEl = ref<HTMLElement>()
let chart: echarts.ECharts | null = null
const viewMode = ref<'tree' | 'treemap'>('tree')
const treeData = ref<any>(null)
const totalDocs = ref(0)
const catCount = ref(0)

async function loadData() {
  try {
    const raw = await get('/api/cosmetics/knowledge-graph')
    if (!raw || !raw.nodes?.length) {
      treeData.value = null
      return
    }
    const nodes = raw.nodes || []
  const links = raw.links || []

  // Build adjacency: parent -> children
  const childrenMap: Record<string, any[]> = {}
  const nodeMap: Record<string, any> = {}
  for (const n of nodes) {
    if (n.category > 1) continue // skip type nodes for tree
    nodeMap[n.id] = {
      name: n.label || n.name,
      fullName: n.name,
      value: n.value || 0,
      symbolSize: n.symbolSize || 20,
      id: n.id,
      children: [],
    }
  }

  let rootNode: any = null
  const typeLinks: Record<string, any[]> = {}

  for (const l of links) {
    // Collect type links separately
    if (l.target && typeof l.target === 'string' && l.target.startsWith('type_')) {
      const catId = l.source
      if (!typeLinks[catId]) typeLinks[catId] = []
      typeLinks[catId].push(l)
      continue
    }

    const parent = nodeMap[l.source]
    const child = nodeMap[l.target]
    if (parent && child) {
      parent.children.push(child)
    } else if (!parent && nodeMap[l.source]) {
      // This might be a root node
    }
  }

  // Find root: the node with no parent (but has children)
  const hasParent = new Set<string>()
  for (const l of links) {
    if (l.target && !l.target.startsWith('type_')) hasParent.add(l.target)
  }
  for (const n of nodes) {
    if (n.category <= 1 && !hasParent.has(n.id) && nodeMap[n.id]?.children?.length > 0) {
      rootNode = nodeMap[n.id]
      break
    }
  }
  if (!rootNode) {
    // Fallback: use first node
    rootNode = nodeMap[nodes[0]?.id]
  }

  // Trim empty children
  function trimEmpty(node: any) {
    if (!node.children || node.children.length === 0) {
      delete node.children
      return
    }
    node.children = node.children.filter((c: any) => c.value > 0 || (c.children && c.children.length > 0))
    for (const c of node.children) trimEmpty(c)
  }
  if (rootNode) trimEmpty(rootNode)

  // Count totals
  totalDocs.value = nodes.reduce((s: number, n: any) => s + (n.value || 0), 0)
  catCount.value = nodes.filter((n: any) => n.category <= 1 && n.value >= 0).length

  // For treemap: flatten type links into the tree
  if (rootNode) {
    for (const nid of Object.keys(typeLinks)) {
      const catNode = findNode(rootNode, nid)
      if (catNode && typeLinks[nid].length > 0) {
        if (!catNode.children) catNode.children = []
        for (const tl of typeLinks[nid]) {
          const typeNode = nodes.find((n: any) => n.id === tl.target)
          if (typeNode) {
            catNode.children.push({
              name: typeNode.label || typeNode.name,
              value: typeNode.value || tl.value || 1,
              itemStyle: typeNode.itemStyle || undefined,
              collapsed: true,
            })
          }
        }
      }
    }
  }

  treeData.value = rootNode
  } catch {
    treeData.value = null
  }
}

function findNode(node: any, id: string): any {
  if (node.id === id) return node
  if (node.children) {
    for (const c of node.children) {
      const found = findNode(c, id)
      if (found) return found
    }
  }
  return null
}

function buildTreeOption() {
  if (!treeData.value) return {}
  return {
    tooltip: {
      trigger: 'item',
      formatter: (p: any) => {
        const v = p.value || 0
        const name = p.name || ''
        return `<b>${name}</b><br/>文档数: ${v}`
      },
    },
    series: [
      {
        type: 'tree',
        data: [treeData.value],
        top: '2%',
        left: '8%',
        bottom: '2%',
        right: '15%',
        symbol: 'circle',
        symbolSize: (v: number, p: any) => {
          return Math.max(8, Math.min(40, 8 + (p.value || 0) * 0.15))
        },
        orient: 'LR',
        expandAndCollapse: true,
        initialTreeDepth: 2,
        label: {
          position: 'right',
          verticalAlign: 'middle',
          align: 'left',
          fontSize: 12,
          color: '#333',
          formatter: (p: any) => {
            const v = p.value || 0
            return v > 0 ? `${p.name} (${v})` : p.name
          },
        },
        leaves: {
          label: {
            position: 'right',
            verticalAlign: 'middle',
            align: 'left',
          },
        },
        lineStyle: {
          color: '#a0a8b4',
          curveness: 0.5,
        },
        itemStyle: {
          borderWidth: 0,
        },
        emphasis: {
          focus: 'descendant',
          label: { fontSize: 14, fontWeight: 'bold' },
        },
      },
    ],
  }
}

function buildTreemapOption() {
  if (!treeData.value) return {}

  // Convert tree to treemap data (flatten)
  function toTreemap(node: any): any {
    const result: any = {
      name: node.name || node.fullName || '',
      value: Math.max(1, node.value || 1),
    }
    if (node.itemStyle) result.itemStyle = node.itemStyle
    if (node.children && node.children.length > 0) {
      result.children = node.children.map(toTreemap)
    }
    return result
  }
  const tmData = toTreemap(treeData.value)

  return {
    tooltip: {
      formatter: (p: any) => {
        return `<b>${p.name}</b><br/>文档数: ${p.value || 0}`
      },
    },
    series: [
      {
        type: 'treemap',
        data: tmData.children || [tmData],
        top: 0,
        left: 0,
        bottom: 0,
        right: 0,
        roam: false,
        breadcrumb: { show: true, height: 28 },
        label: {
          show: true,
          formatter: (p: any) => {
            return `${p.name}\n(${p.value})`
          },
          fontSize: 12,
        },
        upperLabel: {
          show: true,
          height: 24,
          fontSize: 13,
          fontWeight: 'bold',
        },
        itemStyle: {
          borderColor: '#fff',
          borderWidth: 2,
        },
        levels: [
          {
            colorMappingBy: 'value',
            color: ['#e8f0fe', '#a8c8fa', '#5a9af5', '#1e50ae'],
          },
        ],
        emphasis: {
          label: { fontSize: 16, fontWeight: 'bold' },
        },
      },
    ],
  }
}

function buildOption() {
  if (viewMode.value === 'tree') return buildTreeOption()
  return buildTreemapOption()
}

function handleResize() {
  chart?.resize()
}

onMounted(async () => {
  loading.value = true
  await loadData()

  await nextTick()
  if (chartEl.value) {
    chart = echarts.init(chartEl.value)
    chart.on('click', (params: any) => {
      // Navigate to category on click
      if (params.data?.id && !params.data.id.startsWith('type_')) {
        router.push(`/category/${params.data.id}`)
      }
    })
    chart.setOption(buildOption(), true)
    window.addEventListener('resize', handleResize)
  }
  loading.value = false
})

watch(viewMode, async () => {
  await nextTick()
  if (chart) chart.setOption(buildOption(), true)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  chart?.dispose()
})
</script>

<style scoped>
.kg-page { max-width: 100%; padding: 8px 16px; }
.kg-header { text-align: center; margin-bottom: 6px; }
.kg-header h1 { font-size: 20px; font-weight: 700; color: var(--color-text-primary); margin: 0; }
.kg-subtitle { font-size: 12px; color: var(--color-text-secondary); margin: 4px 0 8px; }
.kg-tabs { display: flex; gap: 8px; justify-content: center; margin-bottom: 8px; }
.kg-tabs button {
  padding: 5px 18px; border: 1px solid var(--color-border); border-radius: 16px;
  background: #fff; font-size: 12px; color: var(--color-text-secondary);
  cursor: pointer; font-family: inherit; transition: all .15s;
}
.kg-tabs button:hover { border-color: var(--color-primary); color: var(--color-primary); }
.kg-tabs button.active { background: var(--color-primary); color: #fff; border-color: var(--color-primary); }
.kg-chart-wrap { background: #fff; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,.04); overflow: hidden; }
.kg-chart { width: 100%; height: calc(100vh - 200px); min-height: 600px; }
</style>
