<template>
  <div class="ingredient-search-page">
    <!-- Header -->
    <div class="search-hero">
      <div class="hero-icon">🧪</div>
      <h1>化妆品原料搜索引擎</h1>
      <p class="hero-desc">CIR安全评估 · KCIA韩英对照 · 5000+原料数据</p>

      <!-- Search bar -->
      <div class="search-box">
        <!-- Mode toggles -->
        <div class="mode-toggles">
          <button :class="{ active: mode === 'fuzzy' }" @click="switchMode('fuzzy')">
            <el-icon :size="14"><Search /></el-icon> 模糊搜索
          </button>
          <button :class="{ active: mode === 'exact' }" @click="switchMode('exact')">
            <el-icon :size="14"><Aim /></el-icon> 精确匹配
          </button>
          <button :class="{ active: mode === 'batch' }" @click="switchMode('batch')">
            <el-icon :size="14"><List /></el-icon> 批量搜索
          </button>
        </div>

        <!-- Single search input -->
        <div v-if="mode !== 'batch'" class="search-input-wrap">
          <el-icon :size="18" class="search-prefix"><Search /></el-icon>
          <input
            ref="searchInput"
            v-model="query"
            type="text"
            placeholder="输入原料名称（中/英/INCI）..."
            @keydown.enter="doSearch"
            class="search-field"
          />
          <button v-if="query" class="clear-btn" @click="clearSearch">
            <el-icon><Close /></el-icon>
          </button>
        </div>

        <!-- Batch search textarea -->
        <div v-else class="batch-input-wrap">
          <div class="batch-header">
            <span class="batch-label">每行一个原料名，或用逗号分隔</span>
            <span class="batch-count" v-if="batchLines.length">{{ batchLines.length }} 个原料</span>
          </div>
          <textarea
            v-model="query"
            rows="5"
            placeholder="Retinol&#10;Salicylic Acid&#10;Decanediol, Peppermint&#10;Zinc Oxide"
            class="batch-textarea"
          ></textarea>
        </div>

        <button class="search-btn" @click="doSearch" :disabled="!query.trim()">
          <el-icon><Search /></el-icon> 搜索原料
        </button>

        <!-- Auto-fallback notice -->
        <div v-if="autoFallback" class="fallback-notice">
          <el-icon><Warning /></el-icon>
          精确匹配无结果，已自动切换为模糊搜索
          <button @click="mode='exact'; autoFallback=false">切回精确</button>
        </div>
      </div>
    </div>

    <!-- Batch result summary -->
    <div class="batch-summary" v-if="mode === 'batch' && batchTermStats.length > 0">
      <div class="batch-summary-title">批量搜索汇总</div>
      <div class="batch-term-list">
        <div v-for="stat in batchTermStats" :key="stat.term" class="batch-term-item" :class="{ zero: stat.count === 0 }">
          <span class="batch-term-name">{{ stat.term }}</span>
          <span class="batch-term-count">{{ stat.count }} 条</span>
        </div>
      </div>
    </div>

    <!-- Stats -->
    <div class="stats-bar" v-if="results.length > 0">
      <div class="stat-item">
        <span class="stat-num">{{ total }}</span>
        <span class="stat-label">匹配结果</span>
      </div>
      <div class="stat-item">
        <span class="stat-num">{{ uniqueReports }}</span>
        <span class="stat-label">涉及报告</span>
      </div>
      <div class="stat-item">
        <span class="stat-num">{{ uniqueIngredients }}</span>
        <span class="stat-label">匹配原料</span>
      </div>
    </div>

    <!-- Results -->
    <div class="results-area" v-if="results.length > 0">
      <div v-for="item in results" :key="item.ingredient_name + item.report_title" class="ingredient-card">
        <div class="card-header">
          <div class="ingredient-name-row">
            <span class="ingredient-name">{{ item.ingredient_name }}</span>
            <span v-if="item.inci_name && item.inci_name !== item.ingredient_name" class="inci-name">
              INCI: {{ item.inci_name }}
            </span>
            <span v-if="item.korean_name" class="korean-name">{{ item.korean_name }}</span>
          </div>
          <div class="card-badges">
            <span v-if="mode === 'batch' && item.search_term" class="search-term-badge">
              🔍 {{ item.search_term }}
            </span>
            <span class="source-badge" :class="item.source">{{ item.source }}</span>
          </div>
        </div>

        <div class="card-body">
          <div class="report-info">
            <el-icon :size="14"><Document /></el-icon>
            <span class="report-label">安全评估报告：</span>
            <a class="report-link" @click.stop="$router.push(`/document/${item.document_id}`)">
              {{ item.report_title }}
            </a>
          </div>
          <p v-if="item.match_context" class="match-context">{{ item.match_context }}</p>
        </div>

        <div class="card-actions">
          <el-button size="small" text @click.stop="$router.push(`/document/${item.document_id}`)">
            查看报告详情
          </el-button>
          <el-button size="small" text @click.stop="copyName(item.ingredient_name)">
            <el-icon :size="14"><CopyDocument /></el-icon> 复制名称
          </el-button>
        </div>
      </div>

      <!-- Pagination -->
      <div class="pagination-wrap" v-if="total > size">
        <el-pagination
          v-model:current-page="page"
          :page-size="size"
          :total="total"
          layout="total, prev, pager, next"
          background
          @current-change="doSearch"
        />
      </div>
    </div>

    <!-- Empty -->
    <div class="empty-area" v-else-if="searched">
      <el-icon :size="48" color="#d0d5dd"><Search /></el-icon>
      <h3>未找到匹配的原料</h3>
      <p>该原料可能不在当前数据范围内</p>
      <div class="empty-actions">
        <el-button size="small" @click="mode='fuzzy'; doSearch()">试试模糊搜索</el-button>
        <el-button size="small" type="primary" @click="query=''; results=[]; searched=false">重新输入</el-button>
      </div>
    </div>

    <!-- Initial placeholder -->
    <div class="initial-area" v-else>
      <div class="quick-tips">
        <h3>快速搜索示例</h3>
        <div class="tip-chips">
          <button v-for="t in exampleTerms" :key="t" class="tip-chip" @click="query=t; doSearch()">
            {{ t }}
          </button>
        </div>
        <p class="tip-hint">💡 支持中英文、INCI名、韩文名搜索。点击上方切换精确/批量模式。</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { Search, Close, Document, CopyDocument, Aim, List, Warning } from '@element-plus/icons-vue'
