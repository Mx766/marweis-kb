# 迈瑞生知识库 (Marweis KB) — 需求分析设计文档

> **版本**: v1.0  
> **日期**: 2026-07-14  
> **分析范围**: 全栈代码审查（后端 FastAPI + 前端 Vue3 + 基础设施）  
> **当前版本**: v0.1.1-dev  

---

## 目录

1. [项目概述](#1-项目概述)
2. [业务背景与目标](#2-业务背景与目标)
3. [用户角色分析](#3-用户角色分析)
4. [功能需求详述](#4-功能需求详述)
5. [非功能性需求](#5-非功能性需求)
6. [系统架构设计](#6-系统架构设计)
7. [数据库设计](#7-数据库设计)
8. [API 接口设计](#8-api-接口设计)
9. [前端设计](#9-前端设计)
10. [安全设计](#10-安全设计)
11. [部署架构](#11-部署架构)
12. [已知问题与改进建议](#12-已知问题与改进建议)
13. [待开发功能](#13-待开发功能)

---

## 1. 项目概述

### 1.1 项目信息

| 项目 | 内容 |
|------|------|
| **项目名称** | 迈瑞生知识库 (Marweis Knowledge Base) |
| **项目类型** | 企业内部知识管理系统 |
| **当前版本** | v0.1.1-dev |
| **技术栈** | FastAPI + Vue 3 + PostgreSQL + MinIO + Meilisearch + Gotenberg |
| **部署环境** | Ubuntu 22.04 (Lenovo ThinkCentre M730q, 8GB RAM) |
| **访问地址** | https://192.168.60.175 (内网 HTTPS) |
| **代码仓库** | https://github.com/Mx766/marweis-kb (私有) |

### 1.2 核心定位

迈瑞生知识库是一个面向**医疗器械注册咨询行业**的企业内部知识管理平台。系统为北京迈瑞生医药科技有限公司及其子品牌（善芃 SMO、迈美丝化妆品、大道力维特医食品）的各业务部门提供：

- 医疗器械注册法规/指导原则/审评报告的统一存储与检索
- 按部门隔离的知识分类体系
- 基于 RBAC 的权限管控
- 文档在线预览（PDF 转换）
- 全文搜索引擎

---

## 2. 业务背景与目标

### 2.1 企业业务背景

北京迈瑞生医药科技有限公司是一家专注于**医疗器械注册咨询**的服务机构，业务覆盖：

| 部门 | 业务范围 | 子品牌 |
|------|---------|--------|
| 器械注册部 | 医疗器械 NMPA 注册申报 | — |
| 临床评价部 | 临床评价报告 (CER) 撰写 | — |
| 临床试验部 | 临床试验 CRO + SMO 服务 | 善芃 SMO |
| 生产体系部 | ISO 13485 体系搭建、模拟体考 | — |
| 化妆品·医美部 | 进口/国产化妆品注册备案 | 迈美丝 |
| 特医食品部 | 特殊医学用途配方食品注册 | 大道力维 |
| 管理层 | 战略规划、经营管理 | — |

### 2.2 业务痛点

1. **知识分散**: 历年积累的审评报告、指导原则、法规文件分散在 Windows 共享文件夹和各部门员工本地电脑上
2. **检索困难**: 741 篇审评报告 + 647 篇指导原则 + 法规文件，Windows 文件搜索效率低下
3. **权限缺失**: 共享文件夹无细粒度权限控制，部门间的敏感资料（如管理层专区、发补意见）缺乏隔离
4. **协作低效**: 缺乏统一的文档元数据管理（来源、生效日期、版本号、标签）
5. **预览不便**: Office 文档 (.docx/.xlsx/.pptx) 需要本地安装 Office 才能查看

### 2.3 项目目标

| 目标 | 当前状态 |
|------|---------|
| ✅ 统一知识存储 | 已导入 ~2000 篇文档（审评报告 + 指导原则 + 法规） |
| ✅ 全文搜索 | Meilisearch 搜索引擎，毫秒级响应 |
| ✅ 部门级权限隔离 | RBAC 五级角色 + 分类可见部门配置 |
| ✅ 在线预览 | Gotenberg 自动转 PDF，浏览器内嵌预览 |
| ✅ 工作流导航 | 器械注册部 7 模块工作流侧边栏 |
| ⬜ 全部门覆盖 | 仅器械注册部有工作流侧边栏，其他部门待扩展 |
| ⬜ 批量导入界面 | 当前仅支持脚本导入，无 UI 批量上传 |

---

## 3. 用户角色分析

### 3.1 角色定义

| 角色 | 标识 | 权限层级 | 说明 |
|------|------|---------|------|
| **super_admin** | 超级管理员 | 100 | 全部权限，管理所有用户/分类/文档 |
| **dept_admin** | 部门管理员 | 50 | 管理本部门用户和文档，可编辑部门分类下的文档 |
| **editor** | 编辑者 | 30 | 上传文档，编辑/删除自己上传的文档 |
| **employee** | 普通员工 | 10 | 查看本部门可见文档，收藏，浏览 |
| **guest** | 访客 | 0 | 仅查看公共分类（visible_departments 为 NULL）的文档 |

### 3.2 权限矩阵

| 操作 | super_admin | dept_admin | editor | employee | guest |
|------|:---:|:---:|:---:|:---:|:---:|
| 查看公共文档 | ✅ | ✅ | ✅ | ✅ | ✅ |
| 查看本部门文档 | ✅ | ✅ | ✅ | ✅ | ❌ |
| 查看所有部门文档 | ✅ | ❌ | ❌ | ❌ | ❌ |
| 上传文档 | ✅ | ✅ | ✅ | ❌ | ❌ |
| 编辑自己的文档 | ✅ | ✅ | ✅ | ❌ | ❌ |
| 编辑他人文档(本部门) | ✅ | ✅ | ❌ | ❌ | ❌ |
| 编辑他人文档(跨部门) | ✅ | ❌ | ❌ | ❌ | ❌ |
| 删除文档 | ✅ | ✅(本部门) | ✅(自己的) | ❌ | ❌ |
| 创建分类 | ✅ | ❌ | ❌ | ❌ | ❌ |
| 编辑分类 | ✅ | ❌ | ❌ | ❌ | ❌ |
| 管理本部门用户 | ✅ | ✅ | ❌ | ❌ | ❌ |
| 管理全部用户 | ✅ | ❌ | ❌ | ❌ | ❌ |
| 删除用户 | ✅ | ❌ | ❌ | ❌ | ❌ |
| 个人收藏/历史 | ✅ | ✅ | ✅ | ✅ | ❌(需登录) |

### 3.3 部门列表

```
器械注册部, 临床评价部, 临床试验部, 生产体系部,
化妆品·医美部, 特医食品部, 管理层
```

### 3.4 当前已修复的权限问题

> 以下问题已于 2026-07-14 修复（commit 55e95d6）：

- ✅ dept_admin 不再能创建 super_admin/dept_admin 角色的用户
- ✅ dept_admin 不再能提升现有用户角色为 super_admin/dept_admin
- ✅ dept_admin 只能在本部门内创建用户
- ✅ dept_admin 不能将用户转移到其他部门

---

## 4. 功能需求详述

### 4.1 用户认证模块

#### 4.1.1 登录

| 需求项 | 详情 |
|--------|------|
| **入口** | `/login` |
| **认证方式** | 用户名 + 密码 → JWT Token (HS256, 8小时过期) |
| **密码加密** | bcrypt 加盐哈希 |
| **安全防护** | 滑动窗口限流: 同IP 10次/5分钟 |
| **登录后行为** | 跳转到登录前访问的页面（redirect 参数校验防止 open redirect） |
| **错误提示** | "用户名或密码错误"（不区分是用户名不存在还是密码错误） |

#### 4.1.2 注册

| 需求项 | 详情 |
|--------|------|
| **入口** | `/register` |
| **注册角色** | 固定为 `employee` |
| **必填字段** | 用户名、姓名、部门、密码 |
| **密码强度** | 最少8位 + 至少1个字母 + 至少1个数字 |
| **部门选择** | 7 个预设部门下拉选择 |
| **后台校验** | 用户名唯一性、部门有效性、密码强度 |

#### 4.1.3 当前用户信息

| 需求项 | 详情 |
|--------|------|
| **接口** | `GET /api/auth/me` |
| **返回** | 用户ID、用户名、姓名、工号、部门、角色、邮箱、头像 |

### 4.2 文档管理模块

#### 4.2.1 文档类型

| 类型 | 说明 | 存储方式 |
|------|------|---------|
| **file (文件)** | 物理上传的文件 | MinIO (S3 兼容存储) → Gotenberg 转 PDF 预览 |
| **link (链接)** | 外部 URL 引用 | 仅存 URL 元数据，预览时重定向到外部 |

#### 4.2.2 文档数据结构

| 字段 | 类型 | 必填 | 说明 |
|------|------|:---:|------|
| `title` | String(500) | ✅ | 文档标题 |
| `category_id` | UUID | ❌ | 所属分类 |
| `file_type` | String(20) | ✅ | `file` 或 `link` |
| `original_filename` | String(500) | ✅ | 原始文件名 |
| `original_path` | String(1000) | ✅ | MinIO S3 路径 或 外部URL |
| `preview_path` | String(1000) | ❌ | 转换后的 PDF 预览路径 |
| `file_size` | BigInteger | — | 文件大小(字节) |
| `file_ext` | String(20) | — | 文件扩展名 |
| `mime_type` | String(100) | — | MIME 类型 |
| `tags` | JSON | ❌ | 标签数组 |
| `summary` | Text | ❌ | 摘要/简介 |
| `source` | String(500) | ❌ | 来源机构 (NMPA/CMDE/FDA...) |
| `source_url` | String(1000) | ❌ | 来源链接 |
| `effective_date` | Date | ❌ | 生效日期 |
| `version` | String(50) | ❌ | 版本号 |
| `uploader_id` | UUID | ✅ | 上传者ID |
| `view_count` | Integer | — | 浏览次数 |
| `download_count` | Integer | — | 下载次数 |
| `is_deleted` | Boolean | — | 软删除标记 |

#### 4.2.3 文档列表

| 需求项 | 详情 |
|--------|------|
| **接口** | `GET /api/documents` |
| **分页** | 默认 20 条/页，最大 100 条/页 |
| **排序** | 支持 `updated_at`/`created_at`/`title`/`file_size`，升降序 |
| **分类筛选** | 按 `category_id` 过滤 |
| **权限过滤** | 基于角色+部门过滤可见分类 → 只返回有权限的文档 |
| **N+1 优化** | 批量加载上传者信息（`_batch_load_uploaders`） |

#### 4.2.4 文档上传

| 需求项 | 详情 |
|--------|------|
| **接口** | `POST /api/documents` (multipart/form-data) |
| **支持格式** | PDF/Word/Excel/PPT/TXT/MD/CSV/JSON/图片/音视频/ZIP/RAR/DWG/STP/DCM/EPUB 等 |
| **大小限制** | 默认 500MB（可配置） |
| **处理流程** | 接收文件 → 上传 MinIO (`originals/`) → Gotenberg 转 PDF → 预览存入 MinIO (`previews/`) → 写入 DB → 同步 Meilisearch |
| **权限** | super_admin / dept_admin / editor |

#### 4.2.5 文档预览

| 需求项 | 详情 |
|--------|------|
| **接口** | `GET /api/documents/{id}/preview?token=...` |
| **认证方式** | 支持两种 token — 完整 JWT 或 scope=preview 的限时 token (5分钟) |
| **文件型** | 流式返回 PDF (优先使用缓存预览，否则 Gotenberg 按需转换) |
| **链接型** | 307 重定向到外部 URL (白名单域名校验 — nmpa.gov.cn, fda.gov 等) |
| **图片/音视频** | 直接流式返回原始文件 |
| **预览令牌** | `GET /api/documents/{id}/preview-token` 生成限时 token 用于 iframe src |

#### 4.2.6 文档编辑

| 需求项 | 详情 |
|--------|------|
| **接口** | `PUT /api/documents/{id}` |
| **可编辑字段** | title, category_id, tags, summary, source, source_url, effective_date, version |
| **权限** | super_admin 编辑任意 / dept_admin 编辑本部门可见的 / editor 编辑自己的 |

#### 4.2.7 文档删除

| 需求项 | 详情 |
|--------|------|
| **删除方式** | 软删除 (`is_deleted = True`)，不从 MinIO 物理删除文件 |
| **接口** | `DELETE /api/documents/{id}` |
| **权限** | super_admin / dept_admin(本部门) / editor(自己的) |
| **副作用** | 同步从 Meilisearch 索引中移除 |

#### 4.2.8 文档下载

| 需求项 | 详情 |
|--------|------|
| **接口** | `GET /api/documents/{id}/download` |
| **方式** | 生成 MinIO presigned URL (1小时有效期)，307 重定向 |
| **下载计数** | 每次下载 `download_count++` |
| **权限** | 与查看权限一致 |

### 4.3 分类管理模块

#### 4.3.1 分类数据结构

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | String(100) | 分类名称 |
| `parent_id` | UUID | 父分类ID (NULL=顶级) |
| `sort_order` | Integer | 排序号 |
| `icon` | String(50) | 图标名 |
| `visible_departments` | JSON | 可见部门列表 (NULL=全员可见, `["*"]`=全员, `["器械注册部"]`=仅该部门) |
| `description` | String(500) | 分类描述 |

#### 4.3.2 分类树

| 需求项 | 详情 |
|--------|------|
| **接口** | `GET /api/categories` |
| **返回格式** | 递归树形结构 (children 嵌套) |
| **权限过滤** | super_admin 看全部 → 非管理员按 `visible_departments` 过滤 → Guest 只看 public |
| **递归查找** | CategoryView 实现了树形递归查找 (`findByCat`)，支持深层子分类 |

#### 4.3.3 分类 CRUD

| 操作 | 权限 | 说明 |
|------|------|------|
| 创建分类 | super_admin | 可指定父级、可见部门、排序 |
| 编辑分类 | super_admin | 支持移动分类(带循环检测) |
| 删除分类 | super_admin | 子分类 re-parent 到被删分类的父级 |

#### 4.3.4 当前分类体系

**器械注册部工作流模块** (sort_order 1-7, visible_departments=["器械注册部"]):

```
1. 参考文件
   ├── 通用法规（国内）
   ├── 通用法规（国外）
   ├── 指导原则
   └── 审评论坛
2. 分类目录
3. 校验技术要求
4. 临床评价资料
   ├── 临床文献
   ├── 国家局网站
   └── 说明书
5. 发补
   ├── 例卷
   └── 发补意见
6. 注册证书
   ├── 注册证书
   └── 注册资料
7. 通讯录
   ├── 中央药监局
   └── 地方药监局
```

**其他部门专属分类**:
- 临床评价部（CER）: 临床评价报告模板、等同性论证文献库、CER案例库、评价方法学指南
- 临床试验部（CRO+SMO）: 临床试验方案库、GCP规范、SMO操作手册 等
- 生产体系部: ISO13485体系文件、质量手册、模拟体考检查清单 等
- 化妆品·医美部: 进口化妆品备案、国产特殊化妆品注册 等
- 特医食品部: 特医食品注册指南、临床试验方案 等
- 管理层专区: 战略规划、客户合同、月度报告 等

**公共区域** (visible_departments=NULL, 全员+访客可见):
- 行业新闻 & 法规动态
- NMPA 法规库
- FDA 法规库
- CE MDR 法规库
- 公司制度 & 通用 SOP
- 培训资料（通用）

### 4.4 搜索模块

#### 4.4.1 搜索引擎

| 需求项 | 详情 |
|--------|------|
| **主引擎** | Meilisearch (全文本搜索，支持中文分词) |
| **回退方案** | SQL ILIKE (PostgreSQL 模糊搜索) |
| **索引字段** | title, content(summary), tags, summary |
| **可过滤字段** | category_id, file_type, uploader_id |
| **可排序字段** | created_at, updated_at, title |
| **权限过滤** | 搜索结果按可见分类ID过滤 → 再经过 `can_view_document` 二次校验 |
| **高亮** | Meilisearch 返回高亮片段；前端 `highlight()` 先 HTML 转义再插入 `<em>` 标签 |

#### 4.4.2 搜索接口

| 需求项 | 详情 |
|--------|------|
| **接口** | `GET /api/search?q=&category_id=&file_type=&tag=&page=&size=` |
| **搜索范围** | 标题 + 摘要 |
| **过滤器注入防护** | 单引号转义 (`_escape_meili_filter_value`) |

### 4.5 个人工作台模块

| 功能 | 接口 | 说明 |
|------|------|------|
| **我的上传** | `GET /api/me/uploads` | 当前用户上传的文档列表(分页) |
| **我的收藏** | `GET /api/me/favorites` | 收藏的文档列表(分页) |
| **添加收藏** | `POST /api/me/favorites/{id}` | 收藏文档 (权限校验: 需能查看该文档) |
| **取消收藏** | `DELETE /api/me/favorites/{id}` | 取消收藏 |
| **浏览历史** | `GET /api/me/history` | 浏览过的文档(去重，按时间倒序) |
| **个人统计** | `GET /api/me/stats` | total_uploads / total_favorites / total_history |

### 4.6 管理后台模块

#### 4.6.1 文档管理 (`/admin/documents`)

| 功能 | 说明 |
|------|------|
| 文档列表 | 分页表格，支持搜索（走 Search API） |
| 上传文档 | 弹窗表单：标题、分类(树选择)、标签、摘要、来源、文件/链接 |
| 编辑元数据 | 弹窗：标题、分类、标签、摘要、版本 |
| 删除 | 确认弹窗 → 软删除 |

#### 4.6.2 分类管理 (`/admin/categories`)

| 功能 | 说明 |
|------|------|
| 分类列表 | 扁平化树形表格（按层级缩进） |
| 部门标签页 | 按 7 个部门分组 Tab，显示各部门下的分类数量 |
| 添加分类 | 弹窗：名称、父分类(树选择)、排序、图标、可见部门(多选)、描述 |
| 编辑分类 | 弹窗：同添加，支持移动分类 |
| 删除分类 | 确认弹窗 → 子分类自动 re-parent |

#### 4.6.3 用户管理 (`/admin/users`)

| 功能 | 说明 |
|------|------|
| 用户列表 | 分页表格，支持按部门筛选 |
| 添加用户 | 弹窗：用户名、密码、姓名、工号、部门、角色、邮箱 |
| 编辑用户 | 弹窗：姓名、工号、部门、角色、邮箱 |
| 启停用户 | 一键切换 `is_active` 状态 |
| **权限限制** | dept_admin 只能管理本部门用户，不能授予 super_admin/dept_admin |

#### 4.6.4 系统设置 (`/admin/settings`)

| 标签页 | 功能 | 说明 |
|--------|------|------|
| **基本设置** | 站点名称、描述、主色调、Logo、Slogan、页脚 | ⚠️ 仅前端展示，未与后端持久化关联 |
| **文件与存储** | 上传大小限制、MinIO配置、允许文件类型 | ⚠️ 同上，当前是硬编码配置 |
| **数据库与索引** | 文档/用户/分类统计、重建索引按钮 | ⚠️ 统计数据和索引重建未对接实际后端接口 |

### 4.7 工作流侧边栏模块

| 需求项 | 详情 |
|--------|------|
| **显示条件** | 管理员(super_admin/dept_admin) 或 器械注册部成员 |
| **数据来源** | `GET /api/categories` 接口 → 过滤编号模块(正则 `/^\d+\./`) 和公共知识区 |
| **交互** | 模块名点击 → 导航到分类详情页；箭头点击 → 展开/折叠子分类 |
| **高亮** | 当前激活的分类/子分类高亮显示 |
| **样式** | 深色侧边栏 (#1e293b), 220px 宽, 固定定位 |

### 4.8 批量导入模块（脚本级）

目前通过 Python 脚本直写 MinIO + PostgreSQL 实现，不走 HTTP API：

| 脚本 | 功能 |
|------|------|
| `import_kb.py` | 基础导入 |
| `import_fast.py` | 快速导入 |
| `import_ultra.py` | 终极优化导入 |
| `import_from_windows.py` | 从 Windows 路径导入 |
| `server_import.py` | 服务器端直写导入 |
| `migrate_categories.py` | 批量迁移文档分类 |
| `cleanup_duplicates.py` | 清理重复分类 |

---

## 5. 非功能性需求

### 5.1 性能需求

| 指标 | 目标 | 当前状态 |
|------|------|---------|
| 文档列表响应时间 | < 500ms | ✅ 通过 (N+1 优化 + 分页) |
| 搜索响应时间 | < 200ms (Meilisearch) | ✅ 毫秒级 |
| 文件上传速度 | > 1MB/s | ⚠️ 受 Gotenberg 转换阻塞 |
| PDF 预览加载 | < 3s (缓存) / < 15s (按需转换) | ⚠️ 首次按需转换较慢 |
| 并发用户数 | 50+ | ✅ (仅内网使用) |

### 5.2 安全需求

| 需求 | 状态 |
|------|:---:|
| JWT 密钥通过环境变量注入 (非硬编码) | ✅ |
| 密码 bcrypt 加盐哈希 | ✅ |
| 密码强度验证 (8位+字母+数字) | ✅ |
| 登录限流 (滑动窗口 10次/5分钟) | ✅ |
| SQL 注入防护 (SQLAlchemy ORM) | ✅ |
| Meilisearch 过滤器注入防护 (单引号转义) | ✅ |
| XSS 防护 (v-html 先转义) | ✅ |
| Open Redirect 防护 (路径+协议校验) | ✅ |
| 生产环境不暴露异常类型 | ✅ |
| CORS 限制 | ⚠️ `allow_origins=["*"]` 较宽松 |
| HTTPS 加密传输 | ✅ (Nginx 反向代理) |
| RBAC 权限控制 | ⚠️ 存在已知权限缺陷(见第12节) |

### 5.3 可用性需求

| 需求 | 状态 |
|------|:---:|
| SPA 前端路由 (刷新不 404) | ✅ |
| 错误页面 (403/404/500) 友好提示 | ✅ |
| 响应式布局 (移动端适配) | ⚠️ 仅 DocumentView 有 @media 适配 |
| 加载状态 (v-loading / skeleton) | ✅ |
| 空状态提示 (el-empty) | ✅ |

### 5.4 可维护性需求

| 需求 | 状态 |
|------|:---:|
| 请求日志中间件 (方法/路径/状态/耗时) | ✅ |
| Docker Compose 一键启动基础设施 | ✅ |
| 一键部署脚本 (deploy.sh) | ✅ |
| 数据库迁移工具 (Alembic) | ✅ (但未大量使用迁移) |
| 代码分层清晰 (api/models/services/middleware) | ✅ |
| 类型安全 (Pydantic 后端 + TypeScript 前端) | ✅ |

### 5.5 数据规模

| 指标 | 当前值 |
|------|--------|
| 总文档数 | ~2,000 篇 (含 demo 数据) |
| .docx (指导原则) | 1,180 (59%) |
| .pdf (审评报告+法规) | 788 (40%) |
| 总分类数 | 37 个 |
| 总用户数 | < 50 (企业内部) |

---

## 6. 系统架构设计

### 6.1 总体架构

```
┌─────────────────────────────────────────────────────────┐
│                      客户端层                            │
│  Browser ── HTTPS ──▶ Nginx (:443)                     │
│  Firefox (Chrome 150+ 拦截 HTTPS IP)                    │
└──────────────────────┬──────────────────────────────────┘
                       │ reverse proxy
                       ▼
┌─────────────────────────────────────────────────────────┐
│                   应用服务层                              │
│  uvicorn :8000 (127.0.0.1)                             │
│  ┌──────────────────────────────────────────────────┐   │
│  │ FastAPI Application                              │   │
│  │  ├── middleware/ (logging, error_handler, CORS)   │   │
│  │  ├── api/ (auth, documents, categories, search,  │   │
│  │  │        personal, admin)                        │   │
│  │  ├── services/ (FileService, SearchService)      │   │
│  │  ├── models/ (User, Document, Category,          │   │
│  │  │           Favorite, BrowseHistory)             │   │
│  │  ├── schemas/ (Pydantic request/response)        │   │
│  │  ├── auth.py (JWT, bcrypt)                       │   │
│  │  ├── permissions.py (RBAC)                       │   │
│  │  └── config.py (pydantic_settings)               │   │
│  └──────────────────────────────────────────────────┘   │
│  + Vue 3 SPA (StaticFiles mount /assets/)               │
└──────┬──────────┬──────────┬──────────┬─────────────────┘
       │          │          │          │
       ▼          ▼          ▼          ▼
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐
│PostgreSQL│ │  MinIO   │ │Meilisearch│ │  Gotenberg   │
│  :5432   │ │  :9000   │ │  :7700   │ │    :3000     │
│ Docker   │ │ Docker   │ │ Docker   │ │   Docker     │
│ pgvector │ │ S3 compat│ │ v1.10    │ │   v8         │
└──────────┘ └──────────┘ └──────────┘ └──────────────┘
```

### 6.2 技术选型理由

| 组件 | 选型 | 理由 |
|------|------|------|
| **后端框架** | FastAPI | 高性能异步、自动 OpenAPI 文档、Pydantic 类型校验 |
| **前端框架** | Vue 3 + TypeScript | 渐进式、Element Plus 丰富组件、Pinia 轻量状态管理 |
| **数据库** | PostgreSQL 16 + pgvector | JSON 支持好、UUID 原生支持、未来可扩展向量检索 |
| **ORM** | SQLAlchemy 2.0 async | 成熟稳定、原生异步支持 |
| **对象存储** | MinIO | S3 兼容、Docker 部署简单、适合内网环境 |
| **搜索引擎** | Meilisearch | 中文分词好、部署简单、API 友好 |
| **文档转换** | Gotenberg | 无状态容器、LibreOffice 内核、支持主流 Office 格式 |
| **反向代理** | Nginx | HTTPS 终结、静态文件服务、高性能 |
| **容器化** | Docker Compose | 基础设施一键部署 |

### 6.3 关键业务流程

#### 文件上传流程

```
Client (FormData) → FastAPI upload endpoint
  → 1. 校验权限 (editor+)
  → 2. 校验文件大小 (MAX_UPLOAD_SIZE_MB)
  → 3. 上传原始文件到 MinIO (originals/{uuid}/{filename})
  → 4. 发送原始文件到 Gotenberg → 转换 PDF
  → 5. 上传 PDF 到 MinIO (previews/{uuid}/{filename}.pdf)
  → 6. 写入 PostgreSQL (Document 记录)
  → 7. 同步 Meilisearch 索引
  → 返回 document_id
```

#### 预览流程

```
Client → GET /api/documents/{id}/preview-token → 获取限时 token
Client → GET /api/documents/{id}/preview?token=xxx
  → 1. 验证 token (scope=preview, doc 匹配)
  → 2. 权限检查 (can_view_document)
  → 3. 判断文件类型:
      - link: 307 重定向到外部 URL (白名单校验)
      - 图片/音视频: 直接流式返回
      - 其他:
        - 有 preview_path: 从 MinIO 读取缓存 PDF
        - 无可转换: Gotenberg 按需转换 → 缓存到 MinIO
        → StreamingResponse (application/pdf, inline)
```

#### 搜索流程

```
Client → GET /api/search?q=keyword
  → 1. 获取用户可见分类ID列表
  → 2. 如可见列表为空 → 直接返回空
  → 3. Meilisearch 搜索 (带分类ID权限过滤)
  → 4. 如有结果:
      → 从 PostgreSQL 批量加载文档 + 上传者信息
      → 经过 can_view_document 二次权限过滤
      → 返回 SearchResult
  → 5. 如无结果 (Meilisearch 异常):
      → SQL ILIKE fallback: title/summary 模糊匹配
      → 分类ID过滤 + 权限二次过滤
      → 返回结果
```

---

## 7. 数据库设计

### 7.1 ER 图 (逻辑)

```
┌──────────┐       ┌──────────────┐       ┌──────────┐
│   User   │       │   Document   │       │ Category │
├──────────┤       ├──────────────┤       ├──────────┤
│ id (PK)  │──┐    │ id (PK)      │    ┌──│ id (PK)  │
│ username │  │    │ title        │    │  │ name     │
│ password │  │    │ category_id  │────┘  │ parent_id│──┐
│ name     │  │    │ file_type    │       │ sort     │  │
│ dept     │  │    │ orig_filename│       │ icon     │  │
│ role     │  │    │ orig_path    │       │ visible  │  │
│ email    │  │    │ preview_path │       │ desc     │  │
│ active   │  │    │ file_size    │       └──────────┘  │
└──────────┘  │    │ file_ext     │            │        │
       │      │    │ mime_type    │            └────────┘
       │      │    │ tags (JSON)  │        (self-referencing)
       │      │    │ summary      │
       │      │    │ source       │
       │      ├───▶│ uploader_id  │
       │      │    │ view_count   │
       │      │    │ download_cnt │
       │      │    │ is_deleted   │
       │      │    └──────────────┘
       │      │           │
       │      │    ┌──────┴──────┐
       │      │    │             │
       ▼      ▼    ▼             ▼
┌──────────┐  ┌──────────────────┐
│ Favorite │  │  BrowseHistory   │
├──────────┤  ├──────────────────┤
│ user_id  │  │ user_id          │
│ doc_id   │  │ doc_id           │
└──────────┘  │ created_at       │
              └──────────────────┘
```

### 7.2 表结构

#### users

| 列 | 类型 | 约束 | 说明 |
|----|------|------|------|
| id | UUID | PK, default uuid4 | 用户ID |
| username | VARCHAR(50) | UNIQUE, NOT NULL | 登录用户名 |
| password_hash | VARCHAR(255) | NOT NULL | bcrypt 哈希 |
| display_name | VARCHAR(50) | NOT NULL | 显示姓名 |
| employee_id | VARCHAR(50) | NULLABLE | 工号 |
| department | VARCHAR(50) | NOT NULL | 部门名称 |
| role | VARCHAR(20) | NOT NULL, default 'employee' | 角色标识 |
| email | VARCHAR(100) | NULLABLE | 邮箱 |
| avatar_url | VARCHAR(500) | NULLABLE | 头像URL |
| is_active | BOOLEAN | default true | 账号启用状态 |
| created_at | TIMESTAMP | NOT NULL, server_default now() | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL, onupdate now() | 更新时间 |

#### documents

| 列 | 类型 | 约束 | 说明 |
|----|------|------|------|
| id | UUID | PK | 文档ID |
| title | VARCHAR(500) | NOT NULL | 标题 |
| category_id | UUID | NULLABLE (无 FK) | ⚠️ 未设置外键约束 |
| file_type | VARCHAR(20) | NOT NULL | 'file' / 'link' |
| original_filename | VARCHAR(500) | NOT NULL | 原始文件名 |
| original_path | VARCHAR(1000) | NOT NULL | MinIO路径 |
| preview_path | VARCHAR(1000) | NULLABLE | PDF预览路径 |
| file_size | BIGINT | default 0 | 字节数 |
| file_ext | VARCHAR(20) | default '' | 扩展名 |
| mime_type | VARCHAR(100) | default '' | MIME类型 |
| tags | JSON | NULLABLE | 标签列表 |
| summary | TEXT | NULLABLE | 摘要 |
| source | VARCHAR(500) | NULLABLE | 来源 |
| source_url | VARCHAR(1000) | NULLABLE | 来源链接 |
| effective_date | DATE | NULLABLE | 生效日期 |
| version | VARCHAR(50) | NULLABLE | 版本号 |
| uploader_id | UUID | NOT NULL | 上传者 |
| view_count | INTEGER | default 0 | 浏览次数 |
| download_count | INTEGER | default 0 | 下载次数 |
| is_deleted | BOOLEAN | default false | 软删除 |
| created_at | TIMESTAMP | NOT NULL | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL | 更新时间 |

#### categories

| 列 | 类型 | 约束 | 说明 |
|----|------|------|------|
| id | UUID | PK | 分类ID |
| name | VARCHAR(100) | NOT NULL | 分类名 |
| parent_id | UUID | NULLABLE | 父分类 |
| sort_order | INTEGER | default 0 | 排序 |
| icon | VARCHAR(50) | NULLABLE | 图标 |
| visible_departments | JSON | NULLABLE | 可见部门(NULL=全员) |
| description | VARCHAR(500) | NULLABLE | 描述 |
| created_at | TIMESTAMP | NOT NULL | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL | 更新时间 |

#### favorites

| 列 | 类型 | 约束 | 说明 |
|----|------|------|------|
| id | UUID | PK | — |
| user_id | UUID | FK → users.id | 用户 |
| document_id | UUID | FK → documents.id | 文档 |
| created_at | TIMESTAMP | NOT NULL | 收藏时间 |

#### browse_history

| 列 | 类型 | 约束 | 说明 |
|----|------|------|------|
| id | UUID | PK | — |
| user_id | UUID | FK → users.id | 用户 |
| document_id | UUID | FK → documents.id | 文档 |
| created_at | TIMESTAMP | NOT NULL | 浏览时间 |

### 7.3 索引建议

当前未显式定义数据库索引（除主键和外键）。建议添加：

| 表 | 索引列 | 理由 |
|----|--------|------|
| documents | (category_id, is_deleted) | 分类维度列表查询 |
| documents | (uploader_id, is_deleted) | 个人上传列表 |
| documents | (is_deleted, updated_at DESC) | 首页最近更新 |
| documents | (is_deleted, category_id) | 权限过滤 |
| favorites | (user_id, document_id) | 收藏状态查询 |
| browse_history | (user_id, created_at DESC) | 浏览历史 |
| categories | (parent_id) | 树形递归查询 |

---

## 8. API 接口设计

### 8.1 接口总览

| 方法 | 路径 | 认证 | 说明 |
|------|------|:---:|------|
| `POST` | `/api/auth/login` | ❌ | 登录(限流) |
| `POST` | `/api/auth/register` | ❌ | 注册 |
| `GET` | `/api/auth/me` | ✅ | 当前用户信息 |
| `GET` | `/api/categories` | ❌(可选) | 分类树(按权限) |
| `POST` | `/api/categories` | super_admin | 创建分类 |
| `PUT` | `/api/categories/{id}` | super_admin | 编辑分类 |
| `DELETE` | `/api/categories/{id}` | super_admin | 删除分类 |
| `GET` | `/api/documents` | ❌(可选) | 文档列表(分页/筛选/排序) |
| `GET` | `/api/documents/{id}` | ❌(可选) | 文档详情 |
| `POST` | `/api/documents` | editor+ | 上传文档 |
| `PUT` | `/api/documents/{id}` | ✅ | 编辑文档 |
| `DELETE` | `/api/documents/{id}` | ✅ | 软删除 |
| `GET` | `/api/documents/{id}/preview` | ❌(token) | 流式预览 |
| `GET` | `/api/documents/{id}/preview-token` | ✅ | 获取预览token |
| `GET` | `/api/documents/{id}/download` | ❌(可选) | 下载 |
| `GET` | `/api/search` | ❌(可选) | 全文搜索 |
| `GET` | `/api/me/uploads` | ✅ | 我的上传 |
| `GET` | `/api/me/favorites` | ✅ | 我的收藏 |
| `POST` | `/api/me/favorites/{id}` | ✅ | 添加收藏 |
| `DELETE` | `/api/me/favorites/{id}` | ✅ | 取消收藏 |
| `GET` | `/api/me/history` | ✅ | 浏览历史 |
| `GET` | `/api/me/stats` | ✅ | 个人统计 |
| `GET` | `/api/admin/users` | admin | 用户列表 |
| `POST` | `/api/admin/users` | admin | 创建用户 |
| `PUT` | `/api/admin/users/{id}` | admin | 编辑用户 |
| `DELETE` | `/api/admin/users/{id}` | super_admin | 删除用户 |
| `GET` | `/api/health` | ❌ | 健康检查 |

### 8.2 通用约定

- **响应格式**: `{"data": ...}` 或直接返回对象（各接口不统一，待规范化）
- **分页格式**: `{items, total, page, size, pages}`
- **错误格式**: `{"detail": "错误描述"}`
- **认证方式**: `Authorization: Bearer <JWT>`
- **预览认证**: `?token=<preview_token>` (iframe 无法携带 Header)
- **日期格式**: ISO 8601 字符串

### 8.3 权限过滤逻辑统一性

| 场景 | can_view_document | list_documents | 一致性 |
|------|:---:|:---:|:---:|
| Guest → 未分类文档 | ✅ 允许 | ❌ 不返回 | ⚠️ 不一致 |
| 无可见分类用户 → 未分类文档 | ✅ 允许 | ✅ 返回 | ⚠️ 存疑 |
| 普通用户 → 自己上传的文档 | ✅ 允许 | ✅ 返回 | ✅ |

---

## 9. 前端设计

### 9.1 页面结构

```
App.vue
├── /login          → LoginView (全屏登录页)
├── /register       → RegisterView (全屏注册页)
├── /               → MainLayout (主布局)
│   ├── AppHeader   (顶部导航: Logo, 搜索框, 用户菜单)
│   ├── WorkflowSidebar (左侧工作流: 仅管理员+器械注册部)
│   ├── AppFooter   (底部版权信息)
│   └── <router-view>
│       ├── /                       → HomeView (首页)
│       ├── /category/:id?          → CategoryView (分类详情+文档列表)
│       ├── /document/:id           → DocumentView (文档详情+预览+工具栏)
│       ├── /search                 → SearchView (搜索结果)
│       └── /personal               → PersonalView (个人工作台)
├── /admin          → AdminLayout (管理后台)
│   ├── /admin/documents  → DocumentManage
│   ├── /admin/categories → CategoryManage
│   ├── /admin/users      → UserManage
│   └── /admin/settings   → SystemSettings
└── /*              → NotFoundView
```

### 9.2 设计规范

| 规范项 | 值 |
|--------|-----|
| **主色** | `#c88a04` (金色) |
| **主色浅** | `#e6a817` |
| **主色深** | `#9a6b04` |
| **强调色** | `#e67e22` (橙) |
| **侧边栏背景** | `#1e293b` (深灰蓝) |
| **字体** | Microsoft YaHei / 微软雅黑 |
| **组件库** | Element Plus 2.9+ |
| **CSS 方案** | Scoped CSS + CSS Variables |
| **图标** | Element Plus Icons (@element-plus/icons-vue) |

### 9.3 路由守卫

| 守卫条件 | 行为 |
|----------|------|
| `meta.requiresAuth` + 未登录 | 重定向到 `/login` |
| `meta.guest` + 已登录 | 重定向到 `/` |
| `meta.roles` + 角色不匹配 | 重定向到 `/` |
| `redirect` 参数 | 校验 `startsWith('/') && !startsWith('//')` 防 Open Redirect |

### 9.4 状态管理 (Pinia)

**authStore** 唯一全局 store:

| 状态 | 类型 | 说明 |
|------|------|------|
| `token` | `ref<string>` | JWT Token (持久化到 localStorage) |
| `user` | `ref<User \| null>` | 当前用户信息 |
| `isLoggedIn` | `computed<boolean>` | token 是否非空 |
| `isAdmin` | `computed<boolean>` | 是否为 super_admin/dept_admin |

| 方法 | 说明 |
|------|------|
| `login(username, password)` | 登录 → 存储 token → 跳转 |
| `fetchMe()` | 从后端刷新用户信息 |
| `logout()` | 清除 token → 跳转登录页 |

---

## 10. 安全设计

### 10.1 安全措施总览

| 安全层面 | 措施 | 状态 |
|----------|------|:---:|
| **认证** | JWT (HS256, 8小时过期) + bcrypt 密码哈希 | ✅ |
| **传输** | HTTPS (Nginx SSL 终结) | ✅ |
| **暴力破解** | 登录滑动窗口限流 (10次/5分钟/IP) | ✅ |
| **注入防护** | SQLAlchemy ORM 参数化查询 | ✅ |
| **注入防护** | Meilisearch 过滤器单引号转义 | ✅ |
| **XSS** | 搜索高亮先 HTML 转义再插入标记 | ✅ |
| **Open Redirect** | redirect 参数路径+协议校验 | ✅ |
| **信息泄露** | 生产环境错误处理不暴露异常类型 | ✅ |
| **预览链接可嵌入性** | URL 协议白名单 + 域名白名单 | ✅ |
| **预览 iframe** | sandbox="allow-scripts allow-same-origin" | ✅ |
| **CORS** | allow_origins=["*"], allow_credentials=False | ⚠️ 较宽松 |

### 10.2 安全待改进项

| 问题 | 严重程度 | 状态 |
|------|:---:|:---:|
| dept_admin 可提升权限为 super_admin (创建+编辑) | 🔴 Critical | ✅ 已修复 (55e95d6) |
| dept_admin 可管理其他部门用户 | 🟠 High | ✅ 已修复 (55e95d6) |
| 无可见分类用户返回未分类文档 (权限泄露) | 🟠 High | ❌ 待修复 |
| 删除分类不处理关联文档 (孤儿文档) | 🟠 High | ❌ 待修复 |
| 文档列表与 can_view 权限模型不一致 | 🟠 High | ❌ 待修复 |
| Guest 可查看所有未分类文档 | 🟡 Medium | ❌ 待修复 |
| 创建文档不校验 category_id 存在性 | 🟡 Medium | ❌ 待修复 |
| 创建文档不校验用户对目标分类的上传权限 | 🟡 Medium | ❌ 待修复 |
| view_count 双重计数 (详情+预览) | 🟡 Medium | ❌ 待修复 |
| 登录限流字典内存泄漏 | 🟡 Medium | ❌ 待修复 |

---

## 11. 部署架构

### 11.1 服务器配置

| 项目 | 规格 |
|------|------|
| **机型** | Lenovo ThinkCentre M730q |
| **CPU** | Pentium Gold G6400T |
| **内存** | 8GB RAM |
| **存储** | 240GB SSD |
| **OS** | Ubuntu 22.04 |
| **内网IP** | 192.168.60.175 |
| **外部访问** | HTTPS :443 → Nginx → uvicorn :8000 |

### 11.2 Docker 服务

| 服务 | 容器名 | 镜像 | 端口 |
|------|--------|------|------|
| PostgreSQL 16 | marweis-pg | pgvector/pgvector:pg16 | 5432 |
| Meilisearch | marweis-meili | getmeili/meilisearch:v1.10 | 7700 |
| MinIO | marweis-minio | minio/minio | 9000, 9001 |
| Gotenberg | marweis-gotenberg | gotenberg/gotenberg:8 | 3000 |

### 11.3 部署流程

```
本地开发 (Windows VSCode)
  │
  ├── git push origin master → GitHub (私有仓库)
  │
  └── git push server master → 服务器 (192.168.60.175)
        │
        ├── git pull origin master
        ├── cd frontend && npx vite build --mode production
        │   (前端构建为静态文件到 dist/)
        ├── fuser -k 8000/tcp
        └── nohup python3 -m uvicorn app.main:app
            --host 127.0.0.1 --port 8000 &
```

### 11.4 环境变量 (.env)

| 变量 | 说明 | 敏感 |
|------|------|:---:|
| DB_USER / DB_PASSWORD / DB_HOST / DB_PORT / DB_NAME | 数据库连接 | ✅ |
| JWT_SECRET | JWT 签名密钥 | ✅ |
| MEILI_URL / MEILI_MASTER_KEY | Meilisearch 连接 | ✅ |
| MINIO_ENDPOINT / MINIO_ACCESS_KEY / MINIO_SECRET_KEY | MinIO 凭证 | ✅ |
| MINIO_PUBLIC_ENDPOINT | MinIO 公网地址 | ❌ |
| GOTENBERG_URL | Gotenberg 地址 | ❌ |
| MAX_UPLOAD_SIZE_MB | 上传大小限制 | ❌ |

---

## 12. 已知问题与改进建议

### 12.1 按严重程度排序

#### 🔴 Critical (已修复)

1. **dept_admin 权限提升** — 已修复：dept_admin 现在只能创建 editor/employee/guest 角色，只能在本部门操作

#### 🟠 High (待修复)

1. **H-1: 无分类用户的文档列表逻辑错误**
   - 文件: `backend/app/api/documents.py:109-111`
   - 问题: 当用户无可见分类时返回 `category_id IS NULL` 文档而非空列表
   - 修复: 将 `Document.category_id.is_(None)` 改为 `sqlalchemy.false()`

2. **H-2: 删除分类导致文档成为孤儿**
   - 文件: `backend/app/api/categories.py:114-133`
   - 问题: 删除分类不清除关联文档的 category_id，且 document.category_id 无 FK 约束
   - 修复: 删除前将相关文档 category_id 设为 NULL 或拒绝删除有关联文档的分类

3. **H-3/H-4: 权限模型不一致**
   - Guest 的 `can_view_document` 和 `list_documents` 对未分类文档行为不一致
   - 建议: 统一权限检查逻辑，或以 `can_view_document` 为准在列表接口做后过滤

#### 🟡 Medium (待修复)

4. **M-1/M-3: 不校验 category_id 存在性** — 创建/更新文档时添加分类存在性检查
5. **M-2: 不校验上传目标分类权限** — 创建文档时检查用户是否有权上传到该分类
6. **M-4: view_count 双重计数** — 移除 preview 端点的 view_count++（详情已计数）
7. **M-7: 登录限流内存泄漏** — 使用 `cachetools.TTLCache` 替代普通 dict
8. **M-8: Guest 可查看未分类文档** — 制定明确策略（允许/拒绝/仅限登录用户）

#### 🟢 Low (待改进)

9. **L-1: 注册 display_name 未验证** — 添加长度和内容校验
10. **L-2: CORS 较宽松** — 生产环境建议限制具体 origin
11. **L-3: CategoryView 关键词搜索不生效** — 后端 `list_documents` 不支持 keyword 参数
12. **L-5: Meilisearch 索引异常静默吞没** — 增加监控告警

### 12.2 架构改进建议

| 建议 | 说明 | 优先级 |
|------|------|:---:|
| **添加数据库索引** | 详见 7.3 节 | 🟠 High |
| **SystemSettings 对接后端** | 当前设置页面是纯前端展示，未持久化 | 🟡 Medium |
| **添加 Alembic 迁移** | 将现有 schema 导出为初始迁移 | 🟡 Medium |
| **document.category_id 添加 FK** | 防止孤儿文档 | 🟡 Medium |
| **统一 API 响应格式** | `{code, message, data}` 包络 | 🟢 Low |
| **添加 API 文档导出** | FastAPI 自带 /docs → 可导出 OpenAPI spec | 🟢 Low |
| **前端错误边界** | Vue errorBoundary 捕获渲染错误 | 🟢 Low |

---

## 13. 待开发功能

### 13.1 短期 (v0.2)

| 功能 | 说明 | 工作量估算 |
|------|------|:---:|
| **修复所有 High 级问题** | H1-H4 权限和逻辑缺陷 | 2-3天 |
| **其他部门工作流侧边栏** | 临床评价部/临床试验部等的专属工作流导航 | 2-3天 |
| **通讯录模块卡片展示** | 第7模块的通讯录从链接型升级为卡片 | 1-2天 |
| **批量文档导入 UI** | 前端拖拽上传 + 批量选择分类/标签 | 3-5天 |

### 13.2 中期 (v0.3)

| 功能 | 说明 |
|------|------|
| **文档版本管理** | 同文档多版本存储 + 版本历史查看 |
| **文档评论/批注** | 允许对文档添加评论讨论 |
| **文档分享链接** | 生成限时/限次的外部分享链接 |
| **数据统计仪表盘** | 部门维度: 上传量/查看量/下载量趋势图 |
| **移动端适配** | 完整的响应式布局，支持手机查看 |
| **通知系统** | 新文档通知/分类更新通知 |

### 13.3 长期 (v1.0)

| 功能 | 说明 |
|------|------|
| **AI 智能摘要** | 上传文档自动生成摘要和标签 |
| **向量检索 (RAG)** | 基于 pgvector 的语义搜索 + AI 问答 |
| **法规更新监控** | 自动爬取 NMPA/CMDE/FDA 官网 → 新法规提醒 |
| **SSO 集成** | 对接企业 AD/LDAP 统一认证 |
| **审计日志** | 完整的操作审计 trail |
| **多语言支持** | 中英文界面切换 |

---

## 附录 A: 技术债务清单

| 序号 | 项目 | 文件 | 说明 |
|:---:|------|------|------|
| 1 | document.category_id 无 FK | models/document.py:14 | 缺少数据库层面约束 |
| 2 | CategoryView keyword 参数无效 | CategoryView.vue:138 | 前端传参后端不支持 |
| 3 | SystemSettings 未对接后端 | SystemSettings.vue | 纯前端占位 |
| 4 | view_count 在 preview+detail 双重递增 | api/documents.py:152,384 | 统计失准 |
| 5 | 登录限流用普通 dict | api/auth.py:15 | 长期运行内存泄漏 |
| 6 | search index 失败静默吞没 | services/search_service.py:66 | 无告警 |
| 7 | CORS allow_origins=["*"] | main.py:23 | 生产环境不建议 |
| 8 | Alembic 未有效使用 | alembic/ | 未记录初始迁移 |
| 9 | 缺少自动化测试 | tests/ | 目录存在但为空 |
| 10 | seed 数据硬编码密码 | scripts/seed.py | 示例用，生产需改密码 |

## 附录 B: 文件统计

| 层级 | 文件数 | 代码行数(估) |
|------|:---:|:---:|
| 后端 API | 6 | ~600 |
| 后端 Models | 5 | ~80 |
| 后端 Services | 2 | ~200 |
| 后端 Middleware | 2 | ~30 |
| 后端 Core (config/auth/db/permissions) | 4 | ~200 |
| 后端 Schemas | 1 | ~200 |
| 前端 Views | 11 | ~1800 |
| 前端 Components | 4 | ~500 |
| 前端 Store/Router/API | 3 | ~250 |
| 脚本/部署 | 10+ | ~800 |
| **总计** | **~50** | **~4,600** |

---

> **文档作者**: AI 代码审查 (基于全量源码阅读)  
> **审查范围**: d:\workSpace\marweis-kb 全部源码文件  
> **审查方式**: 逐文件阅读 + 交叉引用分析  
> **首次编写**: 2026-07-14
