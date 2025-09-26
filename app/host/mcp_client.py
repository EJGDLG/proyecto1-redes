import sys, json, time, threading, subprocess, asyncio, requests
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
        self.proc = subprocess.Popen(
            self.command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        self.reader = self.proc.stdout
        self.writer = self.proc.stdin
        threading.Thread(target=self._read_loop_sync, daemon=True).start()
        return {"ok": True, "msg": f"Servidor {self.name} iniciado"}

    def _read_loop_sync(self):
        for line in self.reader:
            try:
                msg = json.loads(line.strip())
            except Exception:
                self._log("recv", {"type": "garbled", "raw": line})
                print(f"[{self.name}] ⚠️ Mensaje no válido: {line.strip()}", file=sys.stderr)
                continue
            self._log("recv", {"type": "jsonrpc", "msg": msg})
            print(f"[{self.name}] ⬅️ Recibido: {msg}", file=sys.stderr)
            if "id" in msg and ("result" in msg or "error" in msg):
                fut = self.pending.pop(msg["id"], None)
                if fut and not fut.done():
                    fut.set_result(msg)

    async def call(self, method, params=None, timeout=10):
        _id = int(time.time_ns())  # ID único
        req = {"jsonrpc": "2.0", "id": _id, "method": method, "params": params or {}}
        data = (jdump(req) + "\n")
        self._log("send", {"type": "jsonrpc", "msg": req})
        print(f"[{self.name}] ➡️ Enviando: {req}", file=sys.stderr)

        self.writer.write(data)
        self.writer.flush()

        loop = asyncio.get_event_loop()
        fut = loop.create_future()
        self.pending[_id] = fut

        try:
            resp = await asyncio.wait_for(fut, timeout=timeout)
        except asyncio.TimeoutError:
            raise RuntimeError(f"⏳ Timeout esperando respuesta de {self.name} (>{timeout}s)")

        if "error" in resp:
            raise RuntimeError(f"MCP error: {resp['error']}")
        return resp["result"]


# 🚀 Cliente HTTP para servidores remotos
class MCPHttpClient:
    def __init__(self, name, url):
        self.name = name
        self.url = url
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
        return {"ok": True, "msg": f"Cliente HTTP {self.name} listo en {self.url}"}

    async def call(self, method, params=None, timeout=15):
        req = {"jsonrpc": "2.0", "id": int(time.time_ns()), "method": method, "params": params or {}}
        self._log("send", {"type": "jsonrpc", "msg": req})
        print(f"[{self.name}] ➡️ POST {self.url} {req}", file=sys.stderr)
        try:
            r = requests.post(self.url, json=req, timeout=timeout)
            r.raise_for_status()
            msg = r.json()
            self._log("recv", {"type": "jsonrpc", "msg": msg})
            print(f"[{self.name}] ⬅️ Recibido: {msg}", file=sys.stderr)
            if "error" in msg:
                raise RuntimeError(f"MCP error: {msg['error']}")
            return msg["result"]
        except Exception as e:
            raise RuntimeError(f"Error llamando a {self.name}: {e}")


class MCPClientManager:
    def __init__(self, cfg):
        self.cfg = cfg
        self.clients = {}

    async def start_all(self):
        for s in self.cfg["servers"]:
            try:
                if "command" in s:  # stdio
                    client = MCPProcessClient(s["name"], s["command"])
                    await client.start()
                elif "url" in s:  # http
                    client = MCPHttpClient(s["name"], s["url"])
                    await client.start()
                else:
                    raise RuntimeError("Config inválida: falta 'command' o 'url'")
                self.clients[s["name"]] = client
            except Exception as e:
                if s.get("optional"):
                    continue
                raise RuntimeError(f"No se pudo iniciar el servidor {s['name']}: {e}")

    async def call(self, server, method, params):
        if server not in self.clients:
            raise RuntimeError(f"Server not available: {server}")
        return await self.clients[server].call(method, params)
