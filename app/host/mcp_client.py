import sys, json, time, threading, subprocess, asyncio
from pathlib import Path

LOG_DIR = Path("logs"); LOG_DIR.mkdir(parents=True, exist_ok=True)

def jdump(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))

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
        # 🚀 Versión para Windows usando subprocess.Popen
        self.proc = subprocess.Popen(
            self.command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        self.reader = self.proc.stdout
        self.writer = self.proc.stdin

        # Inicia un hilo para leer la salida del servidor
        threading.Thread(target=self._read_loop_sync, daemon=True).start()

        return {"ok": True, "msg": f"Servidor {self.name} iniciado"}

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
        return resp["result"]


class MCPClientManager:
    def __init__(self, cfg):
        self.cfg = cfg
        self.clients = {}

    async def start_all(self):
        for s in self.cfg["servers"]:
            try:
                client = MCPProcessClient(s["name"], s["command"])
                await client.start()
                self.clients[s["name"]] = client
            except Exception as e:
                if s.get("optional"):
                    continue
                raise RuntimeError(f"No se pudo iniciar el servidor {s['name']}: {e}")

    async def call(self, server, method, params):
        if server not in self.clients:
            raise RuntimeError(f"Server not available: {server}")
        return await self.clients[server].call(method, params)