import { get } from '@/api/client'
import { ElMessage } from 'element-plus'

const query = ref('')
const mode = ref('fuzzy')
const results = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const size = ref(20)
const searched = ref(false)
const searchInput = ref<HTMLInputElement>()
const autoFallback = ref(false)

const exampleTerms = [
  'Decanediol', 'Salicylic Acid', 'Peppermint', 'Titanium Dioxide',
  'Glycerin', 'Zinc', 'Glycol', 'Sodium Hyaluronate'
]

const batchLines = computed(() => {
  if (mode.value !== 'batch') return []
  return query.value.split(/[\n,，]+/).map(s => s.trim()).filter(Boolean)
})

const batchTermStats = computed(() => {
  if (mode.value !== 'batch' || !results.value.length) return []
  const stats: Record<string, number> = {}
  for (const r of results.value) {
    const term = r.search_term || ''
    stats[term] = (stats[term] || 0) + 1
  }
  // Include terms with 0 results
  for (const term of batchLines.value) {
    if (!(term in stats)) stats[term] = 0
  }
  return Object.entries(stats).map(([term, count]) => ({ term, count }))
})

const uniqueReports = computed(() => new Set(results.value.map((r: any) => r.report_title)).size)
const uniqueIngredients = computed(() => new Set(results.value.map((r: any) => r.ingredient_name.toLowerCase())).size)

function switchMode(m: string) {
  mode.value = m
  autoFallback.value = false
  results.value = []
  total.value = 0
  searched.value = false
}

function clearSearch() {
  query.value = ''
  results.value = []
  total.value = 0
  searched.value = false
  autoFallback.value = false
}

async function doSearch() {
  if (!query.value.trim()) return
  searched.value = true
  page.value = 1
  results.value = []
  autoFallback.value = false

  try {
    const resp: any = await get('/api/cosmetics/ingredient-search', {
      q: query.value.trim(),
      mode: mode.value,
      page: page.value,
      size: size.value,
    })
    results.value = resp.items || []
    total.value = resp.total || 0

    // Auto-fallback: exact mode with 0 results → try fuzzy
    if (mode.value === 'exact' && total.value === 0) {
      const fuzzyResp: any = await get('/api/cosmetics/ingredient-search', {
        q: query.value.trim(),
        mode: 'fuzzy',
        page: 1,
        size: size.value,
      })
      if ((fuzzyResp.total || 0) > 0) {
        results.value = fuzzyResp.items || []
        total.value = fuzzyResp.total || 0
        autoFallback.value = true
      }
    }
  } catch (e) {
    results.value = []
    total.value = 0
    ElMessage.error('搜索失败，请稍后重试')
  }
}

