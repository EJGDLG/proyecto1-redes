import asyncio, json, os, sys, time, uuid, subprocess, threading
from pathlib import Path

LOG_DIR = Path("logs"); LOG_DIR.mkdir(parents=True, exist_ok=True)

def jdump(obj): return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))

class MCPProcessClient:
    """
    Cliente MCP muy simple por STDIO:
      - start(): lanza el proceso (command[]) y hace initialize
      - call(method, params): JSON-RPC request y espera result
      - tools_list(): helper para listar herramientas
    Loggea TODO a logs/mcp-YYYYMMDD.jsonl
    """
    def __init__(self, name, command):
        self.name = name
        self.command = command
        self.proc = None
        self.next_id = 1
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
        self.proc = await asyncio.create_subprocess_exec(
            *self.command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=sys.stderr,
        )
        self.reader = self.proc.stdout
        self.writer = self.proc.stdin
        # hilo lector
        asyncio.create_task(self._read_loop())
        # initialize
        return await self.call("initialize", {"protocolVersion": "2024-08-01"})

    async def _read_loop(self):
        # Muy simple: cada línea es un JSON-RPC
        while True:
            line = await self.reader.readline()
            if not line:
                break
            try:
                msg = json.loads(line.decode("utf-8"))
            except Exception as e:
                self._log("recv", {"type": "garbled", "raw": line.decode("utf-8", "ignore")})
                continue
            self._log("recv", {"type": "jsonrpc", "msg": msg})
            if "id" in msg and ("result" in msg or "error" in msg):
                fut = self.pending.pop(msg["id"], None)
                if fut and not fut.done():
                    fut.set_result(msg)

    async def call(self, method, params=None):
        _id = self.next_id; self.next_id += 1
        req = {"jsonrpc": "2.0", "id": _id, "method": method, "params": params or {}}
        data = (jdump(req) + "\n").encode("utf-8")
        self._log("send", {"type": "jsonrpc", "msg": req})
        self.writer.write(data)
        await self.writer.drain()
        fut = asyncio.get_event_loop().create_future()
        self.pending[_id] = fut
        resp = await fut
        if "error" in resp:
            raise RuntimeError(f"MCP error: {resp['error']}")
        return resp["result"]

    async def tools_list(self):
        return await self.call("tools/list", {})

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
                raise

    async def call(self, server, method, params):
        if server not in self.clients:
            raise RuntimeError(f"Server not available: {server}")
        return await self.clients[server].call(method, params)
