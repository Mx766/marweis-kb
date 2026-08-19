# 企业知识库系统（Enterprise Knowledge Base）

企业级知识库与文件管理系统：以部门为边界的文档知识库 + 团队公盘文件存储 + 管理后台 + 面向 AI 智能体的知识供给。

## 功能概览

- **知识库**：多级分类树、部门可见性隔离、细粒度权限（仅负责人 / 可下载 / 仅本人 / 只读 / 成员上传）、文档检索、访问记录。
- **文件公盘**：部门公盘与个人空间、文件夹上传（支持空文件夹与拖拽）、回收站、星标收藏、文件发送、在线预览与下载权限控制。
- **在线预览**：PDF / Word / Excel / PPT 经 Gotenberg 与 OnlyOffice 在线渲染，支持全屏查看。
- **AI 知识库**：为每篇文档生成 Markdown 副本，供数字员工 / Agent 通过 API 调用，普通用户界面不展示。
- **管理后台**：仪表盘、文档管理、分类管理、用户管理、访问记录、系统设置、AI 知识库、数据更新任务。
- **数据采集更新**：OPS 任务中心对接自动更新代理，支持 NMPA / CMDE 等监管数据的增量抓取与导入。
- **搜索**：Meilisearch 全文检索，按分类、格式、上传者过滤。

## 技术栈

| 层 | 技术 |
| --- | --- |
| 后端 | Python 3.12 / FastAPI / SQLAlchemy(async) |
| 数据库 | PostgreSQL 16 + pgvector |
| 对象存储 | MinIO |
| 搜索引擎 | Meilisearch |
| 文档转换 | Gotenberg |
| 在线编辑/预览 | OnlyOffice Document Server |
| 前端 | Vue 3 / TypeScript / Vite / Element Plus / ECharts |
| 部署 | Docker Compose / systemd |

## 架构

```text
┌──────────────────────────────────────────────────────────┐
│                     Vue3 前端 (Vite)                      │
└───────────────┬──────────────────────────────────────────┘
                │  REST / JWT
┌───────────────▼──────────────────────────────────────────┐
│                 FastAPI 后端 (uvicorn)                    │
│  知识库 / 文件公盘 / 权限 / 搜索 / AI / OPS / 管理         │
└───┬────────────┬────────────┬────────────┬───────────────┘
    │            │            │            │
    ▼            ▼            ▼            ▼
 PostgreSQL   MinIO       Meilisearch  Gotenberg/OnlyOffice
 (+pgvector)  文件存储      全文索引      文档预览/编辑
```

## 目录结构

```text
backend/
  app/                  FastAPI 应用（api / models / services / permissions）
  alembic/              数据库迁移
  scripts/demo_files/   示例文档（演示上传与预览）
  .env.example          环境变量模板
frontend/
  src/                  Vue3 源码（views / components / api / stores）
samples/                演示数据（知识库示例文档）
```

## 快速开始

### 依赖服务

建议用 Docker 启动依赖：PostgreSQL(pgvector)、MinIO、Meilisearch、Gotenberg、OnlyOffice。

### 后端

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # 按需修改数据库/MinIO/Meilisearch 配置
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### 前端

```bash
cd frontend
npm install
npm run dev                        # 默认 http://localhost:5173
```

### 示例数据

`samples/` 与 `backend/scripts/demo_files/` 提供演示文档，可直接上传到知识库体验完整流程。

## 权限模型

- **超级管理员**：全部模块与所有部门数据。
- **部门管理员**：本部门知识库、用户与公盘管理。
- **编辑 / 员工 / 访客**：按分类可见性与文件权限访问。

## 安全说明

所有密钥与连接信息通过环境变量注入（见 `backend/.env.example`），请勿将 `.env` 提交到版本库。

## License

[MIT](LICENSE)
