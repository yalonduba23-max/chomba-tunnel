# utils/tunnel.py — core tunnel logic (WebSocket/TLS, SSH, HTTP proxy)

import threading
import socket
import ssl
import time
import hashlib
import base64
import os
import struct
from kivy.clock import Clock

try:
    import paramiko  # SSH support
    HAS_PARAMIKO = True
except ImportError:
    HAS_PARAMIKO = False


# ── Simple WebSocket client (no external lib needed for basic frames) ────────

def _ws_handshake(sock, host, path, extra_headers=""):
    key = base64.b64encode(os.urandom(16)).decode()
    headers = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {host}\r\n"
        f"Upgrade: websocket\r\n"
        f"Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        f"Sec-WebSocket-Version: 13\r\n"
    )
    if extra_headers:
        headers += extra_headers.rstrip("\r\n") + "\r\n"
    headers += "\r\n"
    sock.sendall(headers.encode())

    resp = b""
    while b"\r\n\r\n" not in resp:
        chunk = sock.recv(4096)
        if not chunk:
            raise ConnectionError("WS handshake failed — server closed connection")
        resp += chunk

    if b"101" not in resp:
        raise ConnectionError(f"WS upgrade rejected:\n{resp[:300].decode(errors='replace')}")
    return True


def _ws_send_frame(sock, data: bytes):
    """Send a masked binary WebSocket frame."""
    mask = os.urandom(4)
    length = len(data)
    masked = bytes(b ^ mask[i % 4] for i, b in enumerate(data))

    header = b"\x82"  # FIN + binary opcode
    if length < 126:
        header += bytes([0x80 | length])
    elif length < 65536:
        header += bytes([0x80 | 126]) + struct.pack(">H", length)
    else:
        header += bytes([0x80 | 127]) + struct.pack(">Q", length)
    sock.sendall(header + mask + masked)


def _ws_recv_frame(sock) -> bytes:
    """Receive one WebSocket frame (handles fragmentation)."""
    def recv_exact(n):
        buf = b""
        while len(buf) < n:
            chunk = sock.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("Connection closed")
            buf += chunk
        return buf

    header = recv_exact(2)
    opcode = header[0] & 0x0F
    masked = bool(header[1] & 0x80)
    length = header[1] & 0x7F

    if length == 126:
        length = struct.unpack(">H", recv_exact(2))[0]
    elif length == 127:
        length = struct.unpack(">Q", recv_exact(8))[0]

    mask_key = recv_exact(4) if masked else b""
    payload  = recv_exact(length)

    if masked:
        payload = bytes(b ^ mask_key[i % 4] for i, b in enumerate(payload))

    if opcode == 8:   # close frame
        raise ConnectionError("Server sent close frame")
    if opcode == 9:   # ping → send pong
        sock.sendall(b"\x8A\x00")
        return b""

    return payload


# ── Tunnel class ─────────────────────────────────────────────────────────────

