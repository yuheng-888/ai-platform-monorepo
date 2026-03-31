# Gemini Business CPAM Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 让主站注册出来的 Gemini Business 账号自动同步进 CPAM，并能通过 CPAM/New API 稳定绑定到指定 Gemini Business 账号发请求。

**Architecture:** 主站负责把 Gemini Business 账号上传成新的 `gemini-business` auth file；CLIProxyAPI 识别该 provider 并复用 OpenAI-compatible executor；主站嵌入式 Gemini runtime 支持通过受控请求头强制指定账号并隔离会话缓存。

**Tech Stack:** Python, FastAPI, SQLModel, requests, Go, Gin, CLIProxyAPI auth/model registry, pytest, go test

---

### Task 1: Main-site Gemini CPAM upload tests

**Files:**
- Modify: `apps/main-site/tests/test_gemini_platform_plugin.py`
- Modify: `apps/main-site/services/external_sync.py`
- Create: `apps/main-site/services/cliproxyapi_gemini_business_sync.py`

**Step 1: Write the failing test**

增加测试，断言：

- `platform == "gemini"` 时会调用 Gemini 专用同步逻辑。
- 上传到 CLIProxyAPI 的 JSON 包含 `type=gemini-business`
- JSON 包含 `email`、`gemini_account_id`、`base_url`、`api_key`
- JSON 包含 `header:X-Gemini-Account-ID`

**Step 2: Run test to verify it fails**

Run: `pytest apps/main-site/tests/test_gemini_platform_plugin.py -k cliproxyapi -v`
Expected: FAIL，提示 Gemini 分支未同步或上传 payload 不符合预期。

**Step 3: Write minimal implementation**

实现 `services/cliproxyapi_gemini_business_sync.py`，并在 `services/external_sync.py` 里增加 Gemini 分支，复用现有 CLIProxyAPI 管理接口上传 auth file。

**Step 4: Run test to verify it passes**

Run: `pytest apps/main-site/tests/test_gemini_platform_plugin.py -k cliproxyapi -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/main-site/services/external_sync.py apps/main-site/services/cliproxyapi_gemini_business_sync.py apps/main-site/tests/test_gemini_platform_plugin.py
git commit -m "feat: sync gemini business accounts to cliproxyapi"
```

### Task 2: Main-site forced account header tests

**Files:**
- Modify: `apps/main-site/tests/test_gemini_platform_plugin.py`
- Modify: `apps/main-site/embedded/gemini_business2api/main.py`

**Step 1: Write the failing test**

增加测试，断言：

- 请求头 `X-Gemini-Account-ID` 存在时，`chat_impl` 会调用 `multi_account_mgr.get_account(forced_id, ...)`
- 不会自动改为 `None`
- 当强制账号不可用时，抛出明确错误

**Step 2: Run test to verify it fails**

Run: `pytest apps/main-site/tests/test_gemini_platform_plugin.py -k forced_account -v`
Expected: FAIL，提示当前请求头未生效或仍走自动选账号。

**Step 3: Write minimal implementation**

在 `embedded/gemini_business2api/main.py` 中读取 `X-Gemini-Account-ID`，将其纳入账号选择分支，并在强制模式下禁用自动切换到其他账号。

**Step 4: Run test to verify it passes**

Run: `pytest apps/main-site/tests/test_gemini_platform_plugin.py -k forced_account -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/main-site/embedded/gemini_business2api/main.py apps/main-site/tests/test_gemini_platform_plugin.py
git commit -m "feat: support forced gemini business account routing"
```

### Task 3: Main-site session cache isolation tests

**Files:**
- Modify: `apps/main-site/tests/test_gemini_platform_plugin.py`
- Modify: `apps/main-site/embedded/gemini_business2api/main.py`

**Step 1: Write the failing test**

增加测试，断言同样的消息内容在不同 `X-Gemini-Account-ID` 下会生成不同缓存命中行为，不会复用到别的账号会话。

**Step 2: Run test to verify it fails**

Run: `pytest apps/main-site/tests/test_gemini_platform_plugin.py -k session_cache -v`
Expected: FAIL，提示缓存键没有区分强制账号。

**Step 3: Write minimal implementation**

调整会话键生成逻辑，把 `forced_account_id` 纳入 key 组成。

**Step 4: Run test to verify it passes**

