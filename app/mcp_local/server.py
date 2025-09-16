
import sys, json, ast
from typing import Dict, Any

def jprint(obj): 
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n"); sys.stdout.flush()

def ok(id, result): jprint({"jsonrpc":"2.0","id":id,"result":result})
def err(id, code, message): jprint({"jsonrpc":"2.0","id":id,"error":{"code":code,"message":message}})

def cyclomatic_complexity(node: ast.AST) -> int:
    count = 1
    for n in ast.walk(node):
        if isinstance(n, (ast.If, ast.For, ast.While, ast.With, ast.Try, ast.IfExp, ast.Match)):
            count += 1
        elif isinstance(n, ast.BoolOp):
            count += max(0, len(n.values)-1)
        elif isinstance(n, ast.ExceptHandler):
            count += 1
    return count

def analyze_code(src: str) -> Dict[str, Any]:
    tree = ast.parse(src)
    report = []
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            comp = cyclomatic_complexity(n)
            report.append({
                "name": n.name,
                "lineno": n.lineno,
                "complexity": comp,
                "risk": "low" if comp <= 5 else ("medium" if comp <=10 else "high")
            })
        elif isinstance(n, ast.ClassDef):
            methods = [m for m in n.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))]
            if methods:
                avg = sum(cyclomatic_complexity(m) for m in methods)/len(methods)
            else:
                avg = 1
            report.append({
                "name": f"class {n.name}",
                "lineno": n.lineno,
                "complexity_avg": round(avg,2),
                "risk": "low" if avg <= 5 else ("medium" if avg <=10 else "high")
            })
    return {"summary": report, "total_items": len(report)}

TOOLS = [{
    "name": "code/complexity/analyze",
    "description": "Analiza complejidad ciclomática de un string de código Python.",
    "inputSchema": {
        "type":"object",
        "properties": {
            "code": {"type":"string", "description":"Código fuente Python"}
        },
        "required": ["code"]
    }
}]

def handle_tools_call(params):
    tool = params.get("name")
    if tool == "code/complexity/analyze":
        code = params.get("arguments", {}).get("code","")
        if not isinstance(code, str) or not code.strip():
            raise ValueError("arguments.code must be non-empty string")
        return analyze_code(code)
    raise ValueError(f"Unknown tool {tool}")

def main():
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        try:
            req = json.loads(line)
        except Exception:
            continue
        rid = req.get("id")
        method = req.get("method")
        params = req.get("params", {})

        try:
            if method == "initialize":
                ok(rid, {"protocolVersion":"2024-08-01","server":"local-complexity"})
            elif method == "tools/list":
                ok(rid, {"tools": TOOLS})
            elif method == "tools/call":
                res = handle_tools_call(params)
                ok(rid, {"content": res})
            else:
                err(rid, -32601, f"Method not found: {method}")
        except Exception as e:
            err(rid, -32000, str(e))

if __name__ == "__main__":
    main()
