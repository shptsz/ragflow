# kb_only Access Level Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让平台超管可为用户设置 `access_level=kb_only`，使其只能使用知识库模块（前后端同时拦截）。

**Architecture:** 在 `user.access_level` 字段上区分 `full` / `kb_only`。`/users/me` 与 admin 用户列表返回该字段；前端按字段过滤导航/路由/设置；Python 与 Go 在受限 API 路径上返回 403。Admin 通过 `PUT /api/v1/admin/users/<email>/access-level` 切换。

**Tech Stack:** Python/Peewee（API + admin:9381）、Go/Gorm（API:9384 + admin:9383）、React/TypeScript（web）

**Spec:** `docs/superpowers/specs/2026-07-10-kb-only-access-level-design.md`

---

## File Map

| 文件 | 职责 |
|------|------|
| `api/db/__init__.py` | `AccessLevel` 枚举 |
| `api/db/db_models.py` | `User.access_level` 字段 + `migrate_db` 加列 |
| `api/common/access_level.py` | 模块白名单 + `ensure_module_access` / 路径拦截 |
| `api/apps/__init__.py` 或 `api/apps/backward_compat.py` | 注册 before_request 拦截 |
| `api/apps/restful_apis/user_api.py` | 注册默认 `full`；禁止用户自改 `access_level` |
| `admin/server/services.py` | 列表返回字段 + `update_user_access_level` |
| `admin/server/routes.py` | `PUT .../access-level` |
| `internal/entity/user.go` | Go `AccessLevel` 字段 |
| `internal/service/user.go` | `GetUserProfile` 返回字段；注册默认值 |
| `internal/admin/service.go` + `handler.go` + `router.go` | Admin 列表/更新 |
| `internal/handler/auth.go` 或新 middleware | Go 路径级 403 |
| `web/src/constants/access-level.ts` | 前端枚举与路径白名单 |
| `web/src/hooks/use-access-level.ts` | `isKbOnly` helper |
| `web/src/interfaces/database/user-setting.ts` | `IUserInfo.access_level` |
| `web/src/layouts/components/global-navbar.tsx` | 过滤主导航 |
| `web/src/routes.tsx` | 路由守卫 / 默认设置页重定向 |
| `web/src/pages/home/*` | kb_only 跳转 datasets |
| `web/src/pages/user-setting/sidebar/index.tsx` | 仅保留 Profile |
| `web/src/pages/admin/users.tsx` + `admin-service.ts` + `api.ts` + types | Admin 列与 API |
| `web/src/locales/en.ts` + `zh.ts` | 文案 |

---

### Task 1: AccessLevel 常量 + DB 字段（Python）

**Files:**
- Modify: `api/db/__init__.py`
- Modify: `api/db/db_models.py`
- Create: `test/unit_test/api/test_access_level_enum.py`

- [ ] **Step 1: 写失败测试**

```python
# test/unit_test/api/test_access_level_enum.py
from api.db import AccessLevel


def test_access_level_values():
    assert AccessLevel.FULL == "full"
    assert AccessLevel.KB_ONLY == "kb_only"
    assert AccessLevel.FULL in AccessLevel
```

- [ ] **Step 2: 运行确认失败**

Run: `uv run pytest test/unit_test/api/test_access_level_enum.py -v`  
Expected: FAIL（`AccessLevel` 未定义）

- [ ] **Step 3: 实现枚举**

在 `api/db/__init__.py` 的 `UserTenantRole` 后添加：

```python
class AccessLevel(StrEnum):
    FULL = "full"
    KB_ONLY = "kb_only"
```

- [ ] **Step 4: User 模型加字段**

在 `api/db/db_models.py` 的 `User.is_superuser` 后添加：

```python
access_level = CharField(
    max_length=32,
    null=False,
    help_text="full|kb_only",
    default="full",
    index=True,
)
```

在 `migrate_db()` 末尾（`logging.disable` 恢复前）添加：

