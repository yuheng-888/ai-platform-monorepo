# Gemini Business CPAM Integration Design

## Goal

把主站 Gemini Business 注册、存储、分发能力统一收敛到 CPAM，不再要求用户在主站和 Gemini 专页之间理解两套配置和两套凭证语义。

## Context

当前链路里，Gemini Business 注册成功后会落到主站账号表，但不会自动同步到 CPAM。与此同时，CLIProxyAPI 现有的 `gemini` / `gemini-cli` 认证模型是 OAuth + project 语义，和 Gemini Business 的 Web Session 账号并不等价。继续把两者混用，会让 UI、配置、上传语义和故障排查长期混乱。

## Requirements

- Gemini Business 注册成功后必须自动进入 CPAM。
- CPAM 中的凭证必须能被 New API / OpenAI-compatible 路由直接分发。
- 不再把 Gemini Business 伪装成 Google OAuth / Project 型凭证。
- 复用主站已经可用的 Gemini Business 运行时，避免在 CLIProxyAPI 内重复实现 Google Web 执行器。
- 单个 CPAM auth 必须稳定绑定到一个 Gemini Business 账号，不能在转发层混号。

## Approaches Considered

### Option A: 强制转换为现有 `gemini-cli` 凭证

优点：
- 表面上改动点少。

缺点：
- 语义错误，Gemini Business session 不是 OAuth project credential。
- 后续刷新、禁用、模型路由、问题定位都会继续混乱。

结论：
- 放弃。

### Option B: 在 CLIProxyAPI 内实现原生 Gemini Business 执行器

优点：
- 长期最纯粹。

缺点：
- 需要在 Go 侧完整复刻主站现有会话选择、冷却、重试、账户存储逻辑。
- 当前目标是先统一管理中心，这条路成本高、恢复慢。

结论：
- 作为远期优化，不作为这次交付路径。

### Option C: 新增 `gemini-business` provider，CPAM 转发到主站嵌入式 Gemini runtime

优点：
- 语义清晰，`gemini-business` 就是业务真实凭证类型。
- 主站 runtime 已经打通会话、账号池、图片/视频、冷却、任务历史。
- CLIProxyAPI 只负责统一凭证管理和分发，不重复造轮子。

缺点：
- 需要补一条“强制账号”请求头链路。
- 需要在 CPAM 新增 provider/model 映射。

结论：
- 采用此方案。

## Final Design

### 1. 主站注册成功后上传 `gemini-business` auth 到 CPAM

主站 `services/external_sync.py` 增加 Gemini 分支。对于 Gemini Business 账号，构造一个 auth JSON 上传到 CLIProxyAPI 管理接口 `/v0/management/auth-files`。

建议 auth JSON 结构：

```json
{
  "type": "gemini-business",
  "email": "user@example.com",
  "gemini_account_id": "10724",
  "base_url": "http://main-site-host:39001/gemini/v1",
  "api_key": "main-site-gemini-admin-key",
  "header:X-Gemini-Account-ID": "10724",
  "upstream_path": "/chat/completions",
  "mail_address": "user@example.com",
  "csesidx": "801018216",
  "config_id": "...",
  "expires_at": "...",
  "secure_c_ses": "...",
  "host_c_oses": "..."
}
```

其中真正给 CPAM 执行器使用的是：

- `type`
- `email`
- `base_url`
- `api_key`
- `header:X-Gemini-Account-ID`

其余字段主要用于管理页展示、排障和后续扩展。

### 2. 主站嵌入式 Gemini runtime 支持“强制账号”

`/gemini/v1/chat/completions` 在 API key 校验通过后，读取请求头 `X-Gemini-Account-ID`。

行为规则：

- 无该请求头：保持现有逻辑，从缓存会话或账号池自动选择。
- 有该请求头：优先使用指定账号。
- 如果指定账号不存在、已禁用、当前配额不可用，返回明确错误，不自动切走别的账号。
- 会话缓存键必须纳入 `forced_account_id`，避免不同 CPAM auth 共享同一会话。

### 3. CLIProxyAPI 新增 `gemini-business` provider

CLIProxyAPI 侧不新写一套 Google Web 执行器，而是把 `gemini-business` 当作一个 OpenAI-compatible provider：

- executor: 复用 `OpenAICompatExecutor`
- credential source: auth file
- authentication: `Authorization: Bearer <api_key>`
- routing: `base_url + /chat/completions`
- per-auth binding: 通过 `header:X-Gemini-Account-ID`

### 4. 模型集合复用 Gemini CLI

`gemini-business` 复用 `gemini-cli` 的模型定义，保证：

- 管理端能看到模型
- New API 能正常选模型
- 调度层不需要额外维护一套近似重复的 Gemini 模型表

这只复用“模型集合”，不复用凭证语义。

## Data Flow

1. 用户在主站发起 Gemini 注册任务。
2. 主站注册成功并保存账号到主站账号表。
3. 主站自动调用外部同步，把该账号上传为 CPAM auth file。
4. CLIProxyAPI watcher 识别 `type=gemini-business`，注册为新 provider。
5. CPAM / New API 选中该 auth 发起请求。
6. CLIProxyAPI 用 OpenAI-compatible executor 转发到主站 `/gemini/v1/chat/completions`。
7. 主站 runtime 通过 `X-Gemini-Account-ID` 绑定到指定 Gemini Business 账号执行。

## Error Handling

- 主站上传 CPAM 失败：
  - 注册任务本身仍记成功。
  - 任务日志中明确记录 `CLIProxyAPI` 上传失败原因。
- CPAM 使用了无效 `gemini_account_id`：
  - 主站返回 404/409 类明确错误，不偷偷切到其他账号。
- 指定账号临时不可用：
  - 返回可读错误，交给 CPAM 现有调度与重试层处理。

## Security

- 强制账号头只在 API key 校验通过后生效。
- 不新增匿名控制入口。
- CPAM 中保存的 `api_key` 是主站嵌入 Gemini runtime 的 admin key，属于已有受控能力延伸。

## Testing Strategy

### Main-site

- 测试 Gemini 注册成功后调用 CPAM 上传，并写出正确 auth JSON。
- 测试 `X-Gemini-Account-ID` 能强制绑定账号。
- 测试带强制账号时，会话缓存键隔离。
- 测试指定账号不可用时不自动回退到其他账号。

### CLIProxyAPI

- 测试 `gemini-business` auth file 能被识别并注册模型。
- 测试 `gemini-business` 复用 Gemini CLI 模型集合。
- 测试 OpenAI-compatible executor 会携带 `Authorization` 和 `X-Gemini-Account-ID` 转发。

## Rollout

1. 本地先补测试并打通代码。
2. 本地验证主站与 CLIProxyAPI 相关测试。
3. 同步到服务器。
4. 重启主站和 CLIProxyAPI。
5. 用一条 Gemini 注册任务验证：
   - 主站账号保存成功
   - CPAM auth file 出现
   - 通过 CPAM 的 New API 能打到对应 Gemini Business 账号