Run: `pytest apps/main-site/tests/test_gemini_platform_plugin.py -k session_cache -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/main-site/embedded/gemini_business2api/main.py apps/main-site/tests/test_gemini_platform_plugin.py
git commit -m "fix: isolate gemini session cache by forced account"
```

### Task 4: CLIProxyAPI gemini-business provider tests

**Files:**
- Modify: `apps/cliproxyapi/internal/watcher/synthesizer/file_test.go`
- Modify: `apps/cliproxyapi/sdk/cliproxy/service_excluded_models_test.go`
- Create: `apps/cliproxyapi/internal/runtime/executor/openai_compat_executor_gemini_business_test.go`
- Modify: `apps/cliproxyapi/internal/watcher/synthesizer/file.go`
- Modify: `apps/cliproxyapi/sdk/cliproxy/service.go`

**Step 1: Write the failing test**

增加测试，断言：

- `type=gemini-business` auth file 会被识别为 `Provider=gemini-business`
- `gemini-business` 会注册 Gemini CLI 模型集合
- OpenAI-compatible executor 转发时会带上 `Authorization` 和 `X-Gemini-Account-ID`

**Step 2: Run test to verify it fails**

Run: `go test ./apps/cliproxyapi/internal/watcher/synthesizer ./apps/cliproxyapi/internal/runtime/executor ./apps/cliproxyapi/sdk/cliproxy`
Expected: FAIL，提示 provider 未识别、模型未注册或请求头未按预期透传。

**Step 3: Write minimal implementation**

在 CLIProxyAPI 中增加 `gemini-business` provider 的模型绑定，并确保走 OpenAI-compatible executor。

**Step 4: Run test to verify it passes**

Run: `go test ./apps/cliproxyapi/internal/watcher/synthesizer ./apps/cliproxyapi/internal/runtime/executor ./apps/cliproxyapi/sdk/cliproxy`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/cliproxyapi/internal/watcher/synthesizer/file.go apps/cliproxyapi/internal/watcher/synthesizer/file_test.go apps/cliproxyapi/internal/runtime/executor/openai_compat_executor_gemini_business_test.go apps/cliproxyapi/sdk/cliproxy/service.go apps/cliproxyapi/sdk/cliproxy/service_excluded_models_test.go
git commit -m "feat: add gemini business provider to cliproxyapi"
```

### Task 5: End-to-end verification

**Files:**
- Modify: `apps/main-site/tests/test_gemini_platform_plugin.py`
- Modify: `apps/cliproxyapi/internal/runtime/executor/openai_compat_executor_gemini_business_test.go`

**Step 1: Write the failing test**

补一个端到端近似测试，验证：

- 从主站上传出来的 auth JSON 可以被 CPAM 接收
- CPAM 生成的请求会把选中的 Gemini Business 账号转发到主站

**Step 2: Run test to verify it fails**

Run: `pytest apps/main-site/tests/test_gemini_platform_plugin.py -v && go test ./apps/cliproxyapi/internal/runtime/executor -run GeminiBusiness -v`
Expected: FAIL

**Step 3: Write minimal implementation**

补齐遗漏的字段、错误处理或模型映射，直到链路闭环。

**Step 4: Run test to verify it passes**

Run: `pytest apps/main-site/tests/test_gemini_platform_plugin.py -v && go test ./apps/cliproxyapi/internal/runtime/executor -run GeminiBusiness -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/main-site/tests/test_gemini_platform_plugin.py apps/cliproxyapi/internal/runtime/executor/openai_compat_executor_gemini_business_test.go
git commit -m "test: verify gemini business cpam integration"
```

### Task 6: Server rollout and smoke test

**Files:**
- Modify: `apps/main-site/services/external_sync.py`
- Modify: `apps/main-site/embedded/gemini_business2api/main.py`
- Modify: `apps/cliproxyapi/sdk/cliproxy/service.go`

**Step 1: Deploy changed files**

同步主站和 CLIProxyAPI 改动到服务器对应目录。

**Step 2: Restart services**

重启主站与 CLIProxyAPI，确认管理端和业务端都恢复。

**Step 3: Smoke test**

验证：

- 主站新增 Gemini 账号后，CPAM `/v0/management/auth-files` 出现 `gemini-business`
- CPAM `/v1/chat/completions` 或 New API 能使用该账号

**Step 4: Capture evidence**

记录成功账号、auth file 名称、接口返回和关键日志，便于后续追踪。