```python
alter_db_add_column(
    migrator,
    "user",
    "access_level",
    CharField(max_length=32, null=False, default="full", help_text="full|kb_only", index=True),
)
```

- [ ] **Step 5: 跑测试通过**

Run: `uv run pytest test/unit_test/api/test_access_level_enum.py -v`  
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add api/db/__init__.py api/db/db_models.py test/unit_test/api/test_access_level_enum.py
git commit -m "feat: add user.access_level field and AccessLevel enum"
```

---

### Task 2: 访问控制辅助（Python）

**Files:**
- Create: `api/common/access_level.py`
- Create: `test/unit_test/api/common/test_access_level.py`

- [ ] **Step 1: 写失败测试**

```python
# test/unit_test/api/common/test_access_level.py
from api.common.access_level import (
    normalize_access_level,
    is_path_allowed_for_kb_only,
    AccessDeniedError,
)


def test_normalize_defaults_to_full():
    assert normalize_access_level(None) == "full"
    assert normalize_access_level("") == "full"
    assert normalize_access_level("kb_only") == "kb_only"


def test_kb_only_allows_datasets_and_profile():
    assert is_path_allowed_for_kb_only("GET", "/api/v1/datasets") is True
    assert is_path_allowed_for_kb_only("GET", "/api/v1/datasets/abc/documents") is True
    assert is_path_allowed_for_kb_only("GET", "/api/v1/users/me") is True
    assert is_path_allowed_for_kb_only("PATCH", "/api/v1/users/me") is True


def test_kb_only_denies_chats_agents_files():
    assert is_path_allowed_for_kb_only("GET", "/api/v1/chats") is False
    assert is_path_allowed_for_kb_only("GET", "/api/v1/agents") is False
    assert is_path_allowed_for_kb_only("GET", "/api/v1/files") is False
    assert is_path_allowed_for_kb_only("GET", "/api/v1/searches") is False
    assert is_path_allowed_for_kb_only("GET", "/api/v1/memories") is False
    assert is_path_allowed_for_kb_only("GET", "/api/v1/tenants/x/users") is False
    assert is_path_allowed_for_kb_only("PATCH", "/api/v1/users/me/models") is False
```

- [ ] **Step 2: 运行确认失败**

Run: `uv run pytest test/unit_test/api/common/test_access_level.py -v`  
Expected: FAIL（模块不存在）

- [ ] **Step 3: 实现 `api/common/access_level.py`**

```python
from api.db import AccessLevel

class AccessDeniedError(Exception):
    """kb_only 用户访问了未授权模块。"""


def normalize_access_level(value: str | None) -> str:
    if value == AccessLevel.KB_ONLY:
        return AccessLevel.KB_ONLY
    return AccessLevel.FULL


# kb_only 允许的路径前缀（按最长匹配优先在实现里处理）
_KB_ONLY_ALLOW_PREFIXES = (
    "/api/v1/datasets",
    "/api/v1/chunks",  # 若实际挂在 datasets 下可删
    "/api/v1/auth",
    "/api/v1/system/version",
    "/api/v1/system/config",
    "/v1/user/login",
    "/v1/user/logout",
    "/v1/system/",
)

# 明确拒绝（即使落在宽前缀下）
_KB_ONLY_DENY_PREFIXES = (
    "/api/v1/chats",
    "/api/v1/chat/",
    "/api/v1/agents",
    "/api/v1/searches",
    "/api/v1/memories",
    "/api/v1/files",
    "/api/v1/tenants",
    "/api/v1/mcp",
    "/api/v1/connectors",
    "/api/v1/chat_channels",
    "/api/v1/users/me/models",
    "/api/v1/bots",
    "/api/v1/plugins",
    "/api/v1/langfuse",
    "/api/v1/providers",
    "/api/v1/models",
)


