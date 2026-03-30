import unittest

from core.base_mailbox import CfMailMailbox, GptMailMailbox, create_mailbox


class SharedMailboxProviderTests(unittest.TestCase):
    def test_create_mailbox_supports_gptmail(self):
        mailbox = create_mailbox(
            "gptmail",
            extra={
                "gptmail_base_url": "https://mail.example.com",
                "gptmail_api_key": "gpt-secret",
                "gptmail_domain": "mail.example.com",
                "gptmail_verify_ssl": "0",
            },
            proxy="http://127.0.0.1:8080",
        )

        self.assertIsInstance(mailbox, GptMailMailbox)
        self.assertEqual(mailbox.client.base_url, "https://mail.example.com")
        self.assertEqual(mailbox.client.api_key, "gpt-secret")
        self.assertEqual(mailbox.client.domain, "mail.example.com")
        self.assertFalse(mailbox.client.verify_ssl)
        self.assertEqual(mailbox.client.proxy_url, "http://127.0.0.1:8080")

    def test_create_mailbox_supports_cfmail(self):
        mailbox = create_mailbox(
            "cfmail",
            extra={
                "cfmail_base_url": "https://cfmail.example.com",
                "cfmail_api_key": "cf-secret",
                "cfmail_domain": "cfmail.example.com",
                "cfmail_verify_ssl": "false",
            },
            proxy="http://127.0.0.1:8080",
        )

        self.assertIsInstance(mailbox, CfMailMailbox)
        self.assertEqual(mailbox.client.base_url, "https://cfmail.example.com")
        self.assertEqual(mailbox.client.api_key, "cf-secret")
        self.assertEqual(mailbox.client.domain, "cfmail.example.com")
        self.assertFalse(mailbox.client.verify_ssl)
        self.assertEqual(mailbox.client.proxy_url, "http://127.0.0.1:8080")


if __name__ == "__main__":
    unittest.main()
