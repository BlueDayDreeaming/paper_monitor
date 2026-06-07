from __future__ import annotations

from html.parser import HTMLParser


class _NetworkPapersParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.data_url: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "div":
            return
        attrs_map = dict(attrs)
        if attrs_map.get("id") != "network-papers":
            return
        self.data_url = attrs_map.get("data-url")


def discover_network_papers_api_url(html_text: str) -> str:
    parser = _NetworkPapersParser()
    parser.feed(html_text)
    if not parser.data_url:
        raise RuntimeError("Failed to locate #network-papers[data-url] on ARN page.")
    if "api.ssrn.com/content/v1/bindings/" not in parser.data_url:
        raise RuntimeError(f"Unexpected network papers API URL: {parser.data_url}")
    return parser.data_url
