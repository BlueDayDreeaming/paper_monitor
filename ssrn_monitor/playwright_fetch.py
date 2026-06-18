from __future__ import annotations

import json
from collections.abc import Sequence
from urllib.error import HTTPError

from ssrn_monitor.discovery import DEFAULT_ARN_API_URL, discover_network_papers_api_url
from ssrn_monitor.fetch import build_papers_page_url, transform_paper
from ssrn_monitor.http import ARN_HOME_URL, DEFAULT_USER_AGENT, JSON_ACCEPT
from ssrn_monitor.models import Paper
from ssrn_monitor.proxies import playwright_proxy_config
from ssrn_monitor.proxy_bridge import ProxyBridge


def _format_attempt_error(error: Exception) -> str:
    if isinstance(error, HTTPError):
        return f"HTTP {error.code}"
    message = str(error).splitlines()[0].strip()
    if not message:
        return type(error).__name__
    if len(message) > 160:
        message = f"{message[:157]}..."
    return f"{type(error).__name__}: {message}"


def _fetch_json_from_page(page, url: str, timeout_ms: int) -> dict:
    result = page.evaluate(
        """async (url) => {
            const response = await fetch(url, {
                method: "GET",
                credentials: "include",
                headers: { "Accept": "application/json, text/plain, */*" }
            });
            const text = await response.text();
            return {
                ok: response.ok,
                status: response.status,
                statusText: response.statusText,
                text
            };
        }""",
        url,
    )
    if not result["ok"]:
        raise HTTPError(url, result["status"], result["statusText"], {}, None)
    return json.loads(result["text"])


def _fetch_json_from_context(context, url: str, timeout_ms: int) -> dict:
    response = context.request.get(url, headers={"Accept": JSON_ACCEPT}, timeout=timeout_ms)
    text = response.text()
    if not response.ok:
        raise HTTPError(url, response.status, response.status_text, response.headers, None)
    return json.loads(text)


def _fetch_json(page, url: str, timeout_ms: int) -> dict:
    try:
        return _fetch_json_from_page(page, url, timeout_ms)
    except Exception:
        return _fetch_json_from_context(page.context, url, timeout_ms)


def _discover_api_url(page, api_url_override: str | None, timeout_ms: int) -> tuple[str, list[str]]:
    if api_url_override:
        return api_url_override, []

    warnings: list[str] = []
    try:
        page.goto(ARN_HOME_URL, wait_until="domcontentloaded", timeout=timeout_ms)
        page.wait_for_timeout(1500)
        html = page.content()
        return discover_network_papers_api_url(html), warnings
    except Exception as error:  # noqa: BLE001
        warnings.append(f"Playwright homepage discovery failed; fell back to default ARN API URL: {error}")
        return DEFAULT_ARN_API_URL, warnings


def _fetch_with_browser_attempt(
    *,
    api_url_override: str | None,
    target_date_et: str,
    page_cap: int,
    proxy_url: str | None,
    timeout_ms: int,
) -> tuple[str, list[Paper], dict[str, int], list[str]]:
    from playwright.sync_api import sync_playwright

    launch_options = {"headless": True}
    proxy_bridge = None
    if proxy_url and proxy_url.startswith("socks5://") and "@" in proxy_url:
        proxy_bridge = ProxyBridge(proxy_url, timeout=max(timeout_ms // 1000, 1))
        proxy_bridge.start()
        launch_options["proxy"] = proxy_bridge.playwright_proxy_config()
    elif proxy_url:
        launch_options["proxy"] = playwright_proxy_config(proxy_url)

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(**launch_options)
            try:
                context = browser.new_context(
                    user_agent=DEFAULT_USER_AGENT,
                    locale="en-US",
                    viewport={"width": 1365, "height": 900},
                    extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
                )
                page = context.new_page()
                page.set_default_timeout(timeout_ms)
                api_url, warnings = _discover_api_url(page, api_url_override, timeout_ms)

                pages_scanned = 0
                papers_scanned = 0
                matched: list[Paper] = []

                for page_index in range(page_cap):
                    page_url = build_papers_page_url(api_url, page_index)
                    payload = _fetch_json(page, page_url, timeout_ms)
                    papers = [transform_paper(paper) for paper in payload.get("papers", [])]

                    pages_scanned += 1
                    papers_scanned += len(papers)
                    matched.extend([paper for paper in papers if paper.approved_date_et == target_date_et])

                    page_dates = sorted({paper.approved_date_et for paper in papers})
                    oldest_date = page_dates[0] if page_dates else None
                    newest_date = page_dates[-1] if page_dates else None

                    if oldest_date and oldest_date < target_date_et:
                        break

                    if page_index + 1 == page_cap and newest_date and newest_date >= target_date_et:
                        warnings.append(
                            f"Reached page cap ({page_cap}) before seeing papers older than {target_date_et}. "
                            "Increase --page-cap if needed."
                        )

                stats = {
                    "pages_scanned": pages_scanned,
                    "papers_scanned": papers_scanned,
                    "target_papers": len(matched),
                }
                return api_url, matched, stats, warnings
            finally:
                browser.close()
    finally:
        if proxy_bridge:
            proxy_bridge.close()


def fetch_papers_for_date_with_playwright(
    *,
    api_url_override: str | None,
    target_date_et: str,
    page_cap: int,
    proxies: Sequence[str] | None = None,
    timeout_ms: int = 60000,
) -> tuple[str, list[Paper], dict[str, int], list[str]]:
    proxy_pool = list(proxies or [])
    attempts: list[str | None] = proxy_pool or [None]
    attempt_errors: list[str] = []

    for index, proxy_url in enumerate(attempts, start=1):
        try:
            return _fetch_with_browser_attempt(
                api_url_override=api_url_override,
                target_date_et=target_date_et,
                page_cap=page_cap,
                proxy_url=proxy_url,
                timeout_ms=timeout_ms,
            )
        except Exception as error:  # noqa: BLE001
            attempt_label = f"proxy {index}" if proxy_url else "direct"
            attempt_errors.append(f"{attempt_label}: {_format_attempt_error(error)}")

    raise RuntimeError("Playwright fetch failed. Attempt summary: " + "; ".join(attempt_errors))
