from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote, urlsplit


PROXY_ENV_VAR = "SSRN_PROXIES"
DEFAULT_PROXY_SCHEME_ENV_VAR = "SSRN_PROXY_SCHEME"


def _split_host_port(value: str) -> tuple[str, str]:
    host, separator, port = value.rpartition(":")
    if not separator or not host or not port.isdigit():
        raise ValueError("proxy host and port must use host:port format")
    return host, port


def normalize_proxy_entry(value: str, default_scheme: str = "socks5") -> str:
    raw = value.strip()
    if not raw:
        raise ValueError("empty proxy entry")

    if "://" in raw:
        parsed = urlsplit(raw)
        if parsed.scheme not in {"http", "https", "socks4", "socks5"}:
            raise ValueError(f"unsupported proxy scheme: {parsed.scheme}")
        if not parsed.hostname or parsed.port is None:
            raise ValueError("proxy URL must include host and port")
        return raw

    if "@" in raw:
        credentials, host_port = raw.rsplit("@", 1)
        username, separator, password = credentials.partition(":")
        if not separator or not username or not password:
            raise ValueError("proxy credentials must use username:password")
        host, port = _split_host_port(host_port)
        return f"{default_scheme}://{quote(username, safe='')}:{quote(password, safe='')}@{host}:{port}"

    parts = raw.split(":")
    if len(parts) == 2:
        host, port = _split_host_port(raw)
        return f"{default_scheme}://{host}:{port}"

    if len(parts) == 4:
        if parts[1].isdigit():
            host, port, username, password = parts
        elif parts[3].isdigit():
            username, password, host, port = parts
        else:
            raise ValueError("four-part proxy entry must include one port field")
        return f"{default_scheme}://{quote(username, safe='')}:{quote(password, safe='')}@{host}:{port}"

    raise ValueError("unsupported proxy entry format")


def parse_proxy_entries(raw_value: str, default_scheme: str = "socks5") -> list[str]:
    proxies: list[str] = []
    for raw_entry in raw_value.replace(",", "\n").splitlines():
        entry = raw_entry.strip()
        if not entry or entry.startswith("#"):
            continue
        proxies.append(normalize_proxy_entry(entry, default_scheme=default_scheme))
    return proxies


def load_proxies_from_env() -> list[str]:
    default_scheme = os.environ.get(DEFAULT_PROXY_SCHEME_ENV_VAR, "socks5")
    return parse_proxy_entries(os.environ.get(PROXY_ENV_VAR, ""), default_scheme=default_scheme)


def load_proxies_from_file(path: str | Path) -> list[str]:
    default_scheme = os.environ.get(DEFAULT_PROXY_SCHEME_ENV_VAR, "socks5")
    return parse_proxy_entries(Path(path).read_text(encoding="utf-8"), default_scheme=default_scheme)