def is_path_allowed_for_kb_only(method: str, path: str) -> bool:
    path = path.rstrip("/") or "/"
    for deny in _KB_ONLY_DENY_PREFIXES:
        if path == deny.rstrip("/") or path.startswith(deny):
            return False
    # 用户资料：仅 GET/PATCH /api/v1/users/me（不含子路径）
    if path == "/api/v1/users/me":
        return method.upper() in {"GET", "PATCH", "HEAD", "OPTIONS"}
    for allow in _KB_ONLY_ALLOW_PREFIXES:
        if path == allow.rstrip("/") or path.startswith(allow):
            return True
    # 文档/切片等挂在 datasets 下的已覆盖；其余默认拒绝
    return False


def ensure_request_allowed(access_level: str | None, method: str, path: str) -> None:
    if normalize_access_level(access_level) != AccessLevel.KB_ONLY:
        return
    if not is_path_allowed_for_kb_only(method, path):
        raise AccessDeniedError(f"access_level=kb_only cannot access {method} {path}")
```

实现时对照真实路由前缀微调白名单（`document_api` / `chunk_api` / `file2document_api` / `task_api` 若独立前缀，加入 allow）。原则：**知识库域放行，其余拒绝**。

- [ ] **Step 4: 跑测试通过并按真实路由修正白名单**

Run: `uv run pytest test/unit_test/api/common/test_access_level.py -v`  
Expected: PASS

用 `rg "manager.route" api/apps/restful_apis/` 核对前缀后更新常量表与测试。

- [ ] **Step 5: Commit**

```bash
git add api/common/access_level.py test/unit_test/api/common/test_access_level.py
git commit -m "feat: add kb_only path allowlist helpers"
```

---

### Task 3: Python 请求拦截 + 注册默认值 + 禁止自改

**Files:**
- Modify: `api/apps/__init__.py`（或应用工厂里已有 before_request 处）
- Modify: `api/apps/restful_apis/user_api.py`
- Modify: `api/db/joint_services/user_account_service.py`（若注册走这里）
- Modify: `api/db/init_data.py`

- [ ] **Step 1: 注册用户写入 `access_level=full`**

在 `user_api.py` 创建用户的 `user_dict` / OAuth 注册 dict 中增加：

```python
"access_level": AccessLevel.FULL,
```

`init_superuser` 同样写入 `AccessLevel.FULL`。  
`PATCH /users/me` 的跳过字段列表加入 `"access_level"`，防止用户自改。

- [ ] **Step 2: 挂 before_request**

在 Quart app 上（`api/apps/__init__.py` 合适位置）注册：

```python
@app.before_request
async def _enforce_access_level():
    # 未登录放行（由 login_required 处理）
    user = getattr(g, "user", None) or current_user
    if user is None or not getattr(user, "is_authenticated", False):
        return None
    try:
        from api.common.access_level import ensure_request_allowed, AccessDeniedError
        ensure_request_allowed(
            getattr(user, "access_level", None),
            request.method,
            request.path,
        )
    except AccessDeniedError as e:
        return get_json_result(
            data=False,
            message=str(e),
            code=RetCode.AUTHENTICATION_ERROR,  # 或专用 403 码，与项目惯例一致
        )
