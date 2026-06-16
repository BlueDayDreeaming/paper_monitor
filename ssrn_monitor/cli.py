from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from ssrn_monitor.dates import default_target_date_et
from ssrn_monitor.discovery import DEFAULT_ARN_API_URL, discover_network_papers_api_url
from ssrn_monitor.fetch import fetch_papers_for_date
from ssrn_monitor.http import http_get
from ssrn_monitor.match import match_papers_to_targets
from ssrn_monitor.playwright_fetch import fetch_papers_for_date_with_playwright
from ssrn_monitor.proxies import load_proxies_from_env, load_proxies_from_file
from ssrn_monitor.report import build_markdown_report, write_markdown_report
from ssrn_monitor.watch_targets import load_watch_targets


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Monitor SSRN Accounting Research Network daily papers.")
    parser.add_argument("--date-et", dest="date_et", help="Target America/New_York date in YYYY-MM-DD format.")
    parser.add_argument("--page-cap", dest="page_cap", type=int, default=10, help="Maximum pages to scan.")
    parser.add_argument(
        "--api-url",
        dest="api_url",
        help="Override the ARN papers API URL and skip homepage discovery.",
    )
    parser.add_argument(
        "--proxy-file",
        dest="proxy_file",
        help="Optional local proxy list file. GitHub Actions should use the SSRN_PROXIES secret instead.",
    )
    parser.add_argument(
        "--fetcher",
        choices=("playwright", "http"),
        default="playwright",
        help="Fetcher backend. Defaults to Playwright for GitHub Actions compatibility.",
    )
    return parser


def resolve_api_url(api_url_override: str | None, proxies: Sequence[str] | None = None) -> tuple[str, list[str]]:
    if api_url_override:
        return api_url_override, []

    try:
        homepage_html = http_get("https://www.ssrn.com/index.cfm/en/arn/", proxies=proxies).decode(
            "utf-8",
            errors="replace",
        )
        return discover_network_papers_api_url(homepage_html), []
    except Exception as error:  # noqa: BLE001
        return (
            DEFAULT_ARN_API_URL,
            [f"Homepage discovery failed; fell back to default ARN API URL: {error}"],
        )


def load_proxy_pool(proxy_file: str | None) -> list[str]:
    if proxy_file:
        return load_proxies_from_file(proxy_file)
    return load_proxies_from_env()


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.date_et and len(args.date_et) != 10:
        parser.error("--date-et must be in YYYY-MM-DD format.")
    if args.page_cap < 1:
        parser.error("--page-cap must be >= 1.")

    repo_root = Path.cwd()
    report_dir = repo_root / "reports"
    target_date_et = args.date_et or default_target_date_et()
    proxy_pool = load_proxy_pool(args.proxy_file)
    print(f"Target date (ET): {target_date_et}", flush=True)
    print(f"Proxies loaded: {len(proxy_pool)}", flush=True)
    if args.fetcher == "playwright":
        api_url, papers, stats, warnings = fetch_papers_for_date_with_playwright(
            api_url_override=args.api_url,
            target_date_et=target_date_et,
            page_cap=args.page_cap,
            proxies=proxy_pool,
        )
    else:
        api_url, warnings = resolve_api_url(args.api_url, proxy_pool)
        papers, stats, fetch_warnings = fetch_papers_for_date(api_url, target_date_et, args.page_cap, proxy_pool)
        warnings.extend(fetch_warnings)

    targets = load_watch_targets()
    matches = match_papers_to_targets(papers, targets)
    markdown = build_markdown_report(target_date_et, stats, warnings, matches)
    report_path = write_markdown_report(report_dir, target_date_et, markdown)

    print(f"API URL: {api_url}")
    print(f"Pages scanned: {stats['pages_scanned']}")
    print(f"Papers scanned: {stats['papers_scanned']}")
    print(f"Papers on target date: {stats['target_papers']}")
    print(f"Matched papers: {len({match.paper.abstract_id for match in matches})}")
    print(f"Report: {report_path}")
    if warnings:
        for warning in warnings:
            print(f"Warning: {warning}")

    return 0
