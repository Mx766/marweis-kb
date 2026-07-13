# 迈瑞生知识库 — 项目交接文档

## 概述

迈瑞生知识库 (Marweis KB) 是迈瑞生集团内部的医疗器械注册法规知识管理平台。
用于存储、搜索和在线预览 NMPA/FDA/CE 审评报告、指导原则、法规文件。

## 快速入口

| 项目 | 地址/值 |
|------|---------|
| **系统访问** | http://192.168.60.175:8000 |
| **管理员账号** | admin / marweis2026 |
| **GitHub 仓库** | https://github.com/Mx766/marweis-kb |
| **服务器地址** | 192.168.60.175 (SSH: mx766@192.168.60.175) |
| **本地仓库路径** | d:\workSpace\marweis-kb |

---

## 服务器信息

| 项 | 详情 |
|----|------|
| 硬件 | Lenovo ThinkCentre M730q, Pentium Gold G6400T, 8GB RAM, 240GB SSD |
| 系统 | Ubuntu 22.04.5 LTS |
| CPU | 双核四线程 @ 3.40GHz |
| 磁盘 | 100G 已分配 / 120G 空闲可扩容 (LVM) |
| SSH | 已配置 Key 认证 |

### Docker 服务

| 容器 | 服务 | 端口 |
|------|------|------|
| marweis-pg | PostgreSQL 16 + pgvector | 5432 |
| marweis-meili | Meilisearch 全文搜索 | 7700 |
| marweis-minio | MinIO 对象存储 | 9000 (API) / 9001 (控制台) |
| marweis-gotenberg | Gotenberg 文档转 PDF | 3000 |
| hermes | AI Agent (非知识库组件) | - |

---

## 技术架构

```
┌──────────────────────────────────────────────────┐
│  前端: Vue3 + TypeScript + Element Plus          │
│  FastAPI 直接 serve dist/ 静态文件               │
│  http://192.168.60.175:8000                      │
└────────────────┬─────────────────────────────────┘
                 │
┌────────────────▼─────────────────────────────────┐
│  后端: FastAPI (Python 3.10)                      │
│  ┌──────────┬──────────┬──────────┬──────────┐  │
│  │ 认证模块 │ 文档模块 │ 分类模块 │ 管理模块 │  │
│  │ JWT+RBAC │ CRUD+上传│ 树形结构 │ 用户管理 │  │
│  └──────────┴──────────┴──────────┴──────────┘  │
└────┬─────────┬────────────┬──────────────────────┘
     │         │            │
┌────▼──┐ ┌───▼────┐ ┌─────▼──────┐
│PostgreSQL│ │Meilisearch│ │   MinIO     │
│ (元数据) │ │ (全文搜索)│ │ (文件存储)  │
└──────────┘ └──────────┘ └─────┬──────┘
                                │
                         ┌──────▼──────┐
                         │  Gotenberg   │
                         │ (预览转PDF)  │
                         └─────────────┘
```

### 目录结构

```
marweis-kb/
├── backend/
│   ├── app/
│   │   ├── api/          # API 路由 (auth, documents, categories, search, admin, personal)
│   │   ├── models/       # SQLAlchemy 数据模型
│   │   ├── schemas/      # Pydantic 请求/响应模式
│   │   ├── services/     # 业务服务 (文件上传, 搜索)
│   │   ├── middleware/   # 全局异常处理
│   │   ├── auth.py       # JWT 认证 + RBAC 权限
│   │   ├── config.py     # 配置 (环境变量)
│   │   ├── database.py   # 数据库连接
│   │   ├── main.py       # FastAPI 应用入口
│   │   └── permissions.py # 文档/分类权限服务
│   ├── alembic/          # 数据库迁移
│   ├── scripts/          # 种子数据 & 导入脚本
│   ├── .env              # 环境变量 (不提交到 git)
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── views/        # 页面组件
│   │   ├── components/   # 布局组件
│   │   ├── api/client.ts # Axios HTTP 客户端
│   │   ├── stores/auth.ts # Pinia 认证状态
│   │   └── router/       # Vue Router 路由
│   ├── dist/             # 构建产物
│   └── package.json
├── docker-compose.yml    # Docker 服务编排
├── deploy.sh             # 一键部署脚本
├── DEVLOG.md             # 开发日志
├── seed_docs/            # 种子文档 (示例 + 知识库.zip)
└── .gitignore
```

---

## 日常运维

### 部署流程

```bash
# 本地开发完成后:
cd d:\workSpace\marweis-kb
git add -A && git commit -m "描述修改内容"
git push server master    # 推送到服务器
git push origin master    # 推送到 GitHub (备份)

# 服务器上拉取并重启:
ssh mx766@192.168.60.175
cd ~/marweis-kb && git pull origin master
fuser -k 8000/tcp          # 停止旧进程
cd backend && nohup python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > ~/logs/backend.log 2>&1 &
```

### 或使用部署脚本

```bash
# 本地执行 deploy.sh 一键推送 + 服务器拉取 + 重启
bash deploy.sh
```

