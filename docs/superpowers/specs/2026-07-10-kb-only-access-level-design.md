# 设计：用户访问级别 `access_level`（仅知识库角色）

日期：2026-07-10  
状态：已确认  
分支目标：`dev`

## 背景

RAGFlow 当前所有已登录用户（含普通注册用户）都能看到主应用全部模块。平台级 `is_superuser` 只控制 `/admin` 管理后台；团队级 `owner` / `normal` 只控制团队协作与共享资源可见性，**都不控制主模块可见性**。

需求：由平台超级管理员在 `/admin` 为用户指定一种受限角色，使其只能使用知识库模块；前后端同时拦截。

## 目标

- 新增用户访问级别字段 `access_level`：`full` | `kb_only`
- 超管可在管理后台切换用户级别
- `kb_only` 用户：
  - 主导航仅显示「知识库」
  - 首页与被禁路由重定向到 `/datasets`
  - 用户设置仅保留个人资料与密码
  - 非知识库相关 API 返回 403
- 现有用户与新注册用户默认 `full`，行为不变

## 非目标

- 不改造团队角色（`owner` / `admin` / `normal` / `invite`）
- 不实现完整企业版 RBAC（`admin/roles` stub 保持不动）
- 不限制知识库内部子功能（文件、检索测试、配置、知识图谱等仍可用）
- 不改变 `is_superuser` 语义（仍只控制管理后台）

## 数据模型

### 字段

在 `user` 表新增：

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `access_level` | `VARCHAR(32)` | `'full'` | 用户主应用访问级别 |

合法取值：

- `full`：完整功能
- `kb_only`：仅知识库 + 个人资料/密码

### 兼容

- 已有用户：迁移/默认值设为 `full`
- 新注册用户：写入 `full`
- 读取时若字段缺失或为空，按 `full` 处理

### 常量（建议）

```python
class AccessLevel(StrEnum):
    FULL = "full"
    KB_ONLY = "kb_only"
```

前端对应：

```ts
export enum AccessLevel {
  Full = 'full',
  KbOnly = 'kb_only',
}
```

## 后端设计

### 1. 用户信息返回

`GET /users/me`（及等价用户信息接口）增加字段：

```json
{
  "access_level": "full"
}
```

### 2. 超管更新接口

在现有 admin 用户管理能力上增加更新 `access_level` 的接口（Python admin 与/或 Go admin，以当前 `/admin` 实际调用链为准）。

约束：

- 仅 `is_superuser` 可调用
- 不允许把最后一个超级管理员改成无法管理平台的状态（本设计不通过 `access_level` 剥夺超管后台权限；`is_superuser` 与 `access_level` 正交）
- 非法取值返回参数错误

### 3. 模块访问鉴权

新增统一校验（Python + Go 两侧按实际路由归属落地）：

```text
if user.access_level == kb_only and module not in allowed:
    return 403
```

#### `kb_only` 允许的模块/能力

- 认证：登录、登出、刷新会话
- 用户：读取自身信息、更新个人资料、修改密码
- 知识库：知识库 CRUD、文档上传/解析/列表、切片、检索测试、知识库配置、知识图谱相关读写（知识库域内）
- 为支撑知识库页面所必需的只读辅助接口（如系统版本、必要的模型列表只读——若知识库配置页强依赖；若可避免则不开放写配置）

#### `kb_only` 拒绝的模块/能力

- 聊天（dialog / conversation）
- 搜索应用（search apps）
- 智能体（agent / canvas）
- 记忆（memory）
- 文件管理（file manager，独立于知识库文档）
- 团队管理（邀请、成员管理）
- 模型提供商配置（增删改密钥/实例）
- MCP
- API Token
- 数据源 / Chat Channel
- 管理后台（仍由 `is_superuser` 控制；`kb_only` 且非超管不可进）

实现方式建议：

1. 定义模块常量与路由/蓝图映射表
2. 在登录后中间件或各蓝图入口调用 `require_access(module)`
3. 优先集中拦截，避免每个 handler 复制粘贴

### 4. 注册与初始化

- 公开注册：`access_level = full`
- `init_superuser`：`access_level = full`（超管默认全功能）

## 前端设计

### 1. 类型与数据源

- `IUserInfo` 增加 `access_level`
- 从 `useFetchUserInfo()` 读取
- 提供 `useAccessLevel()` / `isKbOnlyUser` 辅助

### 2. 主导航

文件：`web/src/layouts/components/global-navbar.tsx`

- `kb_only` 仅保留 `Routes.Datasets`
- 桌面端与移动端共用同一过滤逻辑

### 3. 路由守卫

文件：`web/src/routes.tsx` 与/或 `root-layout`

- `kb_only` 访问以下路径时重定向到 `/datasets`：
  - `/`（首页）
  - `/chats`, `/chat/*`
  - `/searches`, `/search/*`
  - `/agents`, `/agent/*`
  - `/memories`, `/memory/*`
  - `/files`
  - 用户设置中除 profile/password 外的子路由

### 4. 首页

- `kb_only` 不渲染 Applications 等非知识库入口；直接进入 `/datasets`

### 5. 用户设置侧边栏

文件：`web/src/pages/user-setting/sidebar/index.tsx`

`kb_only` 仅保留：

- 个人资料（Profile）
- 密码（Password）

隐藏：数据源、Chat Channel、模型、MCP、团队、API 等。

### 6. Admin 用户管理

文件：`web/src/pages/admin/users.tsx`（及相关表单）

- 用户列表增加 `access_level` 列
- 超管可通过下拉切换 `full` / `kb_only`
- 与现有 `is_superuser` 列并存，互不替代

## 权限矩阵（摘要）

| 能力 | `full` | `kb_only` | 备注 |
|------|--------|-----------|------|
| 知识库模块 | ✓ | ✓ | |
| 聊天/搜索/智能体/记忆/文件 | ✓ | ✗ | 前端隐藏 + API 403 |
| 设置：资料/密码 | ✓ | ✓ | |
| 设置：模型/团队/API/MCP/数据源 | ✓ | ✗ | |
| `/admin` | 仅超管 | 仅超管 | 由 `is_superuser` 决定 |

## 测试计划

1. 默认用户（`full`）回归：导航、设置、各模块可用
2. 将用户改为 `kb_only`：
   - 导航后主导航仅知识库
   - 直访 `/chats` 等跳到 `/datasets`
   - 设置页仅资料/密码
   - 调用聊天/智能体等 API 返回 403
   - 知识库增删改查与文档操作正常
3. 超管可在 `/admin` 改回 `full`，功能恢复
4. 新注册用户默认为 `full`

## 风险与注意

- 仅藏导航不够，必须后端拦截
- 知识库配置页可能依赖模型列表等只读接口；实现时按页面实际请求白名单放行，避免误伤
- Go / Python 双栈都有用户与业务 API，需确认当前部署实际走哪条链路，避免漏拦
- DB 迁移需兼容已有库（默认 `full`）

## 实施顺序（概要）

1. DB 模型 + 常量 + `/users/me` 返回字段
2. Admin 更新 `access_level` API + 前端管理列
3. 前端导航/路由/设置过滤
4. 后端模块级 403 拦截
5. 回归测试并推送到 `dev`
