"""Extract MTProto proxies from arbitrary text/HTML/JSON.

Recognised forms:
    tg://proxy?server=HOST&port=PORT&secret=SECRET
    https://t.me/proxy?server=HOST&port=PORT&secret=SECRET  (also http, telegram.me, telegram.dog)
    JSON objects with host/server, port, secret keys
    HOST:PORT:SECRET   (tab/colon separated plain lists)

Secrets:
    32 hex          plain
    dd + 32 hex     padded ("dd" secure)
    ee + 32 hex + domain-hex   fake-TLS   (also base64url encoded variant starting with 7)
"""
from __future__ import annotations

import base64
import binascii
import html
import json
import re
from dataclasses import dataclass
from urllib.parse import parse_qs, unquote, urlparse

_URL_RE = re.compile(
    r"(?:tg:\/\/proxy|https?:\/\/(?:t|telegram)\.(?:me|dog)\/proxy)\?[^\s\"'<>\]\)]+",
    re.IGNORECASE,
)
_TRIPLE_RE = re.compile(
    r"(?<![\w.])((?:\d{1,3}\.){3}\d{1,3}|[a-z0-9][a-z0-9\-.]{2,253}\.[a-z]{2,})[:\s]+(\d{2,5})[:\s]+([0-9a-fA-F]{32,}|7[A-Za-z0-9_\-]{20,}=*)",
    re.IGNORECASE,
)
_HEX_RE = re.compile(r"^[0-9a-fA-F]+$")


@dataclass(frozen=True)
class Proxy:
    host: str
    port: int
    secret: str

    @property
    def link(self) -> str:
        return f"https://t.me/proxy?server={self.host}&port={self.port}&secret={self.secret}"

    @property
    def tg_link(self) -> str:
        return f"tg://proxy?server={self.host}&port={self.port}&secret={self.secret}"

    @property
    def secret_type(self) -> str:
        s = self.secret.lower()
        if s.startswith("ee") and len(s) > 34:
            return "faketls"
        if s.startswith("dd") and len(s) == 34:
            return "padded"
        if len(s) == 32:
            return "plain"
        return "unknown"

    @property
    def raw_secret(self) -> bytes:
        """16-byte key used for the handshake."""
        s = self.secret.lower()
        if s.startswith(("ee", "dd")) and len(s) >= 34:
            return bytes.fromhex(s[2:34])
        return bytes.fromhex(s[:32])

    @property
    def tls_domain(self) -> str:
        s = self.secret.lower()
        if s.startswith("ee") and len(s) > 34:
            try:
                return bytes.fromhex(s[34:]).decode("ascii", "ignore")
            except ValueError:
                return ""
        return ""

    def key(self) -> tuple[str, int, str]:
        return (self.host.lower(), self.port, self.secret.lower())


def normalise_secret(secret: str) -> str | None:
    secret = secret.strip()
    if not secret:
        return None
    if _HEX_RE.match(secret):
        s = secret.lower()
        if len(s) == 32 or (s.startswith("dd") and len(s) == 34) or (s.startswith("ee") and len(s) > 34 and len(s) % 2 == 0):
            return s
        return None
    # base64url fake-TLS secret (Telegram desktop exports these)
    try:
        pad = "=" * (-len(secret) % 4)
        raw = base64.urlsafe_b64decode(secret + pad)
        if 17 <= len(raw) <= 300 and raw[0] in (0xEE, 0xDD):
            return raw.hex()
    except (binascii.Error, ValueError):
        pass
    return None


def _valid_host(host: str) -> bool:
    host = host.strip().lower()
    if not host or len(host) > 253:
        return False
    if re.fullmatch(r"(\d{1,3}\.){3}\d{1,3}", host):
        parts = [int(p) for p in host.split(".")]
        return all(0 <= p <= 255 for p in parts) and parts[0] not in (0, 10, 127) and not (parts[0] == 192 and parts[1] == 168) \
            and not (parts[0] == 172 and 16 <= parts[1] <= 31) and not (parts[0] == 169 and parts[1] == 254)
    return bool(re.fullmatch(r"[a-z0-9]([a-z0-9\-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9\-]*[a-z0-9])?)+", host))


def make_proxy(host: str, port: int | str, secret: str) -> Proxy | None:
    try:
        port_i = int(str(port).strip())
    except ValueError:
        return None
    if not (1 <= port_i <= 65535):
        return None
    host = html.unescape(unquote(str(host))).strip().strip("[]").lower()
    if not _valid_host(host):
        return None
    sec = normalise_secret(html.unescape(unquote(str(secret))))
    if not sec:
        return None
    return Proxy(host, port_i, sec)


def parse_link(url: str) -> Proxy | None:
    url = html.unescape(url.strip())
    try:
        q = parse_qs(urlparse(url).query, keep_blank_values=False)
    except ValueError:
        return None
    server = q.get("server", [None])[0]
    port = q.get("port", [None])[0]
    secret = q.get("secret", [None])[0]
    if not (server and port and secret):
        return None
    return make_proxy(server, port, secret)


def _walk_json(obj, out: set[Proxy]) -> None:
    if isinstance(obj, dict):
        host = obj.get("host") or obj.get("server") or obj.get("ip") or obj.get("address")
        port = obj.get("port")
        secret = obj.get("secret")
        if host and port and secret:
            p = make_proxy(host, port, secret)
            if p:
                out.add(p)
        for v in obj.values():
            _walk_json(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _walk_json(v, out)
    elif isinstance(obj, str):
        for p in extract_proxies(obj):
            out.add(p)


def extract_proxies(text: str) -> set[Proxy]:
    """Find every proxy in a blob of text, HTML or JSON."""
    found: set[Proxy] = set()
    if not text:
        return found
    stripped = text.lstrip()
    if stripped[:1] in "[{":
        try:
            _walk_json(json.loads(stripped), found)
            if found:
                return found
        except (json.JSONDecodeError, RecursionError):
            pass
    text = html.unescape(text)
    for m in _URL_RE.finditer(text):
        p = parse_link(m.group(0))
        if p:
            found.add(p)
    for m in _TRIPLE_RE.finditer(text):
        p = make_proxy(m.group(1), m.group(2), m.group(3))
        if p:
            found.add(p)
    return found