### 服务器启动/重启

```bash
ssh mx766@192.168.60.175
# 查看进程
ps aux | grep uvicorn
# 停止
fuser -k 8000/tcp
# 启动
cd ~/marweis-kb/backend
nohup python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > ~/logs/backend.log 2>&1 &
# 检查
curl http://localhost:8000/api/health
```

### Docker 服务管理

```bash
# 启动所有服务
cd ~/marweis-kb && docker compose up -d

# 查看状态
docker ps

# 查看日志
docker logs marweis-pg
docker logs marweis-meili
```

### 前端重新构建

```bash
# 服务器上
cd ~/marweis-kb/frontend
npm install
npx vite build --mode production
# 重启后端即可 serve 新的 dist/
```

---

## 关键 API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/login` | 登录获取 token |
| GET | `/api/categories` | 获取分类树 |
| GET | `/api/documents` | 文档列表 (支持分页/筛选/搜索) |
| GET | `/api/documents/{id}` | 文档详情 |
| POST | `/api/documents` | 上传文档 (multipart/form-data) |
| PUT | `/api/documents/{id}` | 更新文档 |
| DELETE | `/api/documents/{id}` | 软删除文档 |
| GET | `/api/documents/{id}/download` | 下载文件 (307 → MinIO presigned URL) |
| GET | `/api/documents/{id}/preview` | 在线预览 (Gotenberg 自动转 PDF) |
| GET | `/api/search?q=关键词` | 全文搜索 |
| GET | `/api/admin/users` | 用户管理 |
| GET | `/api/health` | 健康检查 |

---

## 权限系统

### 角色

| 角色 | 权限 |
|------|------|
| super_admin | 全部权限 |
| dept_admin | 管理本部门用户, 编辑本部门文档 |
| editor | 上传/编辑自己的文档 |
| employee | 浏览 + 下载 |
| guest | 只读公开文档 |

### 部门

器械注册部、临床评价部、临床试验部、生产体系部、化妆品·医美部、特医食品部、管理层

---

## 已导入的数据

2,343 篇文档，按以下分类组织：

- **审评报告** (1,305 篇 PDF) — 医疗器械 + 体外诊断试剂
- **指导原则** (953 篇 docx) — 医疗器械注册审查 + IVD
- **法规** (约 70 篇) — NMPA / FDA / CE MDR
- **分类目录** (12 篇) — 器械分类界定
- **其他** — 产品库、豁免目录等

文件存储在 MinIO (`marweis-documents` bucket)，元数据在 PostgreSQL。

---

## 批量导入新文件

### 方式 1: 直写 MinIO + 数据库（最快，推荐大量文件）

```bash
# 1. 先把文件传到服务器 /tmp/kb_import/ 目录
#    保持目录结构，文件名即文档标题

# 2. 运行导入脚本
ssh mx766@192.168.60.175
python3 /tmp/fast_import.py
```

### 方式 2: API 逐个上传（少量文件）

```
POST /api/documents  (multipart/form-data)
参数: title, category_id, file, tags, summary
```

### 方式 3: 前端 UI 上传

访问 http://192.168.60.175:8000 → 管理后台 → 文档管理 → 上传

---

## 已知问题 & 注意事项

### 已修复的安全问题
- JWT token 过期时间计算错误 → 已修复
- Open Redirect 漏洞 → 已修复（域名白名单精确匹配）
- XSS (v-html) → 已修复（HTML 转义）
- 硬编码演示账号 → 已移除
- 生产环境信息泄露 → 已修复

### 待改进
- 导入脚本中的凭据是硬编码的（仅内网使用，问题不大）
- 前端分类树目前只显示两级，深层分类需点击切换
- 搜索功能依赖 Meilisearch 正常运行
- 还没有 HTTP → 所有流量走明文的 http，如需公网暴露建议加 Nginx + HTTPS

---

## 故障排查

| 问题 | 检查项 |
|------|--------|
| 网站打不开 | `ssh mx766@192.168.60.175` → `ps aux | grep uvicorn` |
| 搜索无结果 | `docker ps | grep meili` (Meilisearch 是否运行) |
| 下载失效 | `docker ps | grep minio` (MinIO 是否运行) |
| 预览失败 | `docker ps | grep gotenberg` (Gotenberg 是否运行) |
| Docker 未启动 | `docker compose up -d` (在 ~/marweis-kb 目录下) |
| 磁盘满 | `df -h /` (当前 32G/98G — 见上方服务器信息) |
| 内存不足 | `free -h` (8GB — 当前约 5GB 可用) |
| 查看后端日志 | `tail -100 ~/logs/backend.log` |
| 查看 API 错误 | `tail -100 ~/logs/backend.log | grep ERROR` |

---

## 文档版本

| 日期 | 说明 |
|------|------|
| 2026-07-10 | 项目初始化 |
| 2026-07-13 | 代码审查修复 21 项 + 部署架构搭建 + 批量导入 2343 篇 + 下载/预览功能 |
