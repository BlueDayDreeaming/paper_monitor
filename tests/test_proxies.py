from __future__ import annotations

import unittest

from ssrn_monitor.proxies import normalize_proxy_entry, parse_proxy_entries


class ProxiesTest(unittest.TestCase):
    def test_normalizes_host_port_username_password(self) -> None:
        self.assertEqual(
            normalize_proxy_entry("proxy.example.com:8080:user:pass"),
            "http://user:pass@proxy.example.com:8080",
        )

    def test_normalizes_username_password_host_port(self) -> None:
        self.assertEqual(
            normalize_proxy_entry("user:pass:proxy.example.com:8080"),
            "http://user:pass@proxy.example.com:8080",
        )

    def test_normalizes_username_password_at_host_port(self) -> None:
        self.assertEqual(
            normalize_proxy_entry("user:pass@proxy.example.com:8080"),
            "http://user:pass@proxy.example.com:8080",
        )

    def test_parses_multiline_and_comma_separated_entries(self) -> None:
        proxies = parse_proxy_entries("proxy1.example.com:8001:user:pass\nproxy2.example.com:8002,")
        self.assertEqual(len(proxies), 2)


if __name__ == "__main__":
    unittest.main()
