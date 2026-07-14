# 迈瑞生知识库 (Marweis KB) — 测试报告

**测试日期**: 2026-07-14  
**测试工程师**: AI Code Review  
**测试方法**: 白盒静态代码审查 (White-box Static Analysis)  
**测试范围**: 全栈 — 后端 (FastAPI) + 前端 (Vue3)  
**版本**: v0.1.1-dev (commit `8c50952`)

> 注意：服务器 (192.168.60.175) 和 Docker 服务当前不可达，本次测试为全量代码审查，未执行运行时测试。

---

## 一、测试覆盖范围

| 模块 | 文件 | 审查方式 |
|------|------|----------|
| 认证 (Auth) | `backend/app/auth.py`, `api/auth.py` | 完整审查 |
| 文档 (Documents) | `backend/app/api/documents.py` | 完整审查 |
| 分类 (Categories) | `backend/app/api/categories.py` | 完整审查 |
| 搜索 (Search) | `backend/app/api/search.py`, `services/search_service.py` | 完整审查 |
| 个人中心 (Personal) | `backend/app/api/personal.py` | 完整审查 |
| 管理后台 (Admin) | `backend/app/api/admin.py` | 完整审查 |
| 权限系统 | `backend/app/permissions.py` | 完整审查 |
| 文件服务 | `backend/app/services/file_service.py` | 完整审查 |
| 中间件 | `backend/app/middleware/*.py` | 完整审查 |
| 前端路由/状态 | `frontend/src/router/`, `stores/`, `api/` | 完整审查 |
| 前端页面 | `frontend/src/views/` | 完整审查 |

---

## 二、发现的问题汇总

### 严重程度定义

| 级别 | 定义 |
|------|------|
| 🔴 Critical | 权限提升/数据泄露/安全漏洞 |
| 🟠 High | 功能错误/数据完整性损坏 |
| 🟡 Medium | 逻辑缺陷/边界条件错误 |
| 🟢 Low | 代码质量/潜在风险 |

---

## 三、详细问题清单

### 🔴 Critical (2项)

#### C-1. dept_admin 可以创建 super_admin 账户（权限提升）