```

注意：`current_user` 在 before_request 时可能尚未解析；若如此，改为在 `login_required` 装饰器通过鉴权后调用 `ensure_request_allowed`（改 `login_required` 包装函数末尾）。**优先改 `login_required`，更可靠。**

- [ ] **Step 3: 手动/单测验证**

对 `login_required` 路径写一个轻量单测（mock user `access_level=kb_only`，请求 `/api/v1/chats` 期望拒绝）。

- [ ] **Step 4: Commit**

```bash
git add api/apps/__init__.py api/apps/restful_apis/user_api.py api/db/init_data.py api/db/joint_services/user_account_service.py
git commit -m "feat: enforce kb_only access on Python API requests"
```

---

### Task 4: Python Admin 更新 access_level

**Files:**
- Modify: `admin/server/services.py`
- Modify: `admin/server/routes.py`
- Create: `test/unit_test/admin/test_access_level_update.py`（可纯测 UserMgr 方法，mock UserService）

- [ ] **Step 1: `UserMgr.get_all_users` / `get_user_details` 返回 `access_level`**

```python
"access_level": getattr(user, "access_level", None) or "full",
```

- [ ] **Step 2: 新增方法**

```python
@staticmethod
def update_user_access_level(username: str, access_level: str) -> str:
    from api.db import AccessLevel
    if access_level not in (AccessLevel.FULL, AccessLevel.KB_ONLY):
        raise AdminException(f"Invalid access_level: {access_level}", 400)
    user_list = UserService.query_user_by_email(username)
    if not user_list:
        raise UserNotFoundError(username)
    if len(user_list) > 1:
        raise AdminException(f"Exist more than 1 user: {username}!")
    usr = user_list[0]
    UserService.update_user(usr.id, {"access_level": access_level})
    return f"access_level updated to {access_level}"
```

- [ ] **Step 3: 路由**

```python
@admin_bp.route("/users/<username>/access-level", methods=["PUT"])
@login_required
@check_admin_auth
def alter_user_access_level(username):
    data = request.get_json() or {}
    access_level = data.get("access_level")
    if not access_level:
        return error_response("access_level is required", 400)
    msg = UserMgr.update_user_access_level(username, access_level)
    return success_response(None, msg)
```

- [ ] **Step 4: Commit**

```bash
git add admin/server/services.py admin/server/routes.py
git commit -m "feat(admin): allow updating user access_level"
```

---

### Task 5: Go 实体 + Profile + Admin + 中间件

**Files:**
- Modify: `internal/entity/user.go`
- Modify: `internal/service/user.go`
- Modify: `internal/admin/service.go`
- Modify: `internal/admin/handler.go`
- Modify: `internal/admin/router.go`
- Create: `internal/common/access_level.go`
- Modify: `internal/handler/auth.go`（或 router 注册中间件）
- Test: `internal/common/access_level_test.go`

- [ ] **Step 1: 实体字段**

```go
AccessLevel string `gorm:"column:access_level;size:32;not null;default:full;index" json:"access_level"`
```

- [ ] **Step 2: `GetUserProfile` 返回**

```go
accessLevel := "full"
if user.AccessLevel != "" {
    accessLevel = user.AccessLevel
}
// map 中加入 "access_level": accessLevel
```

注册新用户处默认 `"full"`。

- [ ] **Step 3: Admin ListUsers / GetUserDetails 带上字段；新增 UpdateUserAccessLevel**

Router:

```go
protected.PUT("/users/:username/access-level", r.handler.UpdateUserAccessLevel)
```

Handler 读 JSON `{"access_level":"kb_only"}`，校验后更新。

- [ ] **Step 4: 路径白名单（与 Python 对齐）+ Auth 后拦截**

在 `AuthMiddleware` 成功设置 user 后：

```go
if !accesslevel.IsAllowed(user.AccessLevel, c.Request.Method, c.Request.URL.Path) {
    common.ResponseWithCodeData(c, common.CodeForbidden /*或现有鉴权码*/, nil, "access denied for kb_only user")
    c.Abort()
    return
}
```

- [ ] **Step 5: Go 单测**

```bash
bash build.sh --test ./internal/common/...
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add internal/entity/user.go internal/service/user.go internal/admin/ internal/common/access_level.go internal/common/access_level_test.go internal/handler/auth.go
git commit -m "feat: enforce kb_only access_level in Go API and admin"
```

---

### Task 6: 前端常量、类型、Hook

**Files:**
- Create: `web/src/constants/access-level.ts`
- Create: `web/src/hooks/use-access-level.ts`
- Modify: `web/src/interfaces/database/user-setting.ts`
- Modify: `web/src/services/admin.service.d.ts`

- [ ] **Step 1: 常量**

```ts
// web/src/constants/access-level.ts
export enum AccessLevel {
  Full = 'full',
  KbOnly = 'kb_only',
}

