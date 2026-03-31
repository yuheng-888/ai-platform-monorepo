import importlib
import sys
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class CLIProxyAPIGeminiBusinessSyncTests(unittest.TestCase):
    def _import_sync_module(self):
        fake_external_apps = types.ModuleType("services.external_apps")
        fake_external_apps._main_site_public_url = lambda: "http://127.0.0.1:39001"

        fake_cliproxy_sync = types.ModuleType("services.cliproxyapi_sync")
        fake_cliproxy_sync.DEFAULT_CLIPROXYAPI_MANAGEMENT_KEY = "cliproxyapi"
        fake_cliproxy_sync.resolve_cliproxyapi_url = lambda api_url=None: (api_url or "http://127.0.0.1:8317").rstrip("/")
        fake_cliproxy_sync._build_upload_url = (
            lambda api_url, filename: f"{api_url.rstrip('/')}/v0/management/auth-files?name={filename}"
        )
        fake_cliproxy_sync._extract_error_message = lambda response: getattr(response, "text", "")

        with patch.dict(
            sys.modules,
            {
                "requests": MagicMock(),
                "services.external_apps": fake_external_apps,
                "services.cliproxyapi_sync": fake_cliproxy_sync,
            },
        ):
            sys.modules.pop("services.cliproxyapi_gemini_business_sync", None)
            return importlib.import_module("services.cliproxyapi_gemini_business_sync")

    def test_build_payload_includes_forced_account_routing_fields(self):
        sync_module = self._import_sync_module()
        account = SimpleNamespace(
            email="gemini@example.com",
            user_id="gemini-account-1",
            extra={
                "gemini_account_id": "gemini-account-1",
                "secure_c_ses": "secure-cookie",
                "host_c_oses": "host-cookie",
                "csesidx": "801018216",
                "config_id": "cfg-1",
                "expires_at": "2026-04-01T00:00:00Z",
            },
        )

        payload = sync_module.build_gemini_business_auth_payload(
            account,
            runtime_url="http://127.0.0.1:39001/gemini/v1",
            admin_key="gemini-admin-key",
        )

        self.assertEqual(payload["type"], "gemini-business")
        self.assertEqual(payload["email"], "gemini@example.com")
        self.assertEqual(payload["gemini_account_id"], "gemini-account-1")
        self.assertEqual(payload["base_url"], "http://127.0.0.1:39001/gemini/v1")
        self.assertEqual(payload["api_key"], "gemini-admin-key")
        self.assertEqual(payload["header:X-Gemini-Account-ID"], "gemini-account-1")
        self.assertEqual(payload["secure_c_ses"], "secure-cookie")
        self.assertEqual(payload["host_c_oses"], "host-cookie")

    def test_sync_posts_gemini_business_auth_file_to_management_api(self):
        sync_module = self._import_sync_module()
        account = SimpleNamespace(
            email="gemini@example.com",
            user_id="gemini-account-1",
            extra={"gemini_account_id": "gemini-account-1"},
        )

        response = SimpleNamespace(status_code=200, text="ok")
        with patch.object(sync_module.requests, "post", return_value=response) as mock_post:
            ok, message = sync_module.sync_gemini_account_to_cliproxyapi(
                account,
                api_url="http://127.0.0.1:8317",
                management_key="mgmt-key",
                runtime_url="http://127.0.0.1:39001/gemini/v1",
                admin_key="gemini-admin-key",
            )

        self.assertTrue(ok)
        self.assertEqual(message, "上传成功")
        self.assertEqual(
            mock_post.call_args.args[0],
            "http://127.0.0.1:8317/v0/management/auth-files?name=gemini@example.com.json",
        )
        self.assertEqual(mock_post.call_args.kwargs["headers"]["Authorization"], "Bearer mgmt-key")
        self.assertEqual(mock_post.call_args.kwargs["json"]["type"], "gemini-business")
        self.assertEqual(
            mock_post.call_args.kwargs["json"]["header:X-Gemini-Account-ID"],
            "gemini-account-1",
        )

    def test_sync_retries_write_when_models_not_ready_after_first_upload(self):
        sync_module = self._import_sync_module()
        account = SimpleNamespace(
            email="gemini@example.com",
            user_id="gemini-account-1",
            extra={"gemini_account_id": "gemini-account-1"},
        )

        response = SimpleNamespace(status_code=200, text="ok")
        model_responses = [
            SimpleNamespace(status_code=200, json=lambda: {"models": []}),
            SimpleNamespace(status_code=200, json=lambda: {"models": []}),
            SimpleNamespace(status_code=200, json=lambda: {"models": [{"id": "gemini-2.5-pro"}]}),
        ]

        with patch.object(sync_module.requests, "post", return_value=response) as mock_post, \
             patch.object(sync_module.requests, "get", side_effect=model_responses) as mock_get, \
             patch.object(sync_module.time, "sleep", return_value=None):
            ok, message = sync_module.sync_gemini_account_to_cliproxyapi(
                account,
                api_url="http://127.0.0.1:8317",
                management_key="mgmt-key",
                runtime_url="http://127.0.0.1:39001/gemini/v1",
                admin_key="gemini-admin-key",
            )

        self.assertTrue(ok)
        self.assertEqual(message, "上传成功")
        self.assertEqual(mock_post.call_count, 2)
        self.assertEqual(mock_get.call_count, 3)

    def test_external_sync_routes_gemini_accounts_to_cliproxyapi(self):
        fake_config_store_module = types.ModuleType("core.config_store")
        fake_config_store_module.config_store = SimpleNamespace(
            get=lambda key, default="": {
                "cliproxyapi_url": "http://127.0.0.1:8317",
            }.get(key, default)
        )
        fake_helper_module = types.ModuleType("services.cliproxyapi_gemini_business_sync")
        fake_helper_module.is_cliproxyapi_enabled = lambda api_url=None: True
        fake_helper_module.sync_gemini_account_to_cliproxyapi = (
            lambda account, api_url=None: (True, f"uploaded {account.email} to {api_url}")
        )

        with patch.dict(
            sys.modules,
            {
                "core.config_store": fake_config_store_module,
                "services.cliproxyapi_gemini_business_sync": fake_helper_module,
            },
        ):
            sys.modules.pop("services.external_sync", None)
            external_sync = importlib.import_module("services.external_sync")

            results = external_sync.sync_account(
                SimpleNamespace(platform="gemini", email="gemini@example.com", extra={"gemini_account_id": "gemini-account-1"})
            )

        self.assertEqual(
            results,
            [{"name": "CLIProxyAPI", "ok": True, "msg": "uploaded gemini@example.com to http://127.0.0.1:8317"}],
        )


if __name__ == "__main__":
    unittest.main()