function copyName(name: string) {
  navigator.clipboard.writeText(name).then(() => {
    ElMessage.success('已复制到剪贴板')
  }).catch(() => {
    ElMessage.warning('复制失败')
  })
}
</script>

<style scoped>
.ingredient-search-page {
  max-width: 900px;
  margin: 0 auto;
  padding: var(--spacing-lg) 0;
}

/* ── Hero ── */
.search-hero {
  text-align: center;
  padding: 40px 20px 32px;
  background: linear-gradient(135deg, #f0f5ff 0%, #e8f0fe 50%, #f5f0ff 100%);
  border-radius: 16px;
  margin-bottom: var(--spacing-lg);
}
.hero-icon { font-size: 48px; margin-bottom: 12px; }
.search-hero h1 {
  font-size: 24px;
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0 0 4px;
}
.hero-desc {
  font-size: 13px;
  color: var(--color-text-secondary);
  margin: 0 0 24px;
}

/* ── Search box ── */
.search-box { max-width: 640px; margin: 0 auto; }

.mode-toggles {
  display: flex;
  gap: 8px;
  justify-content: center;
  margin-bottom: 16px;
}
.mode-toggles button {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 18px;
  border: 1.5px solid var(--color-border);
  border-radius: 20px;
  background: #fff;
  font-size: 13px;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all .15s;
  font-family: inherit;
}
.mode-toggles button:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}
.mode-toggles button.active {
  background: var(--color-primary);
  color: #fff;
  border-color: var(--color-primary);
  font-weight: 600;
}

.search-input-wrap {
  display: flex;
  align-items: center;
  background: #fff;
  border: 2px solid var(--color-border);
  border-radius: 12px;
  padding: 0 14px;
  transition: border-color .2s;
  margin-bottom: 16px;
}
.search-input-wrap:focus-within {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(30, 80, 174, .08);
}
.search-prefix { color: var(--color-text-secondary); flex-shrink: 0; margin-right: 8px; }
.search-field {
  flex: 1;
  border: none;
  outline: none;
  padding: 12px 8px;
  font-size: 15px;
  color: var(--color-text-primary);
  background: transparent;
  font-family: inherit;
}
.search-field::placeholder { color: #c0c4cc; }
.clear-btn {
  background: none; border: none; cursor: pointer;
  color: #bbb; padding: 4px; display: flex; align-items: center;
}
.clear-btn:hover { color: #666; }

/* Batch input */
.batch-input-wrap {
  margin-bottom: 16px;
}
.batch-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
  padding: 0 4px;
}
.batch-label { font-size: 12px; color: var(--color-text-secondary); }
.batch-count {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-primary);
  background: rgba(30,80,174,.06);
  padding: 2px 10px;
  border-radius: 10px;
}
.batch-textarea {
  width: 100%;
  border: 2px solid var(--color-border);
  border-radius: 12px;
  padding: 12px 14px;
  font-size: 14px;
  color: var(--color-text-primary);
  background: #fff;
  font-family: 'Consolas', 'Monaco', monospace;
  resize: vertical;
  line-height: 1.7;
  transition: border-color .2s;
  box-sizing: border-box;
}
.batch-textarea:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(30, 80, 174, .08);
}
.batch-textarea::placeholder { color: #c0c4cc; font-family: inherit; }

.search-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 10px 32px;
  background: var(--color-primary);
  color: #fff;
  border: none;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  font-family: inherit;
  transition: all .2s;
}
.search-btn:hover { opacity: .9; transform: translateY(-1px); }
.search-btn:disabled { opacity: .5; cursor: not-allowed; transform: none; }

.fallback-notice {
  margin-top: 12px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 8px;
  font-size: 13px;
  color: #92400e;
}
.fallback-notice button {
  background: none;
  border: none;
  color: var(--color-primary);
  cursor: pointer;
  font-weight: 600;
  font-size: 12px;
  font-family: inherit;
  text-decoration: underline;
}

