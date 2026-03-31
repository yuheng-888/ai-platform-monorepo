import importlib
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class GeminiRequestBindingTests(unittest.TestCase):
    def _import_module(self):
        sys.modules.pop("embedded.gemini_business2api.core.request_binding", None)
        return importlib.import_module("embedded.gemini_business2api.core.request_binding")

    def test_normalize_forced_account_id_trims_empty_values(self):
        binding = self._import_module()

        self.assertIsNone(binding.normalize_forced_account_id(""))
        self.assertIsNone(binding.normalize_forced_account_id("   "))
        self.assertEqual(binding.normalize_forced_account_id(" gemini-account-1 "), "gemini-account-1")

    def test_scope_conversation_key_isolated_by_forced_account(self):
        binding = self._import_module()

        self.assertEqual(binding.scope_conversation_key("conv-key", None), "conv-key")
        self.assertEqual(
            binding.scope_conversation_key("conv-key", "gemini-account-1"),
            "conv-key::account:gemini-account-1",
        )
        self.assertNotEqual(
            binding.scope_conversation_key("conv-key", "gemini-account-1"),
            binding.scope_conversation_key("conv-key", "gemini-account-2"),
        )


if __name__ == "__main__":
    unittest.main()
