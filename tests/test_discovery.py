from __future__ import annotations

import unittest
from unittest.mock import patch

from ssrn_monitor.discovery import discover_network_papers_api_url
from ssrn_monitor.cli import resolve_api_url


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

    def test_cli_falls_back_to_default_api_when_homepage_fetch_fails(self) -> None:
        with patch("ssrn_monitor.cli.http_get", side_effect=RuntimeError("403")):
            api_url, warnings = resolve_api_url(None)

        self.assertEqual(api_url, "https://api.ssrn.com/content/v1/bindings/204/papers")
        self.assertEqual(len(warnings), 1)
        self.assertIn("fell back to default ARN API URL", warnings[0])


if __name__ == "__main__":
    unittest.main()
