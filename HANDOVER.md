# 迈瑞生知识库 — 项目交接文档 (2026-07-14)

## 快速入口

| 项目 | 地址/值 |
|------|---------|
| **系统访问** | https://192.168.60.175 (HTTPS) / http://192.168.60.175:8000 已废弃 |
| **管理员** | 见服务器 .env 或 seed.py |
| **测试账号** | zhangsan (器械注册部), 密码见 seed.py |
| **GitHub** | https://github.com/Mx766/marweis-kb |
| **服务器** | mx766@192.168.60.175 (SSH Key 认证) |
| **本地仓库** | d:\workSpace\marweis-kb |

## 服务器信息

Ubuntu 22.04, Lenovo ThinkCentre M730q, 8GB RAM

### 服务端口

| 端口 | 服务 | 说明 |
|------|------|------|
| 80 | Nginx → 301 HTTPS | HTTP 自动跳转 |
| 443 | Nginx HTTPS | 反向代理到 8000 |
| 8000 | uvicorn | 仅监听 127.0.0.1 |
| 5432 | PostgreSQL 16 | Docker: marweis-pg |
| 7700 | Meilisearch | Docker: marweis-meili |
| 9000/9001 | MinIO | Docker: marweis-minio |
| 3000 | Gotenberg | Docker: marweis-gotenberg |

### SSL 证书

自签名证书，位置：`/etc/ssl/certs/marweis-kb.crt`，有效期 10 年。
Chrome 150+ 会拦截 HTTPS IP 地址。开发测试用 Firefox 或 `ssh -L 8080:127.0.0.1:8000 mx766@192.168.60.175` + `http://localhost:8080`。

## 技术栈

- 后端：FastAPI (Python 3.10) + SQLAlchemy async + PostgreSQL
- 前端：Vue 3 + TypeScript + Element Plus + Pinia + Vite
- 存储：MinIO (S3 兼容) + Gotenberg (文档转 PDF)
- 搜索：Meilisearch

## 目录结构

```
marweis-kb/
├── backend/
│   ├── app/
│   │   ├── api/          # auth, documents, categories, search, personal, admin
│   │   ├── models/       # User, Document, Category, Favorite, BrowseHistory
│   │   ├── schemas/      # Pydantic 请求/响应模型
│   │   ├── services/     # file_service (MinIO), search_service (Meilisearch)
│   │   ├── middleware/    # error_handler, logging
│   │   ├── auth.py       # JWT + bcrypt + 密码校验
│   │   ├── config.py     # pydantic_settings, 环境变量
│   │   ├── database.py   # async_session
│   │   ├── main.py       # FastAPI 入口, CORS, 中间件, SPA fallback
│   │   └── permissions.py # 部门/角色权限
│   ├── scripts/          # seed.py, migrate_categories.py, cleanup_duplicates.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── views/        # 页面组件
│   │   ├── components/layout/  # AppHeader, MainLayout, WorkflowSidebar
│   │   ├── api/client.ts       # Axios + TS 类型
│   │   ├── stores/auth.ts      # Pinia 认证
│   │   ├── styles/global.css   # CSS 变量 (主色 #c88a04 黄色)
│   │   └── router/       # Vue Router
│   └── package.json
├── docker-compose.yml
├── nginx-marweis-kb.conf  # Nginx 配置
└── deploy.sh
```

## 当前功能状态

### ✅ 已完成

- 登录/注册 (JWT, bcrypt, 密码强度校验)
- 文档 CRUD (上传/编辑/删除)
- 文件上传 → MinIO + Gotenberg 自动转 PDF 预览
- 在线预览 (后端 StreamingResponse 代理 PDF, 内联显示)
- 下载 (MinIO presigned URL)
- 全文搜索 (Meilisearch + SQL fallback)
- RBAC 权限 (super_admin / dept_admin / editor / employee / guest)
- 部门分类可见性控制
- 管理后台 (用户管理/分类管理/文档管理)
- 分类管理按部门标签页分组
- 左侧工作流侧边栏 (器械注册部 7 模块)
- Nginx HTTPS 反向代理
- SPA fallback (刷新不 404)
- 请求日志中间件
- 登录限流

### ❌ 待修复

