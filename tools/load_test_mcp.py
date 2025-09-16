
import asyncio, json, time, argparse, random, shlex, sys, csv
from pathlib import Path

def rand_func_source(idx:int)->str:
    n_loops = random.randint(1,3)
    n_ifs = random.randint(1,3)
    body = []
    for i in range(n_loops):
        body.append(f"    for i{i} in range({random.randint(3,15)}):\n        pass\n")
    for j in range(n_ifs):
        body.append(f"    if {random.randint(0,9)} < {random.randint(0,9)}:\n        x={random.randint(0,9)}\n    else:\n        x={random.randint(0,9)}\n")
    return "def f%d(x):\n%s    return x\n" % (idx, "".join(body))

class MCPProc:
    def __init__(self, command:str):
        self.command = command
        self.proc = None
        self.reader = None
        self.writer = None
        self.next_id = 1
        self.pending = {}

    async def start(self):
        args = shlex.split(self.command)
        self.proc = await asyncio.create_subprocess_exec(
            *args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=sys.stderr,
        )
        self.reader = self.proc.stdout
        self.writer = self.proc.stdin
        asyncio.create_task(self._read_loop())
        await self.call("initialize", {"protocolVersion":"2024-08-01"})

    async def _read_loop(self):
        while True:
            line = await self.reader.readline()
            if not line: break
            try:
                msg = json.loads(line.decode())
            except Exception:
                continue
            if "id" in msg and ("result" in msg or "error" in msg):
                fut = self.pending.pop(msg["id"], None)
                if fut and not fut.done():
                    fut.set_result(msg)

    async def call(self, method, params):
        _id = self.next_id; self.next_id += 1
        req = {"jsonrpc":"2.0","id":_id,"method":method,"params":params}
        self.writer.write((json.dumps(req) + "\n").encode())
        await self.writer.drain()
        fut = asyncio.get_event_loop().create_future()
        self.pending[_id] = fut
        resp = await fut
        if "error" in resp:
            raise RuntimeError(resp["error"])
        return resp["result"]

async def worker(mcp:MCPProc, method, tool_name, samples, total):
    while True:
        if total["left"] <= 0: break
        total["left"] -= 1
        idx = total["sent"]; total["sent"] += 1
        src = rand_func_source(idx)
        payload = {"name": tool_name, "arguments": {"code": src}}
        t0 = time.perf_counter()
        try:
            await mcp.call(method, payload)
            ok = True; err = ""
        except Exception as e:
            ok = False; err = str(e)[:200]
        t1 = time.perf_counter()
        samples.append({"ok": ok, "latency_ms": (t1-t0)*1000.0, "error": err})

def summarize(samples, elapsed, total):
    lat = [s["latency_ms"] for s in samples if s["ok"]]
    errors = [s for s in samples if not s["ok"]]
    succ = len(lat)
    def pct(p):
        if not lat: return 0
        idx = max(0, min(len(lat)-1, int((p/100.0)*len(lat))-1))
        return sorted(lat)[idx]
    return {
        "total_requests": total,
        "success": succ,
        "errors": len(errors),
        "success_rate": round(100*succ/max(1,total),2),
        "elapsed_s": round(elapsed,2),
        "throughput_req_per_s": round(total/max(elapsed,1e-6),2),
        "latency_ms": {
            "avg": round(sum(lat)/max(1,len(lat)),2) if lat else 0,
            "p50": round(pct(50),2) if lat else 0,
            "p90": round(pct(90),2) if lat else 0,
            "p95": round(pct(95),2) if lat else 0,
            "p99": round(pct(99),2) if lat else 0
        }
    }

def save_reports(samples, summary):
    logs = Path("logs"); logs.mkdir(parents=True, exist_ok=True)
    (logs/"load_report.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    with open(logs/"load_samples.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ok","latency_ms","error"])
        for s in samples:
            w.writerow([s["ok"], f"{s['latency_ms']:.2f}", s["error"]])

async def main():
    ap = argparse.ArgumentParser(description="Prueba de carga para un servidor MCP por STDIO")
    ap.add_argument("--command", required=True, help="Comando para lanzar el servidor MCP, ej: \"python -u app/mcp_local/server.py\"")
    ap.add_argument("--method", default="tools/call", help="Método JSON-RPC a invocar")
    ap.add_argument("--name", default="code/complexity/analyze", help="Nombre de la herramienta a invocar")
    ap.add_argument("--concurrency", type=int, default=10)
    ap.add_argument("--requests", type=int, default=200)
    args = ap.parse_args()

    mcp = MCPProc(args.command)
    await mcp.start()

    samples = []
    total = {"left": args.requests, "sent": 0}
    tasks = [asyncio.create_task(worker(mcp, args.method, args.name, samples, total)) for _ in range(args.concurrency)]
    t0 = time.perf_counter()
    await asyncio.gather(*tasks)
    elapsed = time.perf_counter() - t0
    summary = summarize(samples, elapsed, args.requests)
    save_reports(samples, summary)
    print(json.dumps(summary, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
