from __future__ import annotations

import ssl
import time
import urllib.request
import http.client
import socket
from collections.abc import Sequence
from urllib.error import HTTPError
from urllib.parse import unquote, urlsplit


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


def _read_exact(sock: socket.socket, size: int) -> bytes:
    data = b""
    while len(data) < size:
        chunk = sock.recv(size - len(data))
        if not chunk:
            raise OSError("SOCKS5 proxy closed the connection")
        data += chunk
    return data


def _open_socks5_socket(proxy_url: str, target_host: str, target_port: int, timeout: int) -> socket.socket:
    parsed = urlsplit(proxy_url)
    if not parsed.hostname or parsed.port is None:
        raise ValueError("SOCKS5 proxy URL must include host and port")

    username = unquote(parsed.username or "")
    password = unquote(parsed.password or "")
    methods = [2] if username or password else [0]

    sock = socket.create_connection((parsed.hostname, parsed.port), timeout=timeout)
    sock.settimeout(timeout)
    try:
        sock.sendall(bytes([5, len(methods), *methods]))
        version, method = _read_exact(sock, 2)
        if version != 5 or method == 255:
            raise OSError("SOCKS5 proxy rejected authentication methods")

        if method == 2:
            username_bytes = username.encode()
            password_bytes = password.encode()
            if len(username_bytes) > 255 or len(password_bytes) > 255:
                raise ValueError("SOCKS5 username/password must be <= 255 bytes")
            sock.sendall(
                b"\x01"
                + bytes([len(username_bytes)])
                + username_bytes
                + bytes([len(password_bytes)])
                + password_bytes
            )
            auth_version, status = _read_exact(sock, 2)
            if auth_version != 1 or status != 0:
                raise OSError("SOCKS5 proxy authentication failed")

        host_bytes = target_host.encode("idna")
        if len(host_bytes) > 255:
            raise ValueError("SOCKS5 target host is too long")
        sock.sendall(b"\x05\x01\x00\x03" + bytes([len(host_bytes)]) + host_bytes + target_port.to_bytes(2, "big"))

        version, reply, _reserved, address_type = _read_exact(sock, 4)
        if version != 5 or reply != 0:
            raise OSError(f"SOCKS5 proxy connect failed with reply {reply}")

        if address_type == 1:
            _read_exact(sock, 4)
        elif address_type == 3:
            address_length = _read_exact(sock, 1)[0]
            _read_exact(sock, address_length)
        elif address_type == 4:
            _read_exact(sock, 16)
        else:
            raise OSError(f"SOCKS5 proxy returned unsupported address type {address_type}")
        _read_exact(sock, 2)
        return sock
    except Exception:
        sock.close()
        raise


def _http_get_via_socks5(
    url: str,
    headers: dict[str, str] | None,
    timeout: int,
    proxy_url: str,
) -> bytes:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError(f"Unsupported URL scheme for SOCKS5 request: {parsed.scheme}")
    if not parsed.hostname:
        raise ValueError("URL must include a host")

    target_port = parsed.port or (443 if parsed.scheme == "https" else 80)
    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"

    raw_sock = _open_socks5_socket(proxy_url, parsed.hostname, target_port, timeout)
    sock: socket.socket | ssl.SSLSocket
    if parsed.scheme == "https":
        sock = ssl_context().wrap_socket(raw_sock, server_hostname=parsed.hostname)
    else:
        sock = raw_sock

    try:
        resolved_headers = build_headers(url, headers)
        host_header = parsed.hostname if parsed.port is None else f"{parsed.hostname}:{parsed.port}"
        header_lines = [f"GET {path} HTTP/1.1", f"Host: {host_header}", "Connection: close"]
        header_lines.extend(
            f"{key}: {value}"
            for key, value in resolved_headers.items()
            if key.lower() not in {"host", "connection"}
        )
        request = ("\r\n".join(header_lines) + "\r\n\r\n").encode()
        sock.sendall(request)

        response = http.client.HTTPResponse(sock)
        response.begin()
        body = response.read()
        if response.status >= 400:
            raise HTTPError(url, response.status, response.reason, response.headers, None)
        return body
    finally:
        sock.close()


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
            if proxy_url and urlsplit(proxy_url).scheme == "socks5":
                return _http_get_via_socks5(url, headers, timeout, proxy_url)
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
