# ChatGPT Restock Source And Target Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make ChatGPT auto-restock use CLIProxyAPI pool inventory as the source of truth and keep replenishing toward the configured target after the threshold has been crossed.

**Architecture:** Move inventory calculation in `services/auto_restock.py` from the local `AccountModel` table to the existing CLIProxyAPI pool summary service so the dashboard and trigger logic read the same number. Add a small persisted "restock latch" state so once stock drops below the threshold, the scheduler continues launching replenishment batches until the target is reached, even if stock rebounds above the threshold between batches.

**Tech Stack:** FastAPI, SQLModel, SQLite config store, unittest, Ant Design frontend

---

### Task 1: Define the new restock behavior with tests

**Files:**
- Create: `apps/main-site/tests/test_auto_restock.py`
- Modify: `apps/main-site/services/auto_restock.py`

**Step 1: Write the failing tests**

```python
@patch("services.auto_restock.get_cliproxyapi_pool_summary")
def test_restock_summary_uses_cliproxyapi_enabled_inventory(mock_pool_summary):
    mock_pool_summary.return_value = {"enabled": 5756, "last_error": ""}
    summary = auto_restock.get_chatgpt_restock_summary()
    assert summary["available"] == 5756
```

```python
@patch("services.auto_restock.start_register_task")
@patch("services.auto_restock.has_active_auto_restock_task")
@patch("services.auto_restock.get_cliproxyapi_pool_summary")
def test_restock_continues_toward_target_after_latch_is_enabled(...):
    # available is above threshold but below target
    # latch is already enabled from a previous low-stock cycle
    # scheduler should keep starting another batch
```

```python
@patch("services.auto_restock.get_cliproxyapi_pool_summary")
def test_restock_clears_latch_when_target_is_reached(...):
    # available >= target should clear latch and stop scheduling
```

**Step 2: Run tests to verify they fail**

Run: `./.venv-test/bin/python -m unittest tests.test_auto_restock -v`

Expected: failures showing that summary still uses local DB inventory and the scheduler still stops once stock rises above threshold.

**Step 3: Write minimal implementation**

- Add a helper to read CLIProxyAPI pool summary and return the `enabled` count when available.
- Add persisted latch helpers such as `_get_restock_latch(platform)` and `_set_restock_latch(platform, value)` backed by `config_store`.
- Update `check_and_trigger_chatgpt_auto_restock()` to:
  - refuse to trigger when pool stats are unavailable
  - set the latch when `available < threshold`
  - keep triggering while the latch is set and `available < target`
  - clear the latch when `available >= target`
- Keep `batch_size` as the per-round cap but compute the round size from `target - available`.

**Step 4: Run tests to verify they pass**

Run: `./.venv-test/bin/python -m unittest tests.test_auto_restock -v`

Expected: PASS

**Step 5: Commit**

```bash
git add apps/main-site/tests/test_auto_restock.py apps/main-site/services/auto_restock.py
git commit -m "fix: align restock inventory with cliproxyapi pool"
```

### Task 2: Align the dashboard/API summary with the new source of truth

**Files:**
- Modify: `apps/main-site/services/auto_restock.py`
- Modify: `apps/main-site/api/accounts.py`
- Modify: `apps/main-site/frontend/src/pages/Dashboard.tsx`

**Step 1: Write the failing test**

```python
def test_restock_summary_reports_pool_errors_without_zeroing_inventory():
    ...
```

**Step 2: Run test to verify it fails**

Run: `./.venv-test/bin/python -m unittest tests.test_auto_restock -v`

Expected: FAIL because the current summary either hides the pool source or cannot explain why restock is paused.

**Step 3: Write minimal implementation**

- Include `source`, `latched`, and `last_error` in the restock summary payload.
- Keep the dashboard card simple but make sure the "可用库存" value and auto-restock status are based on the same payload.
- If the pool cannot be queried, report `last_error` and do not trigger replenishment.

**Step 4: Run tests and build to verify they pass**

Run: `./.venv-test/bin/python -m unittest tests.test_auto_restock tests.test_gemini_session_auth tests.test_resin_slot_pool tests.test_shared_mailbox_providers tests.test_gemini_shared_config -v`

Run: `npm run build`

Expected: all tests pass, frontend build succeeds.

**Step 5: Commit**

```bash
git add apps/main-site/services/auto_restock.py apps/main-site/api/accounts.py apps/main-site/frontend/src/pages/Dashboard.tsx apps/main-site/tests/test_auto_restock.py
git commit -m "fix: unify restock dashboard inventory source"
```

### Task 3: Verify and deploy

**Files:**
- Modify: `apps/main-site/static/*`
- Deploy: `/opt/any-auto-register`

**Step 1: Run verification**

Run: `./.venv-test/bin/python -m unittest tests.test_auto_restock tests.test_gemini_session_auth tests.test_resin_slot_pool tests.test_shared_mailbox_providers tests.test_gemini_shared_config -v`

Run: `cd apps/main-site/frontend && npm run build`

Expected: all green

**Step 2: Deploy**

Run the same rsync-based deployment flow used for the current server, then verify the homepage serves the newest bundle and the backend process remains healthy.

**Step 3: Smoke test**

- Confirm the dashboard’s "CLIProxyAPI 号池" and "ChatGPT 自动补货" inventory counts now match on the same source of truth.
- Confirm auto-restock starts a new batch when the latch is enabled and inventory is still below target.

**Step 4: Commit deployment-related changes if needed**

```bash
git status --short
```

**Step 5: Report outcome**

- Summarize the root cause
- Summarize the changed behavior
- Note any remaining edge cases such as pool API outage handling
