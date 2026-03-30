import unittest

from embedded.gemini_business2api.shared_config import apply_main_site_shared_config


class GeminiSharedConfigTests(unittest.TestCase):
    def test_apply_main_site_shared_config_overrides_mailbox_settings(self):
        config_data = {
            "basic": {
                "temp_mail_provider": "duckmail",
                "duckmail_base_url": "https://old-duckmail.example.com",
                "duckmail_api_key": "old-duckmail-key",
                "moemail_base_url": "https://old-moemail.example.com",
                "moemail_api_key": "old-moemail-key",
                "freemail_base_url": "https://old-freemail.example.com",
                "freemail_jwt_token": "old-freemail-key",
                "gptmail_base_url": "https://old-gptmail.example.com",
                "gptmail_api_key": "old-gptmail-key",
                "cfmail_base_url": "https://old-cfmail.example.com",
                "cfmail_api_key": "old-cfmail-key",
                "register_max_concurrency": 2,
            }
        }

        apply_main_site_shared_config(
            config_data,
            {
                "mail_provider": "cfmail",
                "duckmail_provider_url": "https://api.duckmail.sbs",
                "duckmail_bearer": "duckmail-key",
                "moemail_api_url": "https://moemail.example.com",
                "moemail_api_key": "moemail-key",
                "moemail_domain": "moemail.example.com",
                "freemail_api_url": "https://freemail.example.com",
                "freemail_admin_token": "freemail-key",
                "freemail_domain": "freemail.example.com",
                "gptmail_base_url": "https://gptmail.example.com",
                "gptmail_api_key": "gptmail-key",
                "gptmail_domain": "gptmail.example.com",
                "gptmail_verify_ssl": "0",
                "cfmail_base_url": "https://cfmail.example.com",
                "cfmail_api_key": "cfmail-key",
                "cfmail_domain": "cfmail.example.com",
                "cfmail_verify_ssl": "false",
                "register_max_concurrency": "7",
            },
        )

        basic = config_data["basic"]
        self.assertEqual(basic["temp_mail_provider"], "cfmail")
        self.assertEqual(basic["register_max_concurrency"], 7)
        self.assertEqual(basic["duckmail_base_url"], "https://api.duckmail.sbs")
        self.assertEqual(basic["duckmail_api_key"], "duckmail-key")
        self.assertEqual(basic["moemail_base_url"], "https://moemail.example.com")
        self.assertEqual(basic["moemail_api_key"], "moemail-key")
        self.assertEqual(basic["moemail_domain"], "moemail.example.com")
        self.assertEqual(basic["freemail_base_url"], "https://freemail.example.com")
        self.assertEqual(basic["freemail_jwt_token"], "freemail-key")
        self.assertEqual(basic["freemail_domain"], "freemail.example.com")
        self.assertEqual(basic["gptmail_base_url"], "https://gptmail.example.com")
        self.assertEqual(basic["gptmail_api_key"], "gptmail-key")
        self.assertEqual(basic["gptmail_domain"], "gptmail.example.com")
        self.assertFalse(basic["gptmail_verify_ssl"])
        self.assertEqual(basic["cfmail_base_url"], "https://cfmail.example.com")
        self.assertEqual(basic["cfmail_api_key"], "cfmail-key")
        self.assertEqual(basic["cfmail_domain"], "cfmail.example.com")
        self.assertFalse(basic["cfmail_verify_ssl"])


if __name__ == "__main__":
    unittest.main()
