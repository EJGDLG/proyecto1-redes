# app/host/mcp_client.py
import sys, json, time, threading, subprocess, asyncio, itertools
from pathlib import Path

# http (para servidores remotos)
try:
    import httpx
except Exception:
    httpx = None

LOG_DIR = Path("logs"); LOG_DIR.mkdir(parents=True, exist_ok=True)

def jdump(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))

# ------------------------ Cliente por proceso (stdio) ------------------------
class MCPProcessClient:
    def __init__(self, name, command):
        self.name = name
        self.command = command
        self.proc = None
        self.pending = {}
        self.reader = None
        self.writer = None
        self.log_path = LOG_DIR / f"mcp-{time.strftime('%Y%m%d')}.jsonl"
        self._lock = threading.Lock()

    def _log(self, direction, payload):
        entry = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "server": self.name,
            "direction": direction,
            **payload
        }
        with self._lock:
            with self.log_path.open("a", encoding="utf-8") as f:
                f.write(jdump(entry) + "\n")

    async def start(self):
        # Lanzar proceso (stdio)
        self.proc = subprocess.Popen(
            self.command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        self.reader = self.proc.stdout
        self.writer = self.proc.stdin

        # Hilo lector de stdout (una línea = un JSON-RPC)
        threading.Thread(target=self._read_loop_sync, daemon=True).start()
        return {"ok": True, "msg": f"Servidor {self.name} iniciado (stdio)"}

    def _read_loop_sync(self):
        for line in self.reader:
            try:
                msg = json.loads(line.strip())
            except Exception:
                self._log("recv", {"type": "garbled", "raw": line})
                continue
            self._log("recv", {"type": "jsonrpc", "msg": msg})
            if "id" in msg and ("result" in msg or "error" in msg):
                fut = self.pending.pop(msg["id"], None)
                if fut and not fut.done():
                    fut.set_result(msg)

    async def call(self, method, params=None):
        _id = len(self.pending) + 1
        req = {"jsonrpc": "2.0", "id": _id, "method": method, "params": params or {}}
        data = (jdump(req) + "\n")
        self._log("send", {"type": "jsonrpc", "msg": req})

        self.writer.write(data)
        self.writer.flush()

        loop = asyncio.get_event_loop()
        fut = loop.create_future()
        self.pending[_id] = fut
        resp = await fut
        if "error" in resp:
            raise RuntimeError(f"MCP error: {resp['error']}")
        return resp.get("result", resp)

    async def stop(self):
        try:
            if self.proc and self.proc.poll() is None:
                self.proc.terminate()
        except Exception:
            pass

# ------------------------ Cliente HTTP (servidor remoto) ---------------------
class MCPHttpClient:
    def __init__(self, name, url):
        self.name = name
        self.url = url.rstrip("/")
        self.session = None
        self._id = itertools.count(1)
        self.log_path = LOG_DIR / f"mcp-{time.strftime('%Y%m%d')}.jsonl"

    def _log(self, direction, payload):
        entry = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "server": self.name,
            "direction": direction,
            **payload
        }
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(jdump(entry) + "\n")

    async def start(self):
        if httpx is None:
            raise RuntimeError("Falta httpx. Instala con: pip install httpx")
        self.session = httpx.AsyncClient(timeout=30.0)
        return {"ok": True, "msg": f"Servidor {self.name} listo (http: {self.url})"}

    async def call(self, method, params=None):
        rid = next(self._id)
        req = {"jsonrpc": "2.0", "id": rid, "method": method, "params": params or {}}
        self._log("send", {"type": "jsonrpc", "http_url": self.url, "msg": req})
        resp = await self.session.post(self.url + "/", json=req)
        data = resp.json()
        self._log("recv", {"type": "jsonrpc", "http_url": self.url, "msg": data})
        if "error" in data:
            raise RuntimeError(f"MCP error: {data['error']}")
        return data.get("result", data)

    async def stop(self):
        try:
            if self.session:
                await self.session.aclose()
        except Exception:
            pass

# ------------------------------ Manager --------------------------------------
class MCPClientManager:
    def __init__(self, cfg):
        self.cfg = cfg
        self.clients = {}

    async def start_all(self):
        for s in self.cfg.get("servers", []):
            try:
                transport = s.get("transport", "stdio")
                if transport == "http":
                    client = MCPHttpClient(s["name"], s["url"])
                else:
                    client = MCPProcessClient(s["name"], s["command"])
                await client.start()
                self.clients[s["name"]] = client
            except Exception as e:
                if s.get("optional"):
                    # opcional: no detener todo si falla
                    continue
                raise RuntimeError(f"No se pudo iniciar el servidor {s.get('name')}: {e}")

    async def stop_all(self):
        for c in list(self.clients.values()):
            try:
                if hasattr(c, "stop"):
                    await c.stop()
            except Exception:
                pass

    async def call(self, server, method, params):
        if server not in self.clients:
            raise RuntimeError(f"Server not available: {server}")
        return await self.clients[server].call(method, params)
