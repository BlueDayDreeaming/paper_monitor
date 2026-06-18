from __future__ import annotations

import unittest

from ssrn_monitor.proxy_bridge import ProxyBridge


class ProxyBridgeTest(unittest.TestCase):
    def test_requires_start_before_config(self) -> None:
        bridge = ProxyBridge("socks5://user:pass@127.0.0.1:9999")
        with self.assertRaises(RuntimeError):
            bridge.playwright_proxy_config()

    def test_builds_local_playwright_proxy_config(self) -> None:
        with ProxyBridge("socks5://user:pass@127.0.0.1:9999") as bridge:
            config = bridge.playwright_proxy_config()

        self.assertTrue(config["server"].startswith("http://127.0.0.1:"))


if __name__ == "__main__":
    unittest.main()
