# 迈瑞生知识库 — 开发需求规格说明书 (PM → Dev / AI)

> **角色**: 项目经理
> **读者**: 开发工程师 / AI Coding Agent
> **用法**: 每个需求的提示词可直接复制使用，包含 UI 设计、数据流、验收标准
> **项目路径**: `d:\workSpace\marweis-kb`

---

## 🎨 品牌设计系统 (提取自 maris-reg.com 官网)

> 以下色值从官网 `www.maris-reg.com` 实际 CSS 中提取。KB 当前主色 `#c88a04` 与官网主色 `#1e50ae` 不一致，需要在本次迭代中统一。

### 色板

| 用途 | 色值 | 预览 | 来源 |
|------|------|------|------|
| **主色 (Primary)** | `#1e50ae` | ████████ | 官网导航/按钮/链接 |
| **金色强调 (Gold)** | `#ffc001` | ████████ | 官网 active 状态/高亮 |
| **橙色强调 (Orange)** | `#fb8c00` | ████████ | 官网重点文字(36px标题) |
| **红色警示 (Red)** | `#c40000` | ████████ | 官网重要提示 |
| **深色文字** | `#333333` | ████████ | 官网正文 |
| **次要文字** | `#9e9e9e` | ████████ | 官网辅助信息 |
| **浅灰边框** | `#dedede` | ████████ | 官网分割线/边框 |
| **白色背景** | `#ffffff` | ████████ | 官网卡片/内容区 |

### 字体

| 用途 | 字体 | 来源 |
|------|------|------|
| 中文正文 | 微软雅黑, Microsoft YaHei | 官网 `<span face="微软雅黑, Microsoft YaHei">` |
| 装饰字体 | 胡晓波真帅体 | 官网 banner 标题 |
| 英文/数字 | Alibaba Sans Medium | 官网 fontface |

### Logo

官网 Logo 为图片型：`//17012616.s21i.faiusr.com/4/4/ABUIABAEGAAguoGzsAYoyZzA0wUwwAc4oAQ.png`
KB 可使用简化的 "M" 字母图标（当前已实现）+ 品牌色 `#1e50ae`。

### 设计系统 CSS 变量映射

```css
:root {
  --color-primary: #1e50ae;        /* 原 #c88a04 → 改为官网蓝 */
  --color-primary-light: #3a7bd5;  /* 浅蓝 hover */
  --color-primary-dark: #0d3b7a;   /* 深蓝 active */
  --color-accent: #ffc001;         /* 金色强调（保留金色体系）*/
  --color-accent-light: #ffd54f;
  --color-orange: #fb8c00;         /* 橙色重点 */
  --color-danger: #c40000;         /* 红色警示 */
  --color-bg: #ffffff;
  --color-bg-secondary: #f5f7fa;
  --color-text-primary: #333333;
  --color-text-secondary: #9e9e9e;
  --color-border: #dedede;
}
```

### 各模块配色方案（部门侧边栏）

| 部门 | 图标 | 主色 | 强调色 |
|------|:---:|------|--------|
| 器械注册部 | M | `#1e50ae` (品牌蓝) | `#ffc001` (品牌金) |
| 临床评价部 | C | `#2e86c1` (浅蓝) | `#5dade2` |
| 临床试验部 | T | `#27ae60` (绿) | `#58d68d` |
| 生产体系部 | Q | `#8e44ad` (紫) | `#af7ac5` |
| 化妆品·医美部 | B | `#e74c3c` (红) | `#f1948a` |
| 特医食品部 | F | `#fb8c00` (品牌橙) | `#f8c471` |
| 管理层 | A | `#333333` (深灰) | `#9e9e9e` |

---

## 目录

