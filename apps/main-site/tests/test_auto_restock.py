import unittest
from unittest.mock import patch

from services import auto_restock


def _config_side_effect(overrides: dict[str, str]):
    defaults = {
        "cliproxyapi_url": "http://127.0.0.1:8317",
        "chatgpt_auto_restock_enabled": "1",
        "chatgpt_auto_restock_threshold": "5000",
        "chatgpt_auto_restock_target": "10000",
        "chatgpt_auto_restock_batch_size": "1000",
        "chatgpt_auto_restock_concurrency": "20",
        "chatgpt_auto_restock_proxy": "",
        "chatgpt_auto_restock_executor_type": "protocol",
        "chatgpt_auto_restock_captcha_solver": "yescaptcha",
        "register_max_concurrency": "20",
    }
    defaults.update(overrides)

    def _get(key: str, default: str = "") -> str:
        return defaults.get(key, default)

    return _get


class ChatGptAutoRestockTests(unittest.TestCase):
    @patch("api.tasks.has_active_auto_restock_task", return_value=False)
    @patch("services.auto_restock._get_chatgpt_inventory_snapshot", create=True)
    def test_restock_summary_uses_cliproxyapi_enabled_inventory(self, mock_inventory_snapshot, _mock_has_active_task):
        mock_inventory_snapshot.return_value = {
            "available": 5756,
            "source": "cliproxyapi",
            "last_error": "",
        }

        with patch.object(auto_restock.config_store, "get", side_effect=_config_side_effect({})):
            summary = auto_restock.get_chatgpt_restock_summary()

        self.assertEqual(summary["available"], 5756)
        self.assertEqual(summary["source"], "cliproxyapi")
        self.assertEqual(summary["last_error"], "")

    @patch("api.tasks.start_register_task", return_value="task_123")
    @patch("api.tasks.has_active_auto_restock_task", return_value=False)
    @patch("services.auto_restock._get_chatgpt_inventory_snapshot", create=True)
    def test_restock_continues_toward_target_when_inventory_is_above_threshold(
        self,
        mock_inventory_snapshot,
        _mock_has_active_task,
        mock_start_task,
    ):
        mock_inventory_snapshot.return_value = {
            "available": 5812,
            "source": "cliproxyapi",
            "last_error": "",
        }

        with patch.object(auto_restock.config_store, "get", side_effect=_config_side_effect({})):
            result = auto_restock.check_and_trigger_chatgpt_auto_restock()

        self.assertTrue(result["triggered"])
        self.assertEqual(result["available"], 5812)
        self.assertEqual(result["count"], 1000)
        self.assertEqual(result["task_id"], "task_123")

        req = mock_start_task.call_args.kwargs["req"]
        self.assertEqual(req.platform, "chatgpt")
        self.assertEqual(req.count, 1000)
        self.assertEqual(req.concurrency, 20)

    @patch("api.tasks.has_active_auto_restock_task", return_value=False)
    @patch("services.auto_restock._get_chatgpt_inventory_snapshot", create=True)
    def test_restock_stops_when_target_inventory_is_reached(self, mock_inventory_snapshot, _mock_has_active_task):
        mock_inventory_snapshot.return_value = {
            "available": 10000,
            "source": "cliproxyapi",
            "last_error": "",
        }

        with patch.object(auto_restock.config_store, "get", side_effect=_config_side_effect({})):
            result = auto_restock.check_and_trigger_chatgpt_auto_restock()

        self.assertFalse(result["triggered"])
        self.assertEqual(result["reason"], "target_met")
        self.assertEqual(result["available"], 10000)

    @patch("api.tasks.has_active_auto_restock_task", return_value=False)
    @patch("services.auto_restock._get_chatgpt_inventory_snapshot", create=True)
    def test_restock_pauses_when_pool_inventory_is_unavailable(self, mock_inventory_snapshot, _mock_has_active_task):
        mock_inventory_snapshot.return_value = {
            "available": 0,
            "source": "cliproxyapi",
            "last_error": "pool unavailable",
        }

        with patch.object(auto_restock.config_store, "get", side_effect=_config_side_effect({})):
            result = auto_restock.check_and_trigger_chatgpt_auto_restock()

        self.assertFalse(result["triggered"])
        self.assertEqual(result["reason"], "inventory_unavailable")
        self.assertEqual(result["last_error"], "pool unavailable")


if __name__ == "__main__":
    unittest.main()