export const KB_ONLY_ALLOWED_NAV = ['/datasets'] as const;

export const KB_ONLY_ALLOWED_SETTING_PATHS = [
  '/user-setting/profile',
] as const;
```

- [ ] **Step 2: Hook**

```ts
// web/src/hooks/use-access-level.ts
import { AccessLevel } from '@/constants/access-level';
import { useFetchUserInfo } from '@/hooks/use-user-setting-request';

export function useAccessLevel() {
  const { data: userInfo } = useFetchUserInfo();
  const accessLevel =
    userInfo?.access_level === AccessLevel.KbOnly
      ? AccessLevel.KbOnly
      : AccessLevel.Full;
  return {
    accessLevel,
    isKbOnly: accessLevel === AccessLevel.KbOnly,
    userInfo,
  };
}
```

- [ ] **Step 3: `IUserInfo` / Admin types 增加 `access_level?: string`**

- [ ] **Step 4: Commit**

```bash
git add web/src/constants/access-level.ts web/src/hooks/use-access-level.ts web/src/interfaces/database/user-setting.ts web/src/services/admin.service.d.ts
git commit -m "feat(web): add access_level types and hook"
```

---

### Task 7: 前端导航、路由、首页、设置侧边栏

**Files:**
- Modify: `web/src/layouts/components/global-navbar.tsx`
- Modify: `web/src/routes.tsx`
- Modify: `web/src/pages/home/index.tsx`（及/或 `applications.tsx`）
- Modify: `web/src/pages/user-setting/sidebar/index.tsx`
- Modify: `web/src/pages/user-setting/index.tsx`（若有默认出口）

- [ ] **Step 1: Navbar 过滤**

```tsx
const { isKbOnly } = useAccessLevel();
const visibleItems = isKbOnly
  ? menuItems.filter((item) => item.path === Routes.Datasets)
  : menuItems;