0. [需求 0: 品牌色系统一（全站 UI 对齐官网）](#需求0)
1. [需求 1: CategoryView 搜索功能修复](#需求1)
2. [需求 2: 文档预览完整方案（调试 + 容错 + UI 升级）](#需求2)
3. [需求 3: 数据库索引优化](#需求3)
4. [需求 4: 全部门工作流侧边栏](#需求4)
5. [需求 5: 系统设置持久化（后端 API + 前端对接）](#需求5)
6. [需求 6: 通讯录模块卡片式展示](#需求6)
7. [需求 7: 批量文档导入 UI](#需求7)
8. [需求 8: 首页个性化 + 统计仪表盘](#需求8)
9. [需求 9: Meilisearch 健康监控 + 管理面板](#需求9)
10. [需求 10: UI/UX 全面优化](#需求10)

---

## <a id="需求0"></a>需求 0: 品牌色系统一 — 全站 UI 对齐官网

**优先级**: P0 (品牌一致性) | **工时**: 2h

### 📋 问题
知识库当前主色 `#c88a04`（金棕色）与公司官网 `maris-reg.com` 的主色 `#1e50ae`（医疗蓝）不一致。需要统一到官网品牌色，保持企业视觉一致性。

### 🔧 实现方案

**1. CSS 变量更新** `frontend/src/styles/global.css`:

```css
:root {
  --color-primary: #1e50ae;        /* 原 #c88a04 → 官网医疗蓝 */
  --color-primary-light: #3a7bd5;  /* hover 浅蓝 */
  --color-primary-dark: #0d3b7a;   /* active 深蓝 */
  --color-accent: #ffc001;         /* 官网金色强调 */
  --color-accent-light: #ffd54f;
  --color-orange: #fb8c00;         /* 官网橙色重点 */
  --color-danger: #c40000;         /* 官网红色 */
  --color-bg: #ffffff;
  --color-bg-secondary: #f5f7fa;
  --color-text-primary: #333333;   /* 官网正文色 */
  --color-text-secondary: #9e9e9e; /* 官网辅助文字 */
  --color-border: #dedede;
}
```

**2. 各页面色值替换**:
- 登录/注册页背景渐变: `#0d3b7a → #1e50ae → #3a7bd5`
- 首页 Hero Banner: `background: linear-gradient(135deg, #1e50ae 0%, #0d3b7a 100%)`
- 按钮/链接/Tag: 全部改用 `--color-primary`
- 侧边栏部门图标背景: `--color-primary`
- 搜索高亮: `background: #fff3cd` (保留，与金色强调协调)

**3. Logo 图标保持 "M" 字母** — 官网 Logo 是图片，KB 使用简化的字母图标即可。

**改动文件**:
- `frontend/src/styles/global.css` — CSS 变量更新
- `frontend/src/views/LoginView.vue` — 背景渐变
- `frontend/src/views/RegisterView.vue` — 背景渐变
- `frontend/src/views/HomeView.vue` — Hero banner 渐变
- `frontend/src/components/layout/AppHeader.vue` — Logo 图标色
- `frontend/src/components/layout/WorkflowSidebar.vue` — 部门图标色
- `frontend/src/views/admin/AdminLayout.vue` — 侧边栏激活色

**验收标准**:
- [ ] 全站主色从 `#c88a04` 切换为 `#1e50ae`
- [ ] 按钮 hover/active 状态颜色正确
- [ ] 登录/注册页渐变与新主色协调
- [ ] 侧边栏激活状态颜色与新系统一致
- [ ] 所有页面无残留旧色值

---

## <a id="需求1"></a>需求 1: CategoryView 搜索功能修复

**优先级**: P0 (Bug) | **工时**: 2h

### 📋 问题
分类页面搜索框输入关键词后，前端传 `params.keyword` 到 `GET /api/documents`，但后端不认识这个参数，搜索无效。

### 🎨 UI 设计（保持现状，只修逻辑）

```
┌─────────────────────────────────────────────────────────┐
│ 首页 > 参考文件                                          │
│                                                         │
│ [全部] [通用法规（国内）] [通用法规（国外）] [指导原则] [审评论坛] │
│                                                         │
│ 🔍 在当前分类下搜索...  [×清除]    文件格式: [全部 ▾]    │
│                                                         │
│ ┌─ 文档列表 ──────────────────────────────────────────┐ │
│ │ 📄 医疗器械监督管理条例（2025修订）                    │ │
│ │    张三 · 2026-07-14 · PDF                           │ │
│ │    明确了医疗器械全生命周期监管要求...                  │ │
│ ├─────────────────────────────────────────────────────┤ │
│ │ ...更多文档...                                        │ │
│ └─────────────────────────────────────────────────────┘ │
│                              < 1  2  3 ... 10 >        │
└─────────────────────────────────────────────────────────┘
```

### 🔧 实现方案

**前端** `frontend/src/views/CategoryView.vue`:

1. 搜索框 `@change="doLoad"` 改为搜索时调用 `/api/search` 而非 `/api/documents`
2. 在 `doLoad()` 方法中判断：如果 `searchKeyword` 有值，走 search API；否则走 documents API

```typescript
// 修改 doLoad 中的数据获取逻辑
async function doLoad() {
  loading.value = true
  try {
    const catId = activeSubId.value || (currentCat.value?.id || '')
    let resp: any

    if (searchKeyword.value.trim()) {
      // 有搜索词 → 走搜索 API，限定当前分类
      const params: any = {
        q: searchKeyword.value.trim(),
        page: page.value,
        size: size.value,
      }
      if (catId) params.category_id = catId
      if (fileTypeFilter.value) params.file_type = fileTypeFilter.value
      resp = await get('/api/search', params)
    } else {
      // 无搜索词 → 走文档列表 API
      const params: any = {
        page: page.value, size: size.value,
        sort: 'updated_at', order: 'desc',
      }
      if (catId) params.category_id = catId
      if (fileTypeFilter.value) params.file_type = fileTypeFilter.value
      resp = await get('/api/documents', params)
    }

    docs.value = resp.items || []
    total.value = resp.total || 0
  } catch { docs.value = []; total.value = 0 }
  loading.value = false
}
```

**改动文件**: 仅 `frontend/src/views/CategoryView.vue` 的 `doLoad()` 函数

**验收标准**:
- [ ] 搜索框输入 "注册" 回车 → 列出标题/摘要含 "注册" 的文档
- [ ] 清空搜索框 → 恢复该分类的全部文档
- [ ] 搜索 + 文件格式筛选可组合使用
- [ ] 分页在搜索结果间正常切换

---

## <a id="需求2"></a>需求 2: 文档预览完整方案

**优先级**: P0 (功能缺陷 + 体验提升) | **工时**: 1天

### 📋 问题
1. 后端 PDF 预览正常（200 + PDF stream），但前端 iframe 可能不显示
2. 无预览时的 fallback 体验差
3. Token 过期无提示

### 🎨 UI 设计

**状态 1: PDF 预览正常**
```
┌──────────────────────────────────────────────────────┐
│ 首页 > 知识库 > 医疗器械监督管理条例                    │
├──────────────────────────────────────────────────────┤
│ ┌─ PDF 预览区 ────────────────────────────────────┐  │
│ │                                                  │  │
│ │   [PDF 内嵌显示，支持翻页/缩放]                    │  │
│ │                                                  │  │
│ └──────────────────────────────────────────────────┘  │
│ [📥 下载原件] [🔗 复制链接] [⭐ 收藏]                  │
│ ┌──────────────────────────────────────────────────┐  │
│ │ 上传者: 张三  │ 更新时间: 2026-07-14              │  │
│ │ 文件格式: PDF │ 文件大小: 2.3 MB                  │  │
│ │ 来源: NMPA   │ 版本: 2025修订                     │  │
│ │ 浏览次数: 127 │ 下载次数: 34                      │  │
│ └──────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘
```

**状态 2: 预览加载中**
```
┌──────────────────────────────────────────────────────┐
│                                                      │
│              ◌ 正在加载预览...                         │
│         文档较大，首次转换可能需要 10-30 秒              │
│                                                      │
└──────────────────────────────────────────────────────┘
```

**状态 3: 不支持预览的文件类型**
```
┌──────────────────────────────────────────────────────┐
│                                                      │
│          📦 此文件格式不支持在线预览                     │
│          (.dwg 为 CAD 工程文件)                        │
│                                                      │
│          [📥 下载原件查看]                             │
│                                                      │
│  ┌──────────────────────────────────────────────┐    │
│  │ 文件信息                                      │    │
│  │ 名称: 产品图纸.dwg                            │    │
│  │ 大小: 15.8 MB                                │    │
│  │ 上传者: 王五 · 2026-06-20                    │    │
│  └──────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────┘
```

**状态 4: Token 过期 / 加载超时**
```
┌──────────────────────────────────────────────────────┐
│                                                      │
│          ⚠️ 预览加载失败                              │
│          预览令牌已过期，请刷新页面重试                  │
│                                                      │
│          [🔄 刷新页面]  [📥 下载原件]                 │
│                                                      │
└──────────────────────────────────────────────────────┘
```

### 🔧 实现方案

**前端** `frontend/src/views/DocumentView.vue`:

1. **Token 获取容错**:
```typescript
async function fetchPreviewToken(docId: string) {
  if (!auth.isLoggedIn) return
  try {
    const resp: any = await get(`/api/documents/${docId}/preview-token`)
    previewToken.value = resp.token
    previewUrl.value = `/api/documents/${docId}/preview?token=${encodeURIComponent(resp.token)}`
  } catch {
    // Fallback: 使用完整 JWT
    previewUrl.value = `/api/documents/${docId}/preview?token=${encodeURIComponent(auth.token)}`
  }
}
```

2. **加载状态**: 新增 `previewLoading` ref，iframe `@load` 事件设 `previewLoading = false`

3. **超时处理**: 15 秒后仍 `previewLoading` → 显示 "加载超时" 提示

4. **不支持预览的文件**: 检测 `file_ext` 是否在可预览列表中 → 显示特殊占位 UI

5. **新增加载状态 UI**:
```html
<!-- 加载中 -->
<div v-if="previewLoading" class="preview-loading">
  <el-icon class="is-loading" :size="32"><Loading /></el-icon>
  <p>正在加载预览...</p>
  <p class="hint">文档较大时首次转换可能需要 10-30 秒</p>
</div>

<!-- 超时 -->
<div v-else-if="previewTimeout" class="preview-error">
  <el-result icon="warning" title="预览加载超时"
    sub-title="请刷新页面重试，或直接下载查看">
    <template #extra>
      <el-button @click="loadDoc">刷新页面</el-button>
      <el-button type="primary" @click="doDownload">下载原件</el-button>
    </template>
  </el-result>
</div>

<!-- 不支持预览 -->
<div v-else-if="!isPreviewSupported" class="preview-unsupported">
  ...
</div>
```

**改动文件**:
- `frontend/src/views/DocumentView.vue` — 全部改动在此

**验收标准**:
- [ ] PDF 文件上传后能在详情页 iframe 中正常预览
- [ ] 不支持预览的文件显示专用占位 UI，提示用户下载
- [ ] Token 获取失败时自动使用完整 JWT 回退
- [ ] 加载超过 15 秒显示超时提示
- [ ] iframe 加载成功后隐藏 loading

---

## <a id="需求3"></a>需求 3: 数据库索引优化

**优先级**: P1 (性能) | **工时**: 1h

### 📋 问题
现有 ~2000 篇文档，无业务索引。随数据增长，分类维度和权限过滤查询将变慢。

### 🔧 实现方案

创建 Alembic 迁移：`cd backend && alembic revision --autogenerate -m "add_performance_indexes"`

在生成的迁移文件中补充以下索引：

```python
# backend/alembic/versions/xxxx_add_performance_indexes.py

def upgrade():
    # documents — 最常查询的表
    op.create_index('idx_docs_cat_deleted', 'documents',
        ['category_id', 'is_deleted'])
    op.create_index('idx_docs_uploader_deleted', 'documents',
        ['uploader_id', 'is_deleted'])
    op.create_index('idx_docs_deleted_updated', 'documents',
        ['is_deleted', text('updated_at DESC')])
    op.create_index('idx_docs_title_trgm', 'documents',
        ['title'], postgresql_using='gin',
        postgresql_ops={'title': 'gin_trgm_ops'})  # 需 CREATE EXTENSION pg_trgm

    # favorites — 高频查询
    op.create_index('idx_fav_user_doc', 'favorites',
        ['user_id', 'document_id'])

    # browse_history — 按用户+时间查询
    op.create_index('idx_history_user_time', 'browse_history',
        ['user_id', text('created_at DESC')])

    # categories — 树查询
    op.create_index('idx_cats_parent', 'categories', ['parent_id'])

def downgrade():
    op.drop_index('idx_docs_cat_deleted')
    op.drop_index('idx_docs_uploader_deleted')
    op.drop_index('idx_docs_deleted_updated')
    op.drop_index('idx_docs_title_trgm')
    op.drop_index('idx_fav_user_doc')
    op.drop_index('idx_history_user_time')
    op.drop_index('idx_cats_parent')
```

**验收标准**:
- [ ] `alembic upgrade head` 执行成功
- [ ] `alembic downgrade -1` 回滚成功
- [ ] 文档列表查询 `EXPLAIN ANALYZE` 确认使用索引

---

## <a id="需求4"></a>需求 4: 全部门工作流侧边栏

**优先级**: P1 (功能缺失) | **工时**: 2天

### 📋 问题
仅器械注册部有工作流侧边栏。其他 6 个部门的员工看不到任何侧边栏导航。

### 🏛 器械注册工作流设计依据

> 参考 [CMDE 器审中心注册申报流程](https://www.cmde.org.cn/sqrzc/zxfw/lcjtcn/index.html)
> 页面结构采用**横向步骤导航** + **纵向详细内容**的布局。

**CMDE 官方注册流程 (7步)**:

```
受理前咨询 → 注册申报(eRPS) → 受理审查(5工作日) → 技术审评 → 发补后咨询 → 行政审批 → 制证送达
```

**现有 KB 7 模块 vs CMDE 流程对照**:

| 序号 | KB 模块 | 对应 CMDE 阶段 | 覆盖内容 |
|:---:|------|:---:|------|
| 1 | 参考文件 | 受理前咨询 + 全流程 | 法规库、指导原则、审评论坛 |
| 2 | 分类目录 | 受理前咨询 | NMPA 分类界定 |
| 3 | 校验技术要求 | 技术审评 | 产品技术要求编写 |
| 4 | 临床评价资料 | 技术审评 | CER、临床文献、说明书 |
| 5 | 发补 | 发补后咨询 | 例卷、发补意见回复策略 |
| 6 | 注册证书 | 行政审批+制证 | 证书管理、注册资料 |
| 7 | 通讯录 | 全流程 | 监管机构联系方式 |

**优化方向**: KB 模块名保持简洁（面向内部员工），子分类增加 CMDE 流程阶段的提示说明（hover tooltip），帮助新员工理解每个模块在注册流程中的位置。

### 🎨 UI 设计 (工作流侧边栏详细)

**导航栏布局（横向顶部导航 + 左侧工作流侧边栏）**:

**顶部横向导航**:
```
┌──────────────────────────────────────────────────────────────┐
│ [M] 迈瑞生知识库 │ 首页 │ 管理后台 │  🔍搜索... │ [👤 张三 ▾] │
└──────────────────────────────────────────────────────────────┘
```

**主内容区 = 左侧工作流侧边栏 + 右侧内容**:
```
┌──────────────┬───────────────────────────────────────────┐
│ [M] 器械注册部│  首页 > 参考文件 > 通用法规（国内）        │
│   工作台      │                                          │
├──────────────┤  ┌──────────────────────────────────────┐ │
│ ▶ 📁 参考文件 │  │ 📄 医疗器械监督管理条例（2025修订）    │ │
│              │  │    张三 · 2026-07-14 · PDF             │ │
│              │  ├──────────────────────────────────────┤ │
│ ▶ 📁 分类目录 │  │ 📄 医疗器械注册管理办法               │ │
│              │  │    ...                                │ │
│ ▼ 📁 临床评价 │  └──────────────────────────────────────┘ │
│   ├ 临床文献  │                                          │
│   ├ 国家局网站│          < 1  2  3 ... 10 >              │
│   └ 说明书    │                                          │
│ ▶ 📁 发补     │                                          │
│ ▶ 📁 注册证书 │                                          │
│ ▶ 📁 通讯录   │                                          │
├──────────────┤                                          │
│ 🌐 公共知识区 │                                          │
└──────────────┴───────────────────────────────────────────┘

导航说明:
- 横向顶部: 全局导航（首页/管理后台/搜索/用户）
- 左侧侧边栏: 部门工作流导航（仅当前部门可见）  
- 右侧内容区: 文档列表/详情
```

**各科室侧边栏配色方案** (已对齐官网品牌色系统):

| 部门 | 图标 | 主色 | 子项激活色 |
|------|:---:|------|--------|
| 器械注册部 | M | `#1e50ae` | `#ffc001` |
| 临床评价部 | C | `#2e86c1` | `#5dade2` |
| 临床试验部 | T | `#27ae60` | `#58d68d` |
| 生产体系部 | Q | `#8e44ad` | `#af7ac5` |
| 化妆品·医美部 | B | `#e74c3c` | `#f1948a` |
| 特医食品部 | F | `#fb8c00` | `#f8c471` |
| 管理层 | A | `#333333` | `#9e9e9e` |

### 🔧 实现方案

**1. 后端** `backend/app/api/categories.py` — 无需改动，`GET /api/categories` 已按部门过滤

**2. 前端** `frontend/src/components/layout/MainLayout.vue`:

```typescript
// 扩展支持所有部门
const WORKFLOW_DEPTS = [
  '器械注册部', '临床评价部', '临床试验部', '生产体系部',
  '化妆品·医美部', '特医食品部', '管理层',
]
const showSidebar = computed(() => {
  if (auth.isAdmin) return true
  const dept = auth.user?.department
  return dept ? WORKFLOW_DEPTS.includes(dept) : false
})
```

**3. 前端** `frontend/src/components/layout/WorkflowSidebar.vue` — 重构为动态部门:

```typescript
// 部门配置映射
const DEPT_CONFIG: Record<string, { icon: string; label: string; color: string; accentColor: string }> = {
  '器械注册部':  { icon: 'M', label: '工作台', color: '#c88a04', accentColor: '#e6a817' },
  '临床评价部':  { icon: 'C', label: 'CER工作台', color: '#2e86c1', accentColor: '#5dade2' },
  '临床试验部':  { icon: 'T', label: 'CRO工作台', color: '#27ae60', accentColor: '#58d68d' },
  '生产体系部':  { icon: 'Q', label: '质量工作台', color: '#8e44ad', accentColor: '#af7ac5' },
  '化妆品·医美部': { icon: 'B', label: '美妆工作台', color: '#e74c3c', accentColor: '#f1948a' },
  '特医食品部':  { icon: 'F', label: '食品工作台', color: '#f39c12', accentColor: '#f8c471' },
  '管理层':      { icon: 'A', label: '管理驾驶舱', color: '#1e293b', accentColor: '#64748b' },
}

// 动态获取当前部门的配置
const deptConfig = computed(() => {
  const dept = auth.user?.department
  const isAdmin = auth.isAdmin
  // 管理员默认显示器械注册部视角，或选择第一个有编号模块的部门
  if (isAdmin) return DEPT_CONFIG['器械注册部']
  return DEPT_CONFIG[dept || ''] || DEPT_CONFIG['器械注册部']
})

// 部门名称
const deptName = computed(() => auth.isAdmin ? '器械注册部' : (auth.user?.department || ''))
```

模板中的侧边栏头改为动态：
```html
<div class="sidebar-header">
  <div class="dept-icon" :style="{ background: deptConfig.color }">
    {{ deptConfig.icon }}
  </div>
  <div class="dept-info">
    <span class="dept-name">{{ deptName }}</span>
    <span class="dept-label">{{ deptConfig.label }}</span>
  </div>
</div>
```

子分类高亮色也使用动态色：
```css
.sub-item.active { color: v-bind('deptConfig.accentColor'); }
```

**改动文件**:
- `frontend/src/components/layout/MainLayout.vue` — 扩展 WORKFLOW_DEPTS
- `frontend/src/components/layout/WorkflowSidebar.vue` — 动态部门配置

**验收标准**:
- [ ] 器械注册部员工 → 看到 7 模块金色侧边栏
- [ ] 临床评价部员工 → 看到 CER 分类蓝色侧边栏
- [ ] 管理层员工 → 看到管理专区深色侧边栏
- [ ] super_admin → 看到器械注册部侧边栏（默认）
- [ ] 同一用户切换部门后侧边栏更新

---

## <a id="需求5"></a>需求 5: 系统设置持久化

**优先级**: P2 (功能缺失) | **工时**: 1.5天

### 📋 问题
管理后台"系统设置"纯前端占位，保存不持久化。

### 🎨 UI 设计

```
┌──────────────────────────────────────────────────────────┐
│ [M] 管理后台 │ 文档管理 │ 分类管理 │ 用户管理 │ 系统设置 │ [返回前台] │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  (页面内容区)                                            │
│                                                          │
└──────────────────────────────────────────────────────────┘
```
**导航设计规范**:
- 全站统一使用**横向顶部导航**（与官网 maris-reg.com 一致）
- 管理后台：横向标签式导航，当前页高亮品牌蓝底部条
- 前台主站：Logo + 首页/管理后台 + 搜索框 + 用户头像
- 不使用竖式侧边栏作为主导航

### 🎨 UI 设计 (系统设置表单)

```
┌─ 系统设置 ──────────────────────────────────────────┐
│ [基本设置] [文件与存储] [数据库与索引]                │
├─────────────────────────────────────────────────────┤
│                                                     │
│ 站点名称    [迈瑞生知识库_______________]             │
│                                            │
│ 站点描述    [医疗器械注册·临床评价·_______]   │
│            [临床试验·法规库______________]   │
│                                            │
│ 主色调      [■ #c88a04]  (颜色选择器)       │
│                                            │
│ 页头Slogan [专业法规知识管理平台_________]   │
│                                            │
│ 页脚信息    [©2026 北京迈瑞生医药科技____]   │
│            [有限公司 版权所有|400-853-5405]   │
│                                            │
│ Logo       [选择文件] 未选择文件             │
│            ┌──────────┐                    │
│            │ [M] 预览  │                    │
│            └──────────┘                    │
│                                            │
│            [保存设置]                       │
└────────────────────────────────────────────┘
```

### 🔧 实现方案

**1. 数据库**: 新建 `system_config` 表

```python
# backend/app/models/system_config.py
class SystemConfig(Model, Base):
    __tablename__ = "system_config"
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
```

**2. 后端 API**:

```python
# backend/app/api/system.py
router = APIRouter()

@router.get("/settings")
async def get_settings(db: AsyncSession = Depends(get_db),
    current_user = Depends(require_role("super_admin"))):
    result = await db.execute(select(SystemConfig))
    configs = {row.key: row.value for row in result.scalars().all()}
    return configs

@router.put("/settings")
async def update_settings(body: dict,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_role("super_admin"))):
    for key, value in body.items():
        existing = await db.get(SystemConfig, key)
        if existing:
            existing.value = str(value)
        else:
            db.add(SystemConfig(key=key, value=str(value)))
    await db.commit()
    return {"message": "设置已保存"}
```

在 `main.py` 注册路由: `app.include_router(system.router, prefix="/api/admin", tags=["系统设置"])`

**3. 前端** `SystemSettings.vue`:

```typescript
// 页面加载时读取配置
onMounted(async () => {
  try {
    const resp = await get('/api/admin/settings')
    if (resp && Object.keys(resp).length > 0) {
      Object.assign(config, resp)
    }
  } catch {}
})

// 保存
async function saveGeneral() {
  try {
    await put('/api/admin/settings', {
      site_name: config.site_name,
      site_description: config.site_desc,
      primary_color: config.primary_color,
      accent_color: config.accent_color,
      slogan: config.slogan,
      footer_info: config.footer,
    })
    ElMessage.success('设置已保存')
    // 动态更新 CSS 变量
    document.documentElement.style.setProperty('--color-primary', config.primary_color)
  } catch { ElMessage.error('保存失败') }
}
```

**4. 配置项在应用启动时加载**:

```python
# backend/app/config.py 新增
async def load_system_config():
    """从数据库加载系统配置覆盖默认值"""
    # 在 app startup event 中调用
```

**改动文件**:
- 新建 `backend/app/models/system_config.py`
- 新建 `backend/app/api/system.py`
- `backend/app/main.py` — 注册路由
- `backend/app/models/__init__.py` — 导出新模型
- `frontend/src/views/admin/SystemSettings.vue` — 对接 API

**验收标准**:
- [ ] 修改站点名称 → 保存 → 刷新 → 名称保持
- [ ] 修改主色调 → 保存 → 前端即时应用新颜色
- [ ] 只有 super_admin 可以修改
- [ ] 空数据库时使用代码中的默认值

---

## <a id="需求6"></a>需求 6: 通讯录模块卡片式展示

**优先级**: P2 (新功能) | **工时**: 1天

### 🎨 UI 设计

```
首页 > 通讯录 > 中央药监局

┌──────────────────────────────────────────────────────────┐
│ 🔍 搜索机构...                                          │
│                                                          │
│ ┌─────────────────────┐ ┌─────────────────────┐         │
│ │ 🏛 国家药监局(NMPA)  │ │ 🏛 器审中心(CMDE)   │         │
│ │ 北京市西城区展览路   │ │ 北京市海淀区气象路   │         │
│ │ 北露园1号            │ │ 50号                  │         │
│ │ 📞 010-88330000      │ │ 📞 010-86452900      │         │
│ │ 🌐 www.nmpa.gov.cn  │ │ 🌐 www.cmde.org.cn  │         │
│ │ 📝 医疗器械注册审批   │ │ 📝 技术审评/指导原则  │         │
│ │ [访问官网] [详情]    │ │ [访问官网] [详情]    │         │
│ └─────────────────────┘ └─────────────────────┘         │
│ ┌─────────────────────┐ ┌─────────────────────┐         │
│ │ 🏛 北京市药监局      │ │ 🏛 中检院            │         │
│ │ ...                  │ │ ...                  │         │
│ └─────────────────────┘ └─────────────────────┘         │
└──────────────────────────────────────────────────────────┘
```

### 🔧 实现方案

**1. 数据存储** (复用 Document 表): 每张通讯录卡片存储为一个 `file_type: "link"` 的 Document，`summary` 字段存放结构化 JSON:

```json
{
  "type": "contact",
  "org_name": "国家药品监督管理局",
  "short_name": "NMPA",
  "address": "北京市西城区展览路北露园1号",
  "phone": "010-88330000",
  "website": "https://www.nmpa.gov.cn",
  "department": "医疗器械注册管理司",
  "notes": "负责医疗器械注册审批、标准制定"
}
```

**2. 前端**: 新建 `frontend/src/views/ContactView.vue`

```vue
<template>
  <div class="contact-page">
    <el-breadcrumb>...</el-breadcrumb>
    <el-input v-model="searchText" placeholder="搜索机构..." />
    <div class="contact-grid">
      <div v-for="card in contacts" :key="card.id" class="contact-card">
        <div class="card-header">
          <span class="org-icon">🏛</span>
          <h3>{{ card.data.org_name }}</h3>
          <el-tag size="small">{{ card.data.short_name }}</el-tag>
        </div>
        <div class="card-body">
          <p v-if="card.data.address">📍 {{ card.data.address }}</p>
          <p v-if="card.data.phone">📞 {{ card.data.phone }}</p>
          <p v-if="card.data.website">🌐 {{ card.data.website }}</p>
          <p v-if="card.data.notes" class="notes">{{ card.data.notes }}</p>
        </div>
        <div class="card-footer">
          <el-button size="small" @click="openWebsite(card.data.website)">
            访问官网
          </el-button>
          <el-button size="small" @click="showDetail(card)">详情</el-button>
        </div>
      </div>
    </div>
  </div>
</template>
```

**3. 路由**: 在 `CategoryView.vue` 中检测通讯录分类，自动切换到 `ContactView`:

```typescript
// 在 loadCategory 中判断
const CONTACT_CATEGORY_IDS = ['通讯录分类的UUID'] // 或通过分类名判断
if (CONTACT_CATEGORY_IDS.includes(id)) {
  router.replace({ name: 'Contact', params: { id } })
}
```

或者更简单的方式：给通讯录分类加一个约定，如 `name` 包含 "通讯录" 时自动切换为卡片模式。

**4. CSS 卡片布局**:
```css
.contact-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 16px;
}
.contact-card {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  box-shadow: var(--shadow-card);
  transition: all 0.2s;
}
.contact-card:hover {
  box-shadow: var(--shadow-hover);
  transform: translateY(-2px);
}
```

**改动文件**:
- 新建 `frontend/src/views/ContactView.vue`
- `frontend/src/router/index.ts` — 新增 Contact 路由
- `frontend/src/views/CategoryView.vue` — 检测通讯录分类，切换视图

**验收标准**:
- [ ] 通讯录分类显示为卡片网格
- [ ] 每张卡片含机构名称、地址、电话、网址
- [ ] 搜索框可过滤卡片
- [ ] 点击网址新标签打开

---

## <a id="需求7"></a>需求 7: 批量文档导入

**优先级**: P3 (效率工具) | **工时**: 3天

### 🎨 UI 设计

**入口**: 管理后台 → 文档管理 → "批量导入"按钮

```
┌──────────────────────────────────────────────────────────────┐
│ 批量导入文档                                          [✕ 关闭] │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  目标分类: [选择分类 ▾]                                      │
│  默认标签: [法规, 2025, NMPA____________] (逗号分隔)         │
│  默认来源: [NMPA________________________]                    │
│                                                              │
│  ┌─ 拖拽文件到此处或点击选择 ─────────────────────────────┐  │
│  │                                                        │  │
│  │     📁 将文件拖到此处                                   │  │
│  │     支持 PDF/Word/Excel/PPT/TXT/图片 (单文件≤500MB)     │  │
│  │                                                        │  │
│  │     [选择文件]                                          │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  上传队列 (3/5):                                             │
│  ┌──────────────────────────────────────────────────────────┐│
│  │ 文件名                    │ 大小    │ 状态              ││
│  │ 审评报告_2024_001.pdf     │ 2.3 MB │ ✅ 上传成功       ││
│  │ 指导原则_有源器械.docx    │ 850 KB │ ✅ 上传成功       ││
│  │ 注册指南_IVD_2025.pdf    │ 1.2 MB │ ◌ 正在处理...     ││
│  │ 分类目录_2024.pdf        │ 5.1 MB │ ⏳ 等待中          ││
│  │ 技术文件_附件A.pdf       │ 0.5 MB │ ❌ 文件过大(>500M) ││
│  └──────────────────────────────────────────────────────────┘│
│                                                              │
│  标题生成规则:                                                │
│  (●) 使用文件名(去掉扩展名)  ( ) 手动编辑每个标题             │
│                                                              │
│  [开始上传]  已完成 2/5，失败 1                              │
└──────────────────────────────────────────────────────────────┘
```

### 🔧 实现方案

**1. 后端**: 新增批量上传接口

```python
# backend/app/api/documents.py

@router.post("/batch")
async def batch_create_documents(
    category_id: str = Form(None),
    tags: str = Form("[]"),
    source: str = Form(None),
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("super_admin", "dept_admin", "editor")),
):
    """批量上传，每个文件独立处理。返回成功/失败统计。"""
    common_tags = json.loads(tags) if isinstance(tags, str) else (tags or [])
    results = {"succeeded": [], "failed": []}

    for file in files:
        try:
            title = os.path.splitext(file.filename or "untitled")[0].replace("_", " ")
            # 复用单文件上传逻辑
            content = await file.read()
            result = await FileService.upload_and_convert(
                content, file.filename or "unknown", file.content_type or ""
            )
            doc = Document(
                title=title, category_id=cat_uuid,
                file_type="file", tags=common_tags, source=source,
                uploader_id=current_user.id, ...
            )
            db.add(doc)
            await db.flush()
            results["succeeded"].append({"filename": file.filename, "id": str(doc.id)})
        except Exception as e:
            results["failed"].append({"filename": file.filename, "error": str(e)})

    await db.commit()
    # 批量同步 Meilisearch
    for item in results["succeeded"]:
        doc = await db.get(Document, item["id"])
        await index_document(doc)

    return {"total": len(files), "succeeded": len(results["succeeded"]),
            "failed": len(results["failed"]), "details": results}
```

**2. 前端**: 在 `DocumentManage.vue` 中新建批量导入 Dialog

```vue
<el-dialog v-model="batchVisible" title="批量导入文档" width="700px">
  <el-form>
    <el-form-item label="目标分类">
      <el-tree-select v-model="batchForm.category_id" :data="catTree" ... />
    </el-form-item>
    <!-- 标签、来源等公共字段 -->
  </el-form>

  <el-upload
    drag multiple :auto-upload="false"
    :on-change="handleBatchFileChange"
    :limit="100">
    <el-icon :size="48"><UploadFilled /></el-icon>
    <div>将文件拖到此处或<em>点击选择</em></div>
  </el-upload>

  <!-- 文件队列 -->
  <div class="batch-queue">
    <div v-for="(f, i) in batchFiles" :key="i" class="queue-item">
      <span>{{ f.name }}</span>
      <span>{{ formatSize(f.size) }}</span>
      <el-tag :type="f.status === 'done' ? 'success' : f.status === 'error' ? 'danger' : 'info'">
        {{ statusLabel(f.status) }}
      </el-tag>
    </div>
  </div>

  <el-button @click="startBatchUpload" :loading="batchUploading">
    开始上传 ({{ doneCount }}/{{ batchFiles.length }})
  </el-button>
</el-dialog>
```

**3. 逐个上传 + 进度反馈**:

```typescript
async function startBatchUpload() {
  batchUploading.value = true
  for (const file of batchFiles.value) {
    if (file.status === 'done') continue
    file.status = 'uploading'
    try {
      const fd = new FormData()
      fd.append('file', file.raw)
      fd.append('title', file.name.replace(/\.[^.]+$/, '').replace(/_/g, ' '))
      if (batchForm.category_id) fd.append('category_id', batchForm.category_id)
      fd.append('tags', JSON.stringify(batchForm.tags))
      fd.append('source', batchForm.source)
      await post('/api/documents', fd)
      file.status = 'done'
    } catch {
      file.status = 'error'
    }
  }
  batchUploading.value = false
  ElMessage.success(`上传完成: ${doneCount.value} 成功, ${errorCount.value} 失败`)
  loadData() // 刷新文档列表
}
```

**改动文件**:
- `backend/app/api/documents.py` — 新增 `POST /api/documents/batch`
- `frontend/src/views/admin/DocumentManage.vue` — 批量导入 Dialog

**验收标准**:
- [ ] 可一次性选择 10+ 文件
- [ ] 每个文件独立上传和状态显示
- [ ] 统一设置分类/标签/来源
- [ ] 失败的文件显示具体原因
- [ ] 上传完成后自动刷新文档列表

---

## <a id="需求8"></a>需求 8: 首页个性化 + 统计仪表盘

**优先级**: P3 (体验提升) | **工时**: 2天

### 🎨 UI 设计

**首页改造 - 登录后**:

```
┌──────────────────────────────────────────────────────────────┐
│  欢迎回来，张三！器械注册部 · 部门管理员                        │
│                                                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐        │
│  │ 📄 今日   │ │ 👁 本周   │ │ 📥 本月   │ │ 📊 本部门  │        │
│  │ 新增 3篇 │ │ 浏览 27  │ │ 上传 12  │ │ 文档 1,835│        │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘        │
│                                                              │
│  ┌─────────────────────┐ ┌──────────────────────────────┐   │
│  │ 🔥 热门文档(本周)    │ │ 📋 最近浏览                   │   │
│  │ 1. 医疗器械监督...   │ │ 注册管理办法(2025版) 10分钟前 │   │
│  │ 2. MDR 2017/745     │ │ 临床评价指导原则    30分钟前  │   │
│  │ 3. ISO 13485:2016   │ │ 分类目录(2024版)    1小时前   │   │
│  │ 4. 注册管理办法...   │ │ 角膜交联仪CER       2小时前   │   │
│  │ 5. GCP 规范指南     │ │                              │   │
│  └─────────────────────┘ └──────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 📌 快捷入口                                          │   │
│  │ [参考文件] [分类目录] [临床评价] [发补] [搜索文档...]   │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

### 🔧 实现方案

**1. 后端**: 新增首页聚合数据 API

```python
# backend/app/api/home.py (或加在 personal.py)
@router.get("/api/home/dashboard")
async def home_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    today = date.today()
    week_ago = today - timedelta(days=7)

    # 今日新增（本部门可见）
    # 本周浏览
    # 本部门文档总数
    # 热门文档（本周浏览量 TOP 10）
    # 最近浏览（当前用户）

    return {
        "today_new": ...,
        "week_views": ...,
        "dept_docs_total": ...,
        "hot_docs": [...],
        "recent_browse": [...],
    }
```

**2. 前端** `HomeView.vue` 改造:

- 登录后显示个性化问候语和统计卡片
- 统计卡片使用 `el-row` + `el-col` 4列布局
- 热门文档 + 最近浏览 双栏布局
- 快捷入口读取用户部门的快捷分类

**3. 快捷入口逻辑**:
```typescript
// 从侧边栏分类中取前4个作为快捷入口
const quickLinks = computed(() => {
  return modules.value.slice(0, 4).map(m => ({
    name: cleanName(m.name),
    id: m.id,
  }))
})
```

**改动文件**:
- 新建 `backend/app/api/home.py`（或扩展 personal.py）
- `frontend/src/views/HomeView.vue` — 全面改造

**验收标准**:
- [ ] 登录后首页显示个性化欢迎信息
- [ ] 统计卡片数据正确
- [ ] 热门文档按周浏览量排序
- [ ] 最近浏览显示当前用户的记录
- [ ] 快捷入口可点击跳转

---

## <a id="需求9"></a>需求 9: Meilisearch 健康监控

**优先级**: P3 (运维) | **工时**: 4h

### 🔧 实现方案

**1. 后端**: 扩展 health check 和新增统计接口

```python
# backend/app/main.py — 扩展 health
@app.get("/api/health")
async def health():
    meili_status = "unknown"
    try:
        client = _get_search_client_sync()
        health = client.health()
        meili_status = health.get("status", "unknown")
    except Exception:
        meili_status = "unreachable"

    return {
        "status": "ok" if meili_status != "unreachable" else "degraded",
        "meilisearch": meili_status,
    }

# backend/app/services/search_service.py — 新增统计
async def get_search_stats(db: AsyncSession) -> dict:
    """返回 Meilisearch vs PostgreSQL 的同步状态"""
    try:
        client = _get_search_client_sync()
        index_stats = client.index("documents").stats()
        meili_count = index_stats.get("numberOfDocuments", 0)
    except Exception:
        meili_count = 0

    # PostgreSQL 未删除文档数
    from sqlalchemy import select, func
    from app.models.document import Document
    result = await db.execute(
        select(func.count(Document.id)).where(Document.is_deleted == False)
    )
    pg_count = result.scalar()

    return {
        "meilisearch_docs": meili_count,
        "postgresql_docs": pg_count,
        "unsynced": pg_count - meili_count,
        "health": "healthy" if abs(pg_count - meili_count) < 10 else "drifted",
    }
```

**2. 前端**: SystemSettings 的"数据库与索引" Tab 对接真实数据

```typescript
onMounted(async () => {
  try {
    const health = await get('/api/health')
    stats.meili_status = health.meilisearch
    const searchStats = await get('/api/admin/search-stats')
    stats.meili_docs = searchStats.meilisearch_docs
    stats.pg_docs = searchStats.postgresql_docs
    stats.unsynced = searchStats.unsynced
  } catch {}
})
```

**验收标准**:
- [ ] `/api/health` 包含 Meilisearch 状态
- [ ] 管理后台索引 Tab 显示同步状态
- [ ] 未同步数量超过阈值时显示警告标签

---

## <a id="需求10"></a>需求 10: UI/UX 全面优化

**优先级**: P2 (体验) | **工时**: 1.5天

### 🎨 优化清单

**1. 全局 Loading 骨架屏**:

```
文档列表加载时:
┌─────────────────────────────────────┐
│ ████████████████░░░░░░░░  (骨架动画) │
│ ██████░░░░░░░░░░░░░░░░░░            │
│ ─────────────────────────────────── │
│ ████████████████████████░░░░░       │
│ ██████░░░░░░░░░░░░░░░░░░            │
└─────────────────────────────────────┘
```

在 `CategoryView`, `SearchView`, `PersonalView` 的 `v-loading` 上增加 `element-loading-skeleton` 效果。

**2. 空状态优化**:

```
当前状态                          优化后
┌──────────────┐          ┌──────────────────────┐
│              │          │        📭            │
│  暂无文档     │    →     │    暂无文档           │
│              │          │  该分类下还没有文档    │
│              │          │  [上传第一篇文档]     │
└──────────────┘          └──────────────────────┘
```

**3. 错误状态优化**: 网络断开时在页面顶部显示 `el-alert` 提示条而非静默失败。

**4. 响应式优化**:

```css
/* 移动端: 隐藏侧边栏，内容全宽 */
@media (max-width: 768px) {
  .workflow-sidebar { display: none; }
  .main-content.with-sidebar { margin-left: 0; }
  .content-wrapper { padding: 12px; }
  .hero-banner { padding: 24px 16px; }
  .hero-banner h1 { font-size: 18px; }
  .header-search { width: 140px; }
}

/* 平板: 收起侧边栏到图标模式 */
@media (max-width: 1024px) {
  .workflow-sidebar { width: 60px; }
  .main-content.with-sidebar { margin-left: 60px; }
  /* 只显示图标，隐藏文字 */
}
```

**5. 键盘快捷键**:

| 快捷键 | 功能 |
|--------|------|
| `Ctrl + K` | 聚焦搜索框 |
| `Ctrl + Enter` | 执行搜索 |
| `Escape` | 关闭弹窗/清空搜索 |
| `Ctrl + D` | 跳转首页 |

```typescript
// App.vue 中添加全局键盘监听
onMounted(() => {
  document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
      e.preventDefault()
      // 聚焦搜索框
    }
  })
})
```

**6. 面包屑导航增强**: 分类页显示完整路径

```
现在是:  首页 > 参考文件
优化为:  首页 > 器械注册部 > 参考文件 > 通用法规（国内）
```

在 `CategoryView.vue` 的 `loadCategory` 中递归构建面包屑路径。

**改动文件**:
- `frontend/src/styles/global.css` — 响应式 + 骨架屏样式
- `frontend/src/App.vue` — 全局键盘快捷键
- `frontend/src/views/CategoryView.vue` — 面包屑增强
- `frontend/src/components/layout/AppHeader.vue` — 搜索快捷键

**验收标准**:
- [ ] 移动端（375px 宽）布局正常
- [ ] 平板（768px 宽）侧边栏为图标模式
- [ ] 搜索框 `Ctrl+K` 聚焦
- [ ] 面包屑显示完整分类路径

---

## 附录: 提示词使用指南

### 怎么用这些提示词？

**方式 1: 直接复制给 Claude Code**
```
（复制上面任意一个需求的完整内容，粘贴到对话框）
```

**方式 2: 拆分为更小的任务**
```
请实现需求4的第2步：扩展 MainLayout.vue 的 WORKFLOW_DEPTS 数组。
当前文件在 frontend/src/components/layout/MainLayout.vue。
```

**方式 3: 给人类开发者**
```
这些就是需求规格，每个都包含了：
- 问题描述（为什么要做）
- UI 设计（做成什么样）
- 实现方案（具体怎么做）
- 改动文件（改哪里）
- 验收标准（怎么算做完）
```

### 实现优先级建议

```
第一周:  需求0 (品牌色统一) + 需求1 (搜索修复) + 需求2 (预览方案) + 需求3 (索引)
第二周:  需求4 (工作流侧边栏) + 需求5 (系统设置)
第三周:  需求10 (UI优化) + 需求6 (通讯录)
第四周:  需求8 (首页) + 需求9 (监控)
第五周:  需求7 (批量导入)
```
