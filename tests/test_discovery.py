from __future__ import annotations

import unittest

from ssrn_monitor.discovery import discover_network_papers_api_url


class DiscoveryTest(unittest.TestCase):
    def test_extracts_network_papers_data_url(self) -> None:
        html = """
        <html>
          <body>
            <div id="network-papers" data-url="https://api.ssrn.com/content/v1/bindings/204/papers"></div>
          </body>
        </html>
        """
        self.assertEqual(
            discover_network_papers_api_url(html),
            "https://api.ssrn.com/content/v1/bindings/204/papers",
        )


if __name__ == "__main__":
    unittest.main()
