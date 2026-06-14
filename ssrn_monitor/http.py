from __future__ import annotations

import ssl
import time
import urllib.request
from collections.abc import Sequence
from urllib.error import HTTPError


HTML_ACCEPT = (
    "text/html,application/xhtml+xml,application/xml;q=0.9,"
    "application/rss+xml;q=0.8,*/*;q=0.7"
)
JSON_ACCEPT = "application/json, text/plain, */*"
ARN_HOME_URL = "https://www.ssrn.com/index.cfm/en/arn/"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/137.0.0.0 Safari/537.36"
)


def ssl_context() -> ssl.SSLContext:
    return ssl.create_default_context()


def build_headers(url: str, headers: dict[str, str] | None = None) -> dict[str, str]:
    resolved = {
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept": JSON_ACCEPT if "api.ssrn.com" in url else HTML_ACCEPT,
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }

    if "api.ssrn.com" in url:
        resolved.update(
            {
                "Origin": "https://www.ssrn.com",
                "Referer": ARN_HOME_URL,
                "X-Requested-With": "XMLHttpRequest",
            }
        )
    elif "ssrn.com" in url:
        resolved["Referer"] = "https://www.ssrn.com/"

    if headers:
        resolved.update(headers)

    return resolved


def http_get(
    url: str,
    headers: dict[str, str] | None = None,
    timeout: int = 30,
    retries: int = 3,
    backoff_seconds: tuple[int, ...] = (0, 5, 15),
    proxies: Sequence[str] | None = None,
) -> bytes:
    last_error: Exception | None = None
    proxy_pool = list(proxies or [])
    attempts = max(retries, len(proxy_pool) or 0)

    for attempt in range(attempts):
        delay = backoff_seconds[min(attempt, len(backoff_seconds) - 1)]
        if delay > 0:
            time.sleep(delay)

        proxy_url = proxy_pool[attempt % len(proxy_pool)] if proxy_pool else None
        request = urllib.request.Request(
            url,
            headers=build_headers(url, headers),
        )
        try:
            if proxy_url:
                opener = urllib.request.build_opener(
                    urllib.request.ProxyHandler({"http": proxy_url, "https": proxy_url}),
                    urllib.request.HTTPSHandler(context=ssl_context()),
                )
                response_context = opener.open(request, timeout=timeout)
            else:
                response_context = urllib.request.urlopen(request, timeout=timeout, context=ssl_context())

            with response_context as response:
                return response.read()
        except HTTPError as error:
            last_error = error
            if error.code == 403 and not proxy_pool:
                break
        except Exception as error:  # noqa: BLE001
            last_error = error

    if isinstance(last_error, HTTPError) and last_error.code == 403:
        raise RuntimeError(
            "HTTP GET failed with 403 Forbidden for "
            f"{url}. SSRN is likely blocking this runner's outbound IP or all configured proxies."
        ) from last_error

    raise RuntimeError(f"HTTP GET failed for {url}: {last_error}") from last_error