/* Batch summary */
.batch-summary {
  background: #fff;
  border-radius: 12px;
  padding: 16px 20px;
  margin-bottom: var(--spacing-md);
  box-shadow: 0 1px 3px rgba(0,0,0,.04);
}
.batch-summary-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-secondary);
  margin-bottom: 10px;
}
.batch-term-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.batch-term-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  border-radius: 16px;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  font-size: 13px;
}
.batch-term-item.zero {
  background: #fef2f2;
  border-color: #fecaca;
}
.batch-term-name {
  color: var(--color-text-primary);
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.batch-term-count {
  font-weight: 600;
  color: #16a34a;
}
.batch-term-item.zero .batch-term-count { color: #dc2626; }

/* ── Stats bar ── */
.stats-bar {
  display: flex;
  gap: 32px;
  justify-content: center;
  padding: 16px;
  background: #fff;
  border-radius: 12px;
  margin-bottom: var(--spacing-md);
  box-shadow: 0 1px 3px rgba(0,0,0,.04);
}
.stat-item { display: flex; flex-direction: column; align-items: center; }
.stat-num { font-size: 24px; font-weight: 700; color: var(--color-primary); }
.stat-label { font-size: 12px; color: var(--color-text-secondary); }

/* ── Ingredient cards ── */
.results-area { display: flex; flex-direction: column; gap: 10px; }
.ingredient-card {
  background: #fff; border-radius: 12px; padding: 16px 20px;
  border: 1px solid transparent; box-shadow: 0 1px 3px rgba(0,0,0,.04);
  transition: all .2s;
}
.ingredient-card:hover {
  border-color: var(--color-border);
  box-shadow: 0 4px 16px rgba(0,0,0,.06);
}
.card-header {
  display: flex; align-items: flex-start; justify-content: space-between;
  gap: 12px; margin-bottom: 10px;
}
.ingredient-name-row { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.ingredient-name { font-size: 16px; font-weight: 700; color: var(--color-text-primary); }
.inci-name {
  font-size: 12px; color: var(--color-primary);
  background: rgba(30, 80, 174, .06); padding: 2px 8px; border-radius: 4px;
  font-family: monospace;
}
.korean-name {
  font-size: 12px; color: #8b5cf6;
  background: rgba(139, 92, 246, .06); padding: 2px 8px; border-radius: 4px;
}
.source-badge {
  font-size: 11px; font-weight: 600; padding: 3px 10px; border-radius: 12px; flex-shrink: 0;
}
.source-badge.CIR { background: #ecfdf5; color: #059669; }
.source-badge.KCIA { background: #fef3c7; color: #d97706; }
.card-badges { display: flex; gap: 6px; align-items: center; flex-shrink: 0; }
.search-term-badge {
  font-size: 11px; font-weight: 500; padding: 3px 10px; border-radius: 12px;
  background: #eff6ff; color: #2563eb; flex-shrink: 0;
}
.card-body { margin-bottom: 8px; }
.report-info {
  display: flex; align-items: center; gap: 6px; margin-bottom: 6px;
  font-size: 13px; color: var(--color-text-secondary);
}
.report-label { flex-shrink: 0; }
.report-link {
  color: var(--color-primary); cursor: pointer; font-weight: 500;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.report-link:hover { text-decoration: underline; }
.match-context {
  font-size: 12.5px; color: #888; background: var(--color-bg-secondary);
  padding: 8px 12px; border-radius: 6px; border-left: 3px solid var(--color-primary);
  margin: 0; line-height: 1.5; max-height: 60px; overflow: hidden;
}
.card-actions { display: flex; gap: 8px; }

/* ── Pagination ── */
.pagination-wrap { display: flex; justify-content: center; padding: var(--spacing-md); }

/* ── Empty / Initial ── */
.empty-area, .initial-area { text-align: center; padding: 64px 24px; }
.empty-area h3, .initial-area h3 {
  font-size: 15px; color: var(--color-text-primary); margin: 12px 0 4px;
}
.empty-area p { font-size: 13px; color: var(--color-text-secondary); margin: 0 0 16px; }
.empty-actions { display: flex; gap: 8px; justify-content: center; }
.quick-tips { max-width: 560px; margin: 0 auto; }
.tip-chips { display: flex; gap: 8px; flex-wrap: wrap; justify-content: center; margin-top: 12px; }
.tip-chip {
  padding: 6px 16px; border: 1px solid var(--color-border); border-radius: 20px;
  background: #fff; font-size: 13px; color: var(--color-primary);
  cursor: pointer; font-family: inherit; transition: all .15s;
}
.tip-chip:hover { background: var(--color-primary); color: #fff; border-color: var(--color-primary); }
.tip-hint { font-size: 12px; color: #bbb; margin-top: 20px; }

@media (max-width: 768px) {
  .ingredient-search-page { padding: var(--spacing-md); }
  .search-hero { padding: 24px 16px; }
  .stats-bar { gap: 16px; }
}
</style>