class TunnelEngine:

    def __init__(self, log_cb=None, status_cb=None, stats_cb=None):
        self.log_cb    = log_cb    or (lambda msg, level="info": None)
        self.status_cb = status_cb or (lambda s: None)
        self.stats_cb  = stats_cb  or (lambda up, dn: None)

        self._thread   = None
        self._stop_evt = threading.Event()
        self._sock     = None
        self._profile  = {}

        self.bytes_up   = 0
        self.bytes_down = 0
        self._start_time = None

    # ── Public API ────────────────────────────────────────────────────────

    def connect(self, profile: dict):
        if self._thread and self._thread.is_alive():
            self.log("Already connected", "warn")
            return
        self._stop_evt.clear()
        self._profile   = profile
        self.bytes_up   = 0
        self.bytes_down = 0
        self._thread    = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def disconnect(self):
        self._stop_evt.set()
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
        self._set_status("disconnected")
        self.log("Disconnected by user", "info")

    def is_connected(self):
        return self._thread is not None and self._thread.is_alive() and not self._stop_evt.is_set()

    def get_uptime(self):
        if self._start_time:
            secs = int(time.time() - self._start_time)
            h, m, s = secs // 3600, (secs % 3600) // 60, secs % 60
            return f"{h:02d}:{m:02d}:{s:02d}"
        return "00:00:00"

    # ── Internal ──────────────────────────────────────────────────────────

    def log(self, msg, level="info"):
        Clock.schedule_once(lambda dt: self.log_cb(msg, level), 0)

    def _set_status(self, status):
        Clock.schedule_once(lambda dt: self.status_cb(status), 0)

    def _push_stats(self):
        up, dn = self.bytes_up, self.bytes_down
        Clock.schedule_once(lambda dt: self.stats_cb(up, dn), 0)

    def _run(self):
        p    = self._profile
        mode = p.get("mode", "WebSocket")
        reconnect = p.get("reconnect", True)

        while not self._stop_evt.is_set():
            self._set_status("connecting")
            self.log(f"Connecting [{mode}] → {p.get('server')}:{p.get('port')}", "info")
            try:
                if mode == "WebSocket":
                    self._run_websocket(p)
                elif mode == "SSH":
                    self._run_ssh(p)
                elif mode == "HTTP Proxy":
                    self._run_http_proxy(p)
                else:
                    self.log(f"Unknown mode: {mode}", "error")
                    break
            except Exception as e:
                self.log(f"Error: {e}", "error")
                self._set_status("error")

            if not reconnect or self._stop_evt.is_set():
                break

            self.log("Reconnecting in 5 s...", "warn")
            self._start_time = None
            self._stop_evt.wait(5)

        self._set_status("disconnected")

    # ── WebSocket mode ────────────────────────────────────────────────────

    def _run_websocket(self, p):
        host    = p["server"]
        port    = int(p.get("port", 443))
        path    = p.get("ws_path", "/") or "/"
        use_tls = p.get("tls", True)
        sni     = p.get("sni") or host
        payload = p.get("payload", "")

        raw = socket.create_connection((host, port), timeout=10)

        if use_tls:
            ctx = ssl.create_default_context()
            ctx.check_hostname = True
            ctx.verify_mode    = ssl.CERT_REQUIRED
            raw = ctx.wrap_socket(raw, server_hostname=sni)
            self.log(f"TLS OK — cipher: {raw.cipher()[0]}", "info")

        self._sock = raw
        _ws_handshake(raw, sni, path, extra_headers=payload)
        self.log("WebSocket connected ✓", "info")

        self._start_time = time.time()
        self._set_status("connected")

        # Keep-alive loop
        last_ping = time.time()
        while not self._stop_evt.is_set():
            if time.time() - last_ping > 20:
                try:
                    raw.sendall(b"\x89\x00")  # ping frame
                    last_ping = time.time()
                except Exception:
                    break
            self._push_stats()
            time.sleep(1)

    # ── SSH mode ──────────────────────────────────────────────────────────

    def _run_ssh(self, p):
        if not HAS_PARAMIKO:
            self.log("SSH mode needs paramiko (pip install paramiko)", "error")
            return

        host     = p["server"]
        port     = int(p.get("port", 22))
        user     = p.get("ssh_user", "root")
        password = p.get("ssh_pass", "")
        key_path = p.get("ssh_key", "")

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        if key_path and os.path.exists(key_path):
            key = paramiko.RSAKey.from_private_key_file(key_path)
            client.connect(host, port=port, username=user, pkey=key, timeout=10)
        else:
            client.connect(host, port=port, username=user, password=password, timeout=10)

        self.log("SSH connected ✓", "info")
        self._start_time = time.time()
        self._set_status("connected")

        transport = client.get_transport()
        transport.set_keepalive(20)

        while not self._stop_evt.is_set():
            if not transport.is_active():
                raise ConnectionError("SSH transport dropped")
            self._push_stats()
            time.sleep(1)

        client.close()

    # ── HTTP Proxy mode ───────────────────────────────────────────────────

    def _run_http_proxy(self, p):
        host       = p.get("proxy_host") or p["server"]
        port       = int(p.get("proxy_port", 8080))
        payload    = p.get("payload", "")

        raw = socket.create_connection((host, port), timeout=10)
        self._sock = raw

        # Send CONNECT or custom payload
        if payload:
            raw.sendall((payload + "\r\n\r\n").encode())
        else:
            raw.sendall(
                f"CONNECT {p['server']}:{p['port']} HTTP/1.1\r\n"
                f"Host: {p['server']}:{p['port']}\r\n\r\n".encode()
            )

        resp = raw.recv(4096)
        if b"200" not in resp and b"OK" not in resp.upper():
            raise ConnectionError(f"Proxy CONNECT failed: {resp[:100].decode(errors='replace')}")

        self.log("HTTP Proxy tunnel established ✓", "info")
        self._start_time = time.time()
        self._set_status("connected")

        while not self._stop_evt.is_set():
            self._push_stats()
            time.sleep(1)


# ── Human-readable byte sizes ────────────────────────────────────────────────

def fmt_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"