1. **预览功能**: 后端正常 (200, PDF stream), 前端 iframe 可能不显示, 需调试 DocumentView.vue 的 `fetchPreviewToken` 和 iframe src
2. **侧边栏跳转**: 7 月 14 日最后修改了 CategoryView（递归查找 + 去掉了重复侧边栏）, 但未经充分测试
3. **Chrome 150+ 拦截**: HTTPS IP 地址被 Chrome SmartScreen 拦截, 正式域名+正规证书后解决
4. **GitHub 推送**: seed_docs/ 大文件 (621MB) 仍在 git 历史中, 需 filter-branch 清理后 force push

### ✅ 2026-07-14 已修复逻辑问题

1. **文档列表权限 (H-1)**: 无可见分类用户现在返回空列表而非泄露未分类文档；有可见分类用户能正常浏览未分类文档（与 `can_view_document` 一致）
2. **删除分类处理关联文档 (H-2)**: 删除分类时自动将关联文档的 `category_id` 设为 NULL，避免孤儿文档
3. **view_count 双重计数 (M-4)**: 预览端点不再递增 view_count，详情端点已负责计数
4. **登录限流内存泄漏 (M-7)**: 增加线程锁 + 定时清理过期条目，防止长期运行内存增长
5. **分类存在性校验 (M-1/M-3)**: 创建和更新文档时验证 `category_id` 是否存在
6. **分类上传权限 (M-2)**: 非 super_admin 用户只能将文档上传到其部门可见的分类

### 待开发

- 其他部门的工作流导航（当前仅器械注册部有）
- 通讯录模块的卡片式展示
- 批量文档导入功能

## 核心 API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/login` | 登录 |
| POST | `/api/auth/register` | 注册 |
| GET | `/api/auth/me` | 当前用户 |
| GET | `/api/categories` | 分类树 (按部门过滤) |
| POST/PUT/DELETE | `/api/categories[/{id}]` | 分类 CRUD |
| GET | `/api/documents` | 文档列表 (分页/筛选) |
| GET | `/api/documents/{id}` | 文档详情 |
| POST | `/api/documents` | 上传文档 |
| PUT/DELETE | `/api/documents/{id}` | 更新/软删除 |
| GET | `/api/documents/{id}/preview` | PDF 流式预览 |
| GET | `/api/documents/{id}/preview-token` | 限时预览 token |
| GET | `/api/documents/{id}/download` | 下载 |
| GET | `/api/search?q=` | 搜索 |
| GET | `/api/admin/users` | 用户管理 |
| GET/POST | `/api/me/favorites/{id}` | 收藏/取消 |
| GET | `/api/me/stats` | 个人统计 |
| GET | `/api/health` | 健康检查 |

## 部署流程

```bash
# 本地
cd d:\workSpace\marweis-kb
git add -A && git commit -m "描述"
git push server master

# 服务器 (SSH)
ssh mx766@192.168.60.175
cd ~/marweis-kb && git pull origin master

# 前端改动需重建
cd ~/marweis-kb/frontend && npx vite build --mode production

# 后端改动需重启
fuser -k 8000/tcp
cd ~/marweis-kb/backend
nohup python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000 > ~/logs/backend.log 2>&1 &
```

## 数据库

### 分类数据结构

器械注册部工作流模块 (sort_order 1-7, visible_departments=["器械注册部"]):

```
1. 参考文件 → 通用法规（国内）, 通用法规（国外）, 指导原则, 审评论坛
2. 分类目录
3. 校验技术要求
4. 临床评价资料 → 临床文献, 国家局网站, 说明书
5. 发补 → 例卷, 发补意见
6. 注册证书 → 注册证书, 注册资料
7. 通讯录 → 中央药监局, 地方药监局
```

批量导入的文档 (01_有源手术器械 等 3000+ 篇) 通过 `migrate_categories.py` 已迁移到对应模块下。

### 迁移脚本

- `scripts/migrate_categories.py` — 将旧分类移到新工作流模块
- `scripts/cleanup_duplicates.py` — 隐藏重复的旧器械注册部顶级分类
- `scripts/seed.py` — 初始化数据库 (仅首次部署用)

## 设计规范

- 主色: `#c88a04` (金色)
- 侧边栏: `#1e293b` 深色背景
- 字体: Microsoft YaHei
- CSS 变量在 `frontend/src/styles/global.css`
