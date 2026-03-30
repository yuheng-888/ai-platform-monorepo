import unittest

from core.resin_slot_pool import (
    build_register_slot_accounts,
    parse_resin_proxy_identity,
    sanitize_slot_value,
)


class ResinSlotPoolTests(unittest.TestCase):
    def test_sanitize_slot_value_normalizes_ip_text(self):
        self.assertEqual(sanitize_slot_value("147.161.239.227"), "147-161-239-227")
        self.assertEqual(sanitize_slot_value(" 2001:db8::1 "), "2001-db8-1")
        self.assertEqual(sanitize_slot_value(""), "slot")

    def test_build_register_slot_accounts_uses_default_and_whitelist_limits(self):
        leases = [
            {
                "account": f"acc-us-{idx}",
                "egress_ip": "1.1.1.1",
                "node_tag": "pool/us-a",
                "node_hash": f"hash-us-{idx}",
            }
            for idx in range(1, 8)
        ] + [
            {
                "account": f"acc-jp-{idx}",
                "egress_ip": "2.2.2.2",
                "node_tag": "pool/jp-a",
                "node_hash": f"hash-jp-{idx}",
            }
            for idx in range(1, 4)
        ]

        accounts, inherit_requests = build_register_slot_accounts(
            leases=leases,
            platform_name="chatgpt-register",
            default_slots_per_ip=5,
            whitelist_slots_per_ip=10,
            whitelist_entries={"2.2.2.2"},
        )

        self.assertEqual(len([item for item in accounts if item.startswith("acc-us-")]), 5)
        self.assertEqual(len([item for item in accounts if item.startswith("acc-jp-")]), 3)
        self.assertEqual(len(inherit_requests), 7)
        self.assertEqual(
            [item["new_account"] for item in inherit_requests[:2]],
            [
                "slot-pool.chatgpt-register.2-2-2-2.slot-04",
                "slot-pool.chatgpt-register.2-2-2-2.slot-05",
            ],
        )

    def test_parse_resin_proxy_identity_extracts_platform_and_account(self):
        parsed = parse_resin_proxy_identity(
            "http://chatgpt-register.slot-pool.chatgpt-register.1-1-1-1.slot-01:token@example.com:39024"
        )
        self.assertEqual(parsed, ("chatgpt-register", "slot-pool.chatgpt-register.1-1-1-1.slot-01"))

        parsed_without_account = parse_resin_proxy_identity(
            "http://chatgpt-register:token@example.com:39024"
        )
        self.assertEqual(parsed_without_account, ("chatgpt-register", ""))


if __name__ == "__main__":
    unittest.main()
