"""Real MTProto proxy tester (no Telegram account needed).

For every proxy we do a *full* protocol handshake, not just a TCP connect:

1. TCP connect                      -> connect latency
2. fake-TLS ClientHello / ServerHello with HMAC(secret) verification
   (only for `ee` secrets) — proves the secret is right.
3. Obfuscated2 init packet (AES-CTR keyed from the secret), then an
   unencrypted MTProto `req_pq_multi` to Telegram DC2 through the proxy.
   A valid `resPQ` with our nonce echoed back proves the proxy really
   relays traffic to Telegram  -> handshake latency (ping_ms)
4. Optional throughput probe: pipeline N `req_pq_multi` requests and
   measure request/response bytes over time -> up/down KB/s. These are
   *relative* numbers (MTProto has no bulk download without an auth key)
   but they rank proxies consistently.

Everything is pure asyncio + `cryptography`; one coroutine per proxy.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import os
import struct
import time
from dataclasses import dataclass, field

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from .parser import Proxy

PROTO_INTERMEDIATE = b"\xee\xee\xee\xee"
PROTO_PADDED = b"\xdd\xdd\xdd\xdd"
REQ_PQ_MULTI = 0xBE7E8EF1
RES_PQ = 0x05162463
TLS_CLIENT_HELLO_HEAD = b"\x16\x03\x01\x02\x00\x01\x00\x01\xfc\x03\x03"
_BAD_FIRST_WORDS = {b"HEAD", b"POST", b"GET ", b"OPTI", b"\xdd\xdd\xdd\xdd", b"\xee\xee\xee\xee", b"\x16\x03\x01\x02", b"PVrG"}


@dataclass
class TestResult:
    ok: bool
    connect_ms: int | None = None
    ping_ms: int | None = None
    down_kbps: float | None = None
    up_kbps: float | None = None
    error: str = ""
    details: dict = field(default_factory=dict)


# ----------------------------------------------------------------- crypto
class _Obfuscator:
    """Obfuscated2 stream: AES-256-CTR both directions."""

    def __init__(self, secret: bytes, dc: int, proto: bytes):
        while True:
            init = bytearray(os.urandom(64))
            if init[0] == 0xEF or bytes(init[:4]) in _BAD_FIRST_WORDS or init[4:8] == b"\0\0\0\0":
                continue
            break
        init[56:60] = proto
        init[60:62] = struct.pack("<h", dc)
        key_iv = bytes(init[8:56])
        enc_key = hashlib.sha256(key_iv[:32] + secret).digest()
        enc_iv = key_iv[32:48]
        rev = key_iv[::-1]
        dec_key = hashlib.sha256(rev[:32] + secret).digest()
        dec_iv = rev[32:48]
        self._enc = Cipher(algorithms.AES(enc_key), modes.CTR(enc_iv)).encryptor()
        self._dec = Cipher(algorithms.AES(dec_key), modes.CTR(dec_iv)).decryptor()
        encrypted = self._enc.update(bytes(init))
        self.init_packet = bytes(init[:56]) + encrypted[56:64]

    def encrypt(self, data: bytes) -> bytes:
        return self._enc.update(data)

    def decrypt(self, data: bytes) -> bytes:
        return self._dec.update(data)


def _frame(payload: bytes, padded: bool) -> bytes:
    if padded:
        payload += os.urandom(int.from_bytes(os.urandom(1), "little") % 16)
    return struct.pack("<I", len(payload)) + payload


_last_msg_id = 0


def _req_pq_multi() -> tuple[bytes, bytes]:
    global _last_msg_id
    nonce = os.urandom(16)
    msg_id = int(time.time() * (1 << 32)) & ~3
    if msg_id <= _last_msg_id:
        msg_id = _last_msg_id + 4
    _last_msg_id = msg_id
    body = struct.pack("<I", REQ_PQ_MULTI) + nonce
    msg = b"\0" * 8 + struct.pack("<q", msg_id) + struct.pack("<I", len(body)) + body
    return msg, nonce


def _build_client_hello(secret: bytes, domain: str) -> bytes:
    """517-byte Chrome-like ClientHello with HMAC(secret) in the random field."""
    sni_host = domain.encode() or b"www.google.com"
    session_id = os.urandom(32)
    ciphers = bytes.fromhex(
        "130113021303c02bc02fc02cc030cca9cca8c013c014009c009d002f0035")
    grease = b"\x2a\x2a"
    ciphers = grease + ciphers
    ext = b""
    ext += grease + b"\x00\x00"                                              # GREASE
    sni = b"\x00" + struct.pack(">H", len(sni_host)) + sni_host
    sni = struct.pack(">H", len(sni)) + sni
    ext += b"\x00\x00" + struct.pack(">H", len(sni)) + sni                   # server_name
    ext += b"\x00\x17\x00\x00"                                              # extended_master_secret
    ext += b"\xff\x01\x00\x01\x00"                                          # renegotiation_info
    ext += b"\x00\x0a\x00\x0a\x00\x08" + grease + b"\x00\x1d\x00\x17\x00\x18"  # supported_groups
    ext += b"\x00\x0b\x00\x02\x01\x00"                                      # ec_point_formats
    ext += b"\x00\x23\x00\x00"                                              # session_ticket
    ext += b"\x00\x10\x00\x0e\x00\x0c\x02\x68\x32\x08\x68\x74\x74\x70\x2f\x31\x2e\x31"  # ALPN
    ext += b"\x00\x05\x00\x05\x01\x00\x00\x00\x00"                          # status_request
    ext += b"\x00\x0d\x00\x12\x00\x10\x04\x03\x08\x04\x04\x01\x05\x03\x08\x05\x05\x01\x08\x06\x06\x01"
    ext += b"\x00\x12\x00\x00"                                              # SCT
    ext += b"\x00\x33\x00\x2b\x00\x29" + grease + b"\x00\x01\x00" + b"\x00\x1d\x00\x20" + os.urandom(32)  # key_share
    ext += b"\x00\x2d\x00\x02\x01\x01"                                      # psk_key_exchange_modes
    ext += b"\x00\x2b\x00\x0b\x0a" + grease + b"\x03\x04\x03\x03\x03\x02\x03\x01"  # supported_versions
    ext += b"\x00\x1b\x00\x03\x02\x00\x02"                                  # compress_certificate
    ext += grease + b"\x00\x01\x00"                                         # GREASE
    body_wo_padding = (b"\x03\x03" + b"\0" * 32 + b"\x20" + session_id +
                       struct.pack(">H", len(ciphers)) + ciphers + b"\x01\x00")
    # padding extension to reach 508-byte handshake body
    cur = len(body_wo_padding) + 2 + len(ext)
    pad_len = 508 - cur - 4
    if pad_len < 0:
        raise ValueError("client hello too big")
    ext += b"\x00\x15" + struct.pack(">H", pad_len) + b"\0" * pad_len
    body = body_wo_padding + struct.pack(">H", len(ext)) + ext
    assert len(body) == 508, len(body)
    hello = TLS_CLIENT_HELLO_HEAD[:9] + body  # 0x16 0301 0200 01 0001fc + body(starts with 0303)
    assert len(hello) == 517, len(hello)
    digest = hmac.new(secret, hello, hashlib.sha256).digest()
    ts = int(time.time()).to_bytes(4, "little")
    digest = digest[:28] + bytes(a ^ b for a, b in zip(digest[28:], ts))
    return hello[:11] + digest + hello[43:], digest


async def _read_exact(reader: asyncio.StreamReader, n: int, timeout: float) -> bytes:
    return await asyncio.wait_for(reader.readexactly(n), timeout)


async def _tls_handshake(reader, writer, secret: bytes, domain: str, timeout: float) -> None:
    hello, client_digest = _build_client_hello(secret, domain)
    writer.write(hello)
    await writer.drain()
    hdr = await _read_exact(reader, 5, timeout)
    if hdr[:3] != b"\x16\x03\x03":
        raise ConnectionError("not a TLS ServerHello")
    sh_len = struct.unpack(">H", hdr[3:5])[0]
    server_hello = hdr + await _read_exact(reader, sh_len, timeout)
    ccs = await _read_exact(reader, 6, timeout)
    if ccs != b"\x14\x03\x03\x00\x01\x01":
        raise ConnectionError("no ChangeCipherSpec")
    app_hdr = await _read_exact(reader, 5, timeout)
    if app_hdr[:3] != b"\x17\x03\x03":
        raise ConnectionError("no app-data record")
    app_len = struct.unpack(">H", app_hdr[3:5])[0]
    app = await _read_exact(reader, app_len, timeout)
    full = server_hello + ccs + app_hdr + app
    srv_digest = full[11:43]
    zeroed = full[:11] + b"\0" * 32 + full[43:]
    expected = hmac.new(secret, client_digest + zeroed, hashlib.sha256).digest()
    if not hmac.compare_digest(srv_digest, expected):
        raise ConnectionError("fake-TLS digest mismatch (wrong secret or not an MTProxy)")


class _TlsWrap:
    """Wraps the obfuscated stream into TLS application-data records."""

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, timeout: float):
        self.r, self.w, self.t = reader, writer, timeout
        self._buf = b""

    def write(self, data: bytes) -> None:
        while data:
            chunk, data = data[:16384], data[16384:]
            self.w.write(b"\x17\x03\x03" + struct.pack(">H", len(chunk)) + chunk)

    async def drain(self):
        await self.w.drain()

    async def readexactly(self, n: int) -> bytes:
        while len(self._buf) < n:
            hdr = await _read_exact(self.r, 5, self.t)
            if hdr[0] not in (0x17, 0x14):
                raise ConnectionError("bad TLS record")
            ln = struct.unpack(">H", hdr[3:5])[0]
            data = await _read_exact(self.r, ln, self.t)
            if hdr[0] == 0x17:
                self._buf += data
        out, self._buf = self._buf[:n], self._buf[n:]
        return out


class _Plain:
    def __init__(self, reader, writer, timeout):
        self.r, self.w, self.t = reader, writer, timeout

    def write(self, d: bytes):
        self.w.write(d)

    async def drain(self):
        await self.w.drain()

    async def readexactly(self, n: int) -> bytes:
        return await _read_exact(self.r, n, self.t)


async def _read_frame(stream, obf: _Obfuscator) -> bytes:
    raw_len = obf.decrypt(await stream.readexactly(4))
    ln = struct.unpack("<I", raw_len)[0]
    if ln > 1 << 20 or ln < 4:
        raise ConnectionError(f"bad frame length {ln}")
    return obf.decrypt(await stream.readexactly(ln))


def _check_res_pq(payload: bytes, nonce: bytes) -> bool:
    if len(payload) < 20 + 4 + 16:
        if len(payload) == 4:
            raise ConnectionError(f"DC error {struct.unpack('<i', payload)[0]}")
        return False
    body = payload[20:]
    return struct.unpack("<I", body[:4])[0] == RES_PQ and body[4:20] == nonce


async def test_proxy(proxy: Proxy, timeout: float = 4.0, speed: bool = False,
                     speed_requests: int = 48, speed_timeout: float = 8.0) -> TestResult:
    """Full handshake test. Set `speed=True` for the throughput probe."""
    secret = proxy.raw_secret
    stype = proxy.secret_type
    padded = stype in ("padded", "faketls")
    proto = PROTO_PADDED if padded else PROTO_INTERMEDIATE
    t0 = time.perf_counter()
    writer = None
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(proxy.host, proxy.port), timeout)
        connect_ms = int((time.perf_counter() - t0) * 1000)
        if stype == "faketls":
            await _tls_handshake(reader, writer, secret, proxy.tls_domain, timeout)
            stream = _TlsWrap(reader, writer, timeout)
        else:
            stream = _Plain(reader, writer, timeout)
        obf = _Obfuscator(secret, dc=2, proto=proto)
        msg, nonce = _req_pq_multi()
        stream.write(obf.init_packet + obf.encrypt(_frame(msg, padded)))
        await stream.drain()
        t1 = time.perf_counter()
        payload = await asyncio.wait_for(_read_frame(stream, obf), timeout)
        ping_ms = int((time.perf_counter() - t1) * 1000)
        if not _check_res_pq(payload, nonce):
            return TestResult(False, connect_ms, None, error="unexpected DC reply")
        res = TestResult(True, connect_ms, ping_ms, details={"type": stype})
        if speed:
            down, up = await _throughput(stream, obf, padded, speed_requests, speed_timeout)
            res.down_kbps, res.up_kbps = down, up
        return res
    except asyncio.TimeoutError:
        return TestResult(False, error="timeout")
    except (asyncio.IncompleteReadError, ConnectionError, OSError) as e:
        return TestResult(False, error=type(e).__name__ + (f": {e}" if str(e) else ""))
    except Exception as e:  # noqa: BLE001
        return TestResult(False, error=f"{type(e).__name__}: {e}")
    finally:
        if writer is not None:
            writer.close()
            try:
                await asyncio.wait_for(writer.wait_closed(), 1)
            except Exception:  # noqa: BLE001
                pass


async def _throughput(stream, obf, padded: bool, n: int, timeout: float) -> tuple[float, float]:
    """Sequential req_pq_multi round-trips (Telegram answers one unencrypted
    request at a time). Returns (down_kbps, up_kbps) — relative throughput
    numbers that rank proxies consistently."""
    sent = received = 0
    up_time = down_time = 0.0
    t_start = time.perf_counter()
    deadline = t_start + timeout
    got = 0
    for _ in range(n):
        if time.perf_counter() >= deadline:
            break
        msg, nonce = _req_pq_multi()
        fr = _frame(msg, padded)
        t0 = time.perf_counter()
        stream.write(obf.encrypt(fr))
        await stream.drain()
        t1 = time.perf_counter()
        try:
            payload = await asyncio.wait_for(_read_frame(stream, obf), max(0.1, deadline - time.perf_counter()))
        except asyncio.TimeoutError:
            break
        t2 = time.perf_counter()
        if not _check_res_pq(payload, nonce):
            break
        sent += len(fr)
        received += len(payload) + 4
        up_time += (t1 - t0) + (t2 - t1) / 2
        down_time += (t2 - t1) / 2
        got += 1
    if got == 0:
        return 0.0, 0.0
    down_kbps = round(received / 1024 / max(down_time, 1e-3), 2)
    up_kbps = round(sent / 1024 / max(up_time, 1e-3), 2)
    return down_kbps, up_kbps
