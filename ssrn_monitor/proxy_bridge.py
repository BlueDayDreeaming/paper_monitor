from __future__ import annotations

import select
import socket
import socketserver
import threading
from dataclasses import dataclass
from urllib.parse import urlsplit

from ssrn_monitor.http import _open_socks5_socket


def _recv_header(client: socket.socket, limit: int = 65536) -> tuple[bytes, bytes]:
    data = b""
    while b"\r\n\r\n" not in data:
        chunk = client.recv(4096)
        if not chunk:
            break
        data += chunk
        if len(data) > limit:
            raise OSError("proxy request header is too large")

    header, separator, rest = data.partition(b"\r\n\r\n")
    if not separator:
        raise OSError("incomplete proxy request header")
    return header + b"\r\n\r\n", rest


def _split_host_port(value: str, default_port: int) -> tuple[str, int]:
    host, separator, port = value.rpartition(":")
    if separator and port.isdigit():
        return host, int(port)
    return value, default_port


def _relay(left: socket.socket, right: socket.socket) -> None:
    sockets = [left, right]
    while sockets:
        readable, _, _ = select.select(sockets, [], [], 30)
        if not readable:
            return
        for source in readable:
            try:
                data = source.recv(65536)
            except OSError:
                return
            if not data:
                return
            target = right if source is left else left
            try:
                target.sendall(data)
            except OSError:
                return


class _ThreadingTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


class _ProxyBridgeHandler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        server: _ProxyBridgeServer = self.server  # type: ignore[assignment]
        client = self.request
        try:
            header, rest = _recv_header(client)
            first_line, *header_lines = header.decode("iso-8859-1").split("\r\n")
            method, target, version = first_line.split(" ", 2)

            if method.upper() == "CONNECT":
                host, port = _split_host_port(target, 443)
                upstream = _open_socks5_socket(server.upstream_proxy_url, host, port, server.timeout)
                try:
                    client.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
                    if rest:
                        upstream.sendall(rest)
                    _relay(client, upstream)
                finally:
                    upstream.close()
                return

            parsed = urlsplit(target)
            if parsed.scheme not in {"http", "https"} or not parsed.hostname:
                raise OSError(f"unsupported proxy request target: {target}")

            port = parsed.port or (443 if parsed.scheme == "https" else 80)
            path = parsed.path or "/"
            if parsed.query:
                path = f"{path}?{parsed.query}"

            upstream = _open_socks5_socket(server.upstream_proxy_url, parsed.hostname, port, server.timeout)
            try:
                rewritten = [f"{method} {path} {version}"]
                rewritten.extend(line for line in header_lines if line)
                upstream.sendall(("\r\n".join(rewritten) + "\r\n\r\n").encode("iso-8859-1") + rest)
                _relay(client, upstream)
            finally:
                upstream.close()
        except Exception:
            try:
                client.sendall(b"HTTP/1.1 502 Bad Gateway\r\nConnection: close\r\n\r\n")
            except OSError:
                pass


class _ProxyBridgeServer(_ThreadingTCPServer):
    def __init__(self, upstream_proxy_url: str, timeout: int) -> None:
        self.upstream_proxy_url = upstream_proxy_url
        self.timeout = timeout
        super().__init__(("127.0.0.1", 0), _ProxyBridgeHandler)


@dataclass(slots=True)
class ProxyBridge:
    upstream_proxy_url: str
    timeout: int = 30
    _server: _ProxyBridgeServer | None = None
    _thread: threading.Thread | None = None

    def __enter__(self) -> "ProxyBridge":
        self.start()
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def start(self) -> None:
        if self._server:
            return
        self._server = _ProxyBridgeServer(self.upstream_proxy_url, self.timeout)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def close(self) -> None:
        if not self._server:
            return
        self._server.shutdown()
        self._server.server_close()
        if self._thread:
            self._thread.join(timeout=5)
        self._server = None
        self._thread = None

    def playwright_proxy_config(self) -> dict[str, str]:
        if not self._server:
            raise RuntimeError("ProxyBridge must be started before building config")
        host, port = self._server.server_address
        return {"server": f"http://{host}:{port}"}
