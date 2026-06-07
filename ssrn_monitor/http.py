from __future__ import annotations

import ssl
import time
import urllib.request


HTML_ACCEPT = (
    "text/html,application/xhtml+xml,application/xml;q=0.9,"
    "application/rss+xml;q=0.8,*/*;q=0.7"
)
JSON_ACCEPT = "application/json, text/plain, */*"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "accounting-research-agent/0.1"
)


def ssl_context() -> ssl.SSLContext:
    return ssl.create_default_context()


def http_get(
    url: str,
    headers: dict[str, str] | None = None,
    timeout: int = 30,
    retries: int = 3,
    backoff_seconds: tuple[int, ...] = (0, 5, 15),
) -> bytes:
    last_error: Exception | None = None
    for attempt in range(retries):
        delay = backoff_seconds[min(attempt, len(backoff_seconds) - 1)]
        if delay > 0:
            time.sleep(delay)

        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": DEFAULT_USER_AGENT,
                "Accept": HTML_ACCEPT,
                "Accept-Language": "en-US,en;q=0.9",
                **(headers or {}),
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout, context=ssl_context()) as response:
                return response.read()
        except Exception as error:  # noqa: BLE001
            last_error = error

    raise RuntimeError(f"HTTP GET failed for {url}: {last_error}") from last_error