- **文件**: [backend/app/api/admin.py:54-88](backend/app/api/admin.py#L54-L88)
- **问题**: `create_user` 接口允许 `dept_admin` 创建用户，但没有限制 `dept_admin` 能分配的角色。`dept_admin` 可以通过 `POST /api/admin/users` 创建 `super_admin` 账户，实现权限提升。
- **根因**: 缺少角色层级校验 — 没有检查 `dept_admin` 只能创建 `role <= dept_admin` 的用户。
- **复现步骤**:
  1. 以 dept_admin 身份登录，获取 JWT
  2. `POST /api/admin/users`，body: `{"username":"hacker","password":"...","display_name":"Hacker","department":"器械注册部","role":"super_admin"}`
  3. 使用新创建的 super_admin 账户登录 → 获得完全管理员权限
- **影响**: 任意 dept_admin 可完全接管系统。

#### C-2. dept_admin 可以将现有用户角色提升为 super_admin（权限提升）

- **文件**: [backend/app/api/admin.py:91-116](backend/app/api/admin.py#L91-L116)
- **问题**: `update_user` 同样没有限制 `dept_admin` 能设置的角色。dept_admin 可以将本部门任意用户的 role 改为 `super_admin`。
- **根因**: 同 C-1，缺少角色层级校验。
- **影响**: 同上。

---

### 🟠 High (4项)

#### H-1. 文档列表权限逻辑错误：返回未分类文档而非空列表

- **文件**: [backend/app/api/documents.py:103-111](backend/app/api/documents.py#L103-L111)
- **问题**: 当用户没有可见分类时 (`visible_ids` 为空)，代码注释写 "return empty list"，但实际代码是:
  ```python
  conditions.append(Document.category_id.is_(None))
  ```
  这会返回所有 `category_id = NULL` 的文档，而非空列表。
- **根因**: 代码与注释不一致，逻辑错误。
- **复现**:
  1. 创建一个部门受限用户（该部门无可见分类）
  2. `GET /api/documents` → 返回未分类的文档（而非空列表）
- **影响**: 用户能看到不应该看到的未分类文档。

#### H-2. 删除分类导致文档成为孤儿（数据完整性损坏）

- **文件**: [backend/app/api/categories.py:114-133](backend/app/api/categories.py#L114-L133)
- **问题**: `delete_category` 只将子分类重新挂载到父级，但没有处理属于该分类的文档 (`Document.category_id` 仍指向已删除的 Category ID)。
- **根因**: 
  1. `Document.category_id` 没有 `ForeignKey` 约束（[backend/app/models/document.py:14](backend/app/models/document.py#L14)），数据库层面无保护。
  2. 删除分类后，文档保留无效的 `category_id`。
- **影响**:
  - 文档详情页/列表页在按分类查询时，这些文档永远不会被找到
  - 权限过滤基于分类ID，孤儿文档的权限行为不可预测
  - UI 层面无法展示这些文档的分类信息
- **建议修复**: 删除前将相关文档的 `category_id` 设为 NULL，或拒绝删除有关联文档的分类。

#### H-3. 文档列表与权限检查对 Guest 用户行为不一致

- **文件**: [backend/app/api/documents.py](backend/app/api/documents.py) vs [backend/app/permissions.py](backend/app/permissions.py)
- **问题**: 
  - `can_view_document()`: Guest 可以看到 `category_id = NULL` 的文档 → 返回 `True`
  - `list_documents()`: Guest 只能看到 `visible_departments IS NULL` 分类中的文档，如果存在公开分类，未分类文档被排除
- **影响**: Guest 无法通过列表页发现未分类文档，但可以通过直接访问 URL 查看。信息泄露路径不一致。

#### H-4. 文档列表对无分类用户的回退逻辑拒绝访问已授权文档

- **文件**: [backend/app/api/documents.py:109-111](backend/app/api/documents.py#L109-L111)
- **问题**: 当用户的 `visible_ids` 为空（非 super_admin 且无可见分类），列表仅返回 `category_id IS NULL` 的文档。但 `can_view_document()` 可能允许这些用户查看属于特定分类的文档（例如用户自己的上传）。列表端点与详情端点的权限模型不一致。
- **影响**: 用户无法浏览自己有权限查看的分类文档，只能通过搜索或直接链接访问。

---

### 🟡 Medium (8项)

#### M-1. 创建文档不验证 category_id 是否存在

- **文件**: [backend/app/api/documents.py:179-249](backend/app/api/documents.py#L179-L249)
- **问题**: `create_document` 直接使用传入的 `category_id`，不检查该分类是否存在。
- **影响**: 可以创建属于不存在分类的文档。

#### M-2. 创建文档不检查用户是否有权限上传到指定分类

- **文件**: [backend/app/api/documents.py:179-249](backend/app/api/documents.py#L179-L249)
- **问题**: 任何有上传权限的用户（editor/dept_admin/super_admin）可以将文档上传到任意分类，即使该分类不对其部门开放。
- **复现**: 器械注册部的 editor 上传文档到"临床评价部"专属分类。
- **影响**: 部门隔离被绕过。

#### M-3. 更新文档不验证新 category_id 是否存在

- **文件**: [backend/app/api/documents.py:252-276](backend/app/api/documents.py#L252-L276)
- **问题**: `update_document` 的 `DocumentUpdate` schema 包含 `category_id`，更新时不验证该分类是否存在。
- **影响**: 文档可以被移动到不存在的分类。

#### M-4. 文档查看次数 (view_count) 双重计数

- **文件**: [backend/app/api/documents.py:152](backend/app/api/documents.py#L152) + [backend/app/api/documents.py:384](backend/app/api/documents.py#L384)
- **问题**: `get_document` (详情接口) 和 `preview_document` (预览接口) 都会递增 `view_count`。前端 DocumentView 在加载文档时同时调用这两个接口：
  1. `GET /api/documents/{id}` → view_count++
  2. `GET /api/documents/{id}/preview?token=...` → view_count++
- **影响**: 每次页面访问 view_count 增加 2 而非 1，统计数据失真。

#### M-5. dept_admin 可以管理其他部门的用户（跨部门越权）

- **文件**: [backend/app/api/admin.py:54-88](backend/app/api/admin.py#L54-L88) (create) + [line 91-116](backend/app/api/admin.py#L91-L116) (update)
- **问题**: 
  - `create_user`: dept_admin 可以设置 `department` 为任意值，包括其他部门
  - `update_user`: 只检查原始 `user.department`，不检查更新的 `body.department` 是否在 dept_admin 管辖范围内
- **影响**: dept_admin 可以在其他部门创建/移动用户，破坏了部门隔离。

#### M-6. 预览端点先提交 view_count 再执行业务逻辑

- **文件**: [backend/app/api/documents.py:384-419](backend/app/api/documents.py#L384-L419)
- **问题**: `preview_document` 在权限检查通过后立即 `++view_count` 并 `commit()`。后续如果 Gotenberg 转换失败或文件读取失败导致返回错误，view_count 已经递增。
- **影响**: 失败的预览请求仍会计入 view_count。

#### M-7. 登录限流字典无限增长（内存泄漏）

- **文件**: [backend/app/api/auth.py:15-32](backend/app/api/auth.py#L15-L32)
- **问题**: `_login_attempts` 是模块级 dict，清理逻辑只在新的登录请求时触发。大量不同 IP 的尝试或长期运行后，字典会无限增长。
- **建议**: 使用 TTL 缓存（如 `cachetools.TTLCache`）或定期后台清理。

#### M-8. Guest 可以查看所有未分类文档

- **文件**: [backend/app/permissions.py:42-60](backend/app/permissions.py#L42-L60)
- **问题**: `can_view_document` 中，如果 `doc.category_id is None`，直接返回 `True`，无需任何权限检查。这意味着任何未分类的文档对所有 Guest 可见。
- **影响**: 如果管理员上传了敏感文档但忘记分类，该文档对未登录用户完全可见。

---

### 🟢 Low (5项)

#### L-1. 注册接口未验证 display_name

- **文件**: [backend/app/api/auth.py:56-84](backend/app/api/auth.py#L56-L84)
- **问题**: `display_name` 可以为空字符串，未验证长度或内容。
- **影响**: 可能出现空名称用户。

#### L-2. CORS 允许所有来源

- **文件**: [backend/app/main.py:23](backend/app/main.py#L23)
- **问题**: `allow_origins=["*"]` 且 `allow_credentials=False`。虽然后者限制了带凭据的请求，但在生产环境中更严格的来源限制是更好的实践。
- **影响**: 低风险（`allow_credentials=False` 已提供基本保护）。

#### L-3. CategoryView 搜索参数未传递给后端

- **文件**: [frontend/src/views/CategoryView.vue:138](frontend/src/views/CategoryView.vue#L138)
- **问题**: 前端设置了 `searchKeyword` 并通过 `queryParams.keyword` 传递，但后端 `list_documents` 接口不接受 `keyword` 参数（只有 `category_id`, `page`, `size`, `sort`, `order`）。搜索关键词在前端不会生效，文档列表不会被过滤。
- **影响**: 用户在分类页面的搜索框输入关键词无效果。

#### L-4. 数据库 session rollback 逻辑可能丢失变更

- **文件**: [backend/app/database.py:25-26](backend/app/database.py#L25-L26)
- **问题**: `get_db` 的 finally 块检查 `session.is_active and session.dirty`，如果未提交且有脏数据就 rollback。但如果某个端点调用了 `await db.flush()` 但忘记 `commit()`，数据会在不知情的情况下被回滚。
- **影响**: 潜在的数据丢失（依赖开发者正确使用）。

#### L-5. Meilisearch 索引异常被静默吞没

- **文件**: [backend/app/services/search_service.py:66-67](backend/app/services/search_service.py#L66-L67) 等多处
- **问题**: 索引/搜索异常只记录 warning 日志，不影响主流程。这是有意设计的 fire-and-forget 模式（"failure is logged but doesn't block"），但如果 Meilisearch 长期故障，搜索索引会完全过期而无人察觉。
- **建议**: 增加监控/告警机制。

---

## 四、安全审查专项

| 检查项 | 状态 | 说明 |
|--------|------|------|
| JWT 密钥硬编码 | ✅ 已修复 | 通过环境变量注入 |
| Open Redirect | ✅ 已修复 | 域名白名单 + 协议检查 |
| XSS (v-html) | ✅ 已修复 | SearchView highlight 先转义再插入 |
| 登录暴力破解 | ✅ 已防护 | 滑动窗口限流 (10次/5分钟) |
| SQL 注入 | ✅ 安全 | 使用 SQLAlchemy ORM 参数化查询 |
| Meilisearch 过滤器注入 | ✅ 已修复 | `_escape_meili_filter_value()` 转义单引号 |
| 权限提升 (dept_admin → super_admin) | 🔴 未修复 | 见 C-1, C-2 |
| 跨部门用户管理 | 🟡 未修复 | 见 M-5 |
| 密码强度验证 | ✅ 已实现 | 最少8位 + 至少1字母 + 至少1数字 |
| 生产环境错误信息泄露 | ✅ 已防护 | 全局异常处理区分 dev/prod |
| 硬编码演示账号 | ✅ 已移除 | LoginView 中已清理 |

---

## 五、前端审查

### 路由安全
- ✅ 路由守卫检查 `requiresAuth` 和 `roles`
- ✅ 登录后 redirect 参数做了路径安全检查 (`startsWith('/') && !startsWith('//')`)
- ✅ Guest 页面 (`/login`, `/register`) 已登录用户自动跳转

### 数据安全
- ✅ SearchView 的 `highlight()` 函数先 HTML 转义再插入 `<em>` 标签
- ✅ `isEmbeddable()` 检查 URL 协议白名单
- ✅ Token 存储在 localStorage，请求拦截器自动附加

### 问题
- 🟢 L-3: CategoryView 关键词搜索在前端设置了参数但后端不支持（见 Low 部分）

---

## 六、建议的修复优先级

### 立即修复（Critical + High）

1. **C-1/C-2**: `admin.py` — 添加角色层级校验：
   ```python
   ROLE_HIERARCHY = {"super_admin": 100, "dept_admin": 50, "editor": 30, "employee": 10, "guest": 0}
   # dept_admin 只能分配 role 层级 <= dept_admin 的角色
   ```

2. **H-1**: `documents.py:109-111` — 将 `Document.category_id.is_(None)` 改为 `False` (返回空结果)：
   ```python
   else:
       # User has no visible categories at all — return empty list
       conditions.append(False)  # or use a sentinel that evaluates to false
   ```
   更好的方案：使用 `sqlalchemy.false()` 或直接返回空列表。

3. **H-2**: `categories.py:114-133` — 删除分类前处理关联文档：
   ```python
   # Set documents' category_id to NULL before deleting the category
   docs = await db.execute(select(Document).where(Document.category_id == cat.id))
   for doc in docs.scalars().all():
       doc.category_id = None
   ```

4. **H-3/H-4**: 统一 `list_documents` 和 `can_view_document` 的权限模型。

### 近期修复（Medium）

5. **M-1/M-3**: 添加 category_id 存在性验证。
6. **M-2**: 创建文档时检查用户是否有权限上传到目标分类。
7. **M-4**: 移除 `preview_document` 中的 view_count 递增（`get_document` 已计数）。
8. **M-5**: 限制 dept_admin 只能管理本部门用户。
9. **M-7**: 使用 TTL 缓存替代普通 dict 做限流存储。
10. **M-8**: Guest 查看未分类文档需要明确的权限策略。

### 后续优化（Low）

11. **L-1**: 添加 display_name 长度/内容验证。
12. **L-3**: 后端添加 keyword 搜索参数支持，或前端改用 search API。

---

## 七、测试建议

### 建议添加的自动化测试

1. **单元测试** (`backend/tests/`):
   - `test_auth.py`: 密码哈希/验证, token 创建/解码, 密码强度验证
   - `test_permissions.py`: PermissionService 各角色/场景的权限矩阵
   - `test_admin.py`: 角色层级校验, 跨部门限制

2. **集成测试**:
   - `test_api_auth.py`: 登录/注册/限流端到端
   - `test_api_documents.py`: CRUD + 权限过滤
   - `test_api_admin.py`: 用户管理权限边界

3. **安全测试**:
   - dept_admin 权限提升测试
   - 跨部门数据访问测试
   - Guest 访问边界测试

---

## 八、总结

| 指标 | 数值 |
|------|------|
| 审查文件数 | 25+ |
| 发现问题总数 | 19 |
| 🔴 Critical | 2 |
| 🟠 High | 4 |
| 🟡 Medium | 8 |
| 🟢 Low | 5 |
| 已修复的历史问题 | 21 (见 DEVLOG 2026-07-13) |
| 整体代码质量 | 良好 |
| 安全防护水平 | 中等（关键权限漏洞需修复） |

**总体评价**: 项目代码结构清晰，历史安全问题已得到较好修复。当前最严重的问题是 `dept_admin` 角色的权限边界控制不足，存在明确的权限提升路径。建议优先修复 Critical 和 High 级别的问题后再上线生产环境。
