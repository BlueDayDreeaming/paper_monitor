from __future__ import annotations

import unittest

from ssrn_monitor.fetch import build_papers_page_url
from ssrn_monitor.http import ARN_HOME_URL, JSON_ACCEPT, build_headers


class HttpTest(unittest.TestCase):
    def test_api_headers_include_referer_origin_and_json_accept(self) -> None:
        headers = build_headers("https://api.ssrn.com/content/v1/bindings/204/papers?index=0&count=1&sort=0")
        self.assertEqual(headers["Accept"], JSON_ACCEPT)
        self.assertEqual(headers["Referer"], ARN_HOME_URL)
        self.assertEqual(headers["Origin"], "https://www.ssrn.com")
        self.assertEqual(headers["X-Requested-With"], "XMLHttpRequest")

    def test_homepage_headers_include_html_accept(self) -> None:
        headers = build_headers("https://www.ssrn.com/index.cfm/en/arn/")
        self.assertIn("text/html", headers["Accept"])
        self.assertEqual(headers["Referer"], "https://www.ssrn.com/")

    def test_builds_papers_page_url(self) -> None:
        self.assertEqual(
            build_papers_page_url("https://api.ssrn.com/content/v1/bindings/204/papers", 2),
            "https://api.ssrn.com/content/v1/bindings/204/papers?index=100&count=50&sort=0",
        )


if __name__ == "__main__":
    unittest.main()