```

桌面端与移动端都改用 `visibleItems`。

- [ ] **Step 2: 路由守卫**

在 `RootLayout` children 或单独 wrapper：

- `kb_only` 访问 `/`、`/chats`、`/chat/*`、`/searches`、`/search/*`、`/agents`、`/agent/*`、`/memories`、`/memory/*`、`/files` → `<Navigate to="/datasets" replace />`
- 用户设置：默认子路由目前是 DataSource；改为：
  - `full`：保持现有默认
  - `kb_only`：默认 `/user-setting/profile`，并拦截 model/team/api/mcp/data-source/chat-channel → profile

实现可用小组件：

```tsx
function RequireFullAccess({ children }: { children: React.ReactNode }) {
  const { isKbOnly } = useAccessLevel();
  if (isKbOnly) return <Navigate to={Routes.Datasets} replace />;
  return <>{children}</>;
}
```

包在非知识库路由的 `element`/`Component` 外层（或 loader）。

- [ ] **Step 3: 设置侧边栏**

```tsx
const { isKbOnly } = useAccessLevel();
const items = menuItems(t).filter((item) =>
  isKbOnly ? item.key === Routes.Profile || item.key.endsWith('/profile') : true,
);
```

注意：密码改密在 Profile 页内，无需单独菜单项。

- [ ] **Step 4: 本地验证**

`cd web && npm run type-check`（或项目等价命令）

- [ ] **Step 5: Commit**

```bash
git add web/src/layouts/components/global-navbar.tsx web/src/routes.tsx web/src/pages/home web/src/pages/user-setting
git commit -m "feat(web): hide non-dataset modules for kb_only users"
```

---

### Task 8: Admin 前端列 + API 客户端 + i18n

**Files:**
- Modify: `web/src/utils/api.ts`
- Modify: `web/src/services/admin-service.ts`
- Modify: `web/src/pages/admin/users.tsx`
- Modify: `web/src/locales/en.ts`
- Modify: `web/src/locales/zh.ts`

- [ ] **Step 1: API**

```ts
// api.ts
adminUpdateUserAccessLevel: (username: string) =>
  `${restAPIv1}/admin/users/${username}/access-level`,
```

```ts
// admin-service.ts
export const updateUserAccessLevel = (
  email: string,
  accessLevel: 'full' | 'kb_only',
) =>
  request.put(api.adminUpdateUserAccessLevel(email), {
    access_level: accessLevel,
  });
```

- [ ] **Step 2: users.tsx 增加列**（仿 `is_superuser` Select）

```tsx
columnHelper.accessor('access_level', {
  header: t('admin.accessLevel'),
  cell: ({ cell, row }) => (
    <Select
      value={cell.getValue() === 'kb_only' ? 'kb_only' : 'full'}
      onValueChange={(value) => {
        updateAccessLevelMutation.mutate({
          email: row.original.email,
          accessLevel: value as 'full' | 'kb_only',
        });
      }}
    >
      <SelectTrigger><SelectValue /></SelectTrigger>
      <SelectContent>
        <SelectItem value="full">{t('admin.accessLevelFull')}</SelectItem>
        <SelectItem value="kb_only">{t('admin.accessLevelKbOnly')}</SelectItem>
      </SelectContent>
    </Select>
  ),
}),
```

`ListUsersItem` 增加 `access_level?: string`。

- [ ] **Step 3: i18n（仅 en + zh）**

```ts
// en.ts — Sentence case
accessLevel: 'Access level',
accessLevelFull: 'Full access',
accessLevelKbOnly: 'Knowledge base only',

// zh.ts
accessLevel: '访问级别',
accessLevelFull: '完整功能',
accessLevelKbOnly: '仅知识库',
```

- [ ] **Step 4: Commit**

```bash
git add web/src/utils/api.ts web/src/services/admin-service.ts web/src/pages/admin/users.tsx web/src/locales/en.ts web/src/locales/zh.ts
git commit -m "feat(admin-ui): manage user access_level"
```

---

### Task 9: 端到端核对与推送准备

- [ ] **Step 1: 核对清单**

1. DB 迁移后旧用户 `access_level` 默认为 `full`
2. `/users/me` 含 `access_level`
3. Admin 可改为 `kb_only`，刷新后导航仅知识库
4. 直访 `/chats` 跳到 `/datasets`
5. `GET /api/v1/chats` 返回错误（403/鉴权错误）
6. 知识库 CRUD 正常；Profile 改密正常
7. 改回 `full` 后功能恢复

- [ ] **Step 2: 跑相关测试**

```bash
uv run pytest test/unit_test/api/test_access_level_enum.py test/unit_test/api/common/test_access_level.py -v
bash build.sh --test ./internal/common/...
cd web && npm run type-check
```

- [ ] **Step 3: 若有遗漏白名单，修完再提交**

```bash
git commit -m "fix: align kb_only allowlist with real API routes"
```

- [ ] **Step 4: 推送到 `dev`（仅当用户明确要求时）**

```bash
git push -u origin HEAD
```

---

## Spec Coverage Self-Review

| Spec 要求 | Task |
|-----------|------|
| `access_level` 字段 + 默认 `full` | Task 1, 3, 5 |
| `/users/me` 返回 | Task 3（to_safe_dict 自动带字段）, Task 5 |
| Admin 可改 | Task 4, 5, 8 |
| 导航仅知识库 | Task 7 |
| 路由重定向 | Task 7 |
| 设置仅资料/密码（Profile 含改密） | Task 7 |
| API 403 | Task 2, 3, 5 |
| 不改团队角色 / 企业 RBAC | 未触及 |
| 知识库子功能可用 | 白名单放行 datasets 域 |

## Placeholder Scan

无 TBD/TODO 占位；白名单需在 Task 2/5 对照真实路由微调（已写明核对命令）。
