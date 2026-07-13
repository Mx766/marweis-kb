# 迈瑞生知识库 — 开发日志

## 项目概况

- **项目名称**: 迈瑞生知识库 (Marweis KB)
- **版本**: v0.1.1-dev
- **技术栈**: FastAPI (Python) + Vue3 (TypeScript) + PostgreSQL + MinIO + Meilisearch + Docker
- **服务器**: Lenovo ThinkCentre M730q (Pentium Gold G6400T, 8GB RAM, 240GB SSD, Ubuntu 22.04)
- **仓库**: [GitHub](https://github.com/Mx766/marweis-kb) | 服务器 `mx766@192.168.60.175`

---

## 2026-07-10: 项目初始化

- 创建项目骨架: FastAPI 后端 + Vue3 前端
- Docker Compose 编排 PostgreSQL, Meilisearch, MinIO, Gotenberg
- 实现文档 CRUD, 用户认证 (JWT), RBAC 权限系统
- 实现分类树、全文搜索、个人中心、管理后台

## 2026-07-13: 代码审查 + 部署

### 代码审查 (21 项修复)

**Critical (7)**:
| 问题 | 修复 |
|------|------|
| 硬编码密钥 (密码/密钥直接写入 config.py) | 全部通过环境变量注入 |
| `expires_at` 计算错误 (返回用户创建时间而非 token 过期时间) | 使用 `datetime.now() + JWT_EXPIRE_HOURS` |
| Meilisearch 过滤器注入 (单引号未转义) | 添加 `_escape_meili_filter_value()` |
| 文档列表权限存在死代码 + 重复逻辑 | 统一使用 `PermissionService.get_visible_category_ids()` |
| 游客权限 AttributeError (只 query UUID 却访问 `.visible_departments`) | 查询完整 Category 对象 |
| 删除分类不处理子分类 (孤儿子分类) | 子分类 re-parent 到被删分类的父级 |
| `get_db` 自动提交导致部分 flush 被意外持久化 | 移除 auto-commit，所有变更端点显式 `commit()` |

**Medium (9)**: 异常静默吞没 → 加 logging；Meilisearch 非线程安全单例 → 加锁；路由守卫未校验角色 → 补全；用户创建无 department/role 校验 → 添加；MinIO `:latest` 标签 → 固定版本；登录无速率限制 → 滑动窗口限流；SQLAlchemy 风格混用 (Column vs Mapped) → 统一为 Mapped

**Low (5)**: 前端 401 用 `window.location.href` → `window.location.replace`；缺 `.env.example` 和 `.gitignore` → 创建；`UserProfile.model_validate` 覆盖 Pydantic 内置方法 → 重命名为 `from_orm()`；Alembic env.py 异步 runner 不完整 → 统一 `asyncio.run()`；搜索 fallback 不处理 tag 参数 → 添加

### 安全审查 (4 项修复)

- LoginView 移除硬编码演示账号密码 (admin/marweis2026)
- SearchView `v-html` 输出前转义 HTML 特殊字符防 XSS
- DocumentView `isEmbeddable` 增加 URL 协议白名单校验 (https/http only)
- error_handler 生产环境不暴露异常类型信息

### Git + 部署架构

```
本地 (VSCode) ──git push──▶ GitHub (私有仓库, Mx766/marweis-kb)
       │
       └──git push server──▶ 服务器 (192.168.60.175)
                                └── git pull → 重启 uvicorn
```

- 服务器 SSH Key 认证 (免密登录)
- 一键部署脚本 `deploy.sh`
- 后端集成前端静态文件服务 (SPA fallback)

## 2026-07-13 (续): 知识库批量导入

### 数据源

`D:\知识库\迈瑞生知识库\` — 公司历年积累的医疗器械注册审评报告和指导原则。

| 目录 | 内容 | 文件数 | 大小 |
|------|------|--------|------|
| 01 分类目录 | 器械分类界定汇总、IVD 分类目录 | 6 | 3 MB |
| 02 豁免临床评价目录 | 免于临床评价器械目录 | 3 | 2 MB |
| 03 临床路径 | 临床评价推荐路径 | 2 | 0.1 MB |
| 04 同产品查找 | 已上市产品库 | 1 | 0.02 MB |
| 05 审评报告 | CMDE 审评报告 (IVD + 22 类器械) | 741 | 503 MB |
| 06 指导原则 | 注册审查指导原则 (IVD + 23 类器械) | 647 | 205 MB |
| 07 法规 | NMPA/EU/FDA 核心法规 | 13 | 6 MB |
| **合计** | | **~1413** | **~719 MB** |

### 导入方案演进

**方案 A: API 逐文件上传** (被放弃)

- 通过 FastAPI `POST /api/documents` multipart/form-data 逐个上传
- 速度仅 ~0.5 文件/秒，1413 文件需要 ~40 分钟
- 瓶颈: `UploadFile` 底层 `SpooledTemporaryFile` 双写问题 + HTTP 协议开销
- 结论: 少量文件可行，大批量不可用

**方案 B: tar+ssh 传输 + 直写 MinIO + PostgreSQL** (最终方案)

1. Windows 本地用 `tar czf` 打包 → pipe through SSH → 服务器解压 (几十秒)
2. 服务器端 Python 脚本: 直接调用 boto3 写 MinIO + SQLAlchemy 批量 INSERT
3. 200 条/批次批量提交 PostgreSQL，单次提交包含完整元数据
4. 结果: **1413 文件 ~60 秒完成，速度提升 ~40 倍**

### 导入结果

| 指标 | 数值 |
|------|------|
| 总文档数 | 1,995 篇 (含 demo 数据) |
| .docx (指导原则) | 1,180 (59%) |
| .pdf (审评报告+法规) | 788 (40%) |
| 其他 (xlsx/txt/png/link) | 27 (1%) |
| 分类数 | 37 个 (含 23 类器械子分类) |

### 经验总结

1. **大批量文件导入不要走 HTTP API** — 协议开销 + FastAPI UploadFile 的 SpooledTemporaryFile 双写是巨大瓶颈
2. **直写存储层 + 批量 DB INSERT** 是最快路径 — 本地 localhost MinIO + PG 可达每秒数百条
3. **tar over SSH pipe** 是 Windows→Linux 传输大量文件的最佳方式 — 无需 rsync (Windows 不自带) 且比逐文件 scp 快几个数量级
4. **分类树应该提前规划好** — 本次的 23 类 NMPA 器械分类体系直接在导入时自动创建了子分类
