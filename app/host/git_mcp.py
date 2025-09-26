# git_mcp.py (versión stdio)
import sys, json, subprocess, os

TOOLS = [
    {
        "name": "git/init",
        "description": "Inicializa un repositorio Git en un directorio.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"]
        }
    },
    {
        "name": "git/status",
        "description": "Devuelve el estado del repositorio.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"]
        }
    },
    {
        "name": "git/commit",
        "description": "Hace commit de cambios con un mensaje.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "message": {"type": "string"}
            },
            "required": ["path", "message"]
        }
    }
]

def ok(id, result):
    return {"jsonrpc": "2.0", "id": id, "result": result}

def err(id, code, message):
    return {"jsonrpc": "2.0", "id": id, "error": {"code": code, "message": message}}

def run_git_command(path, args):
    result = subprocess.run(["git", "-C", path] + args, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())
    return result.stdout.strip()

def handle_call(name, args):
    if name == "git/init":
        path = args["path"]
        os.makedirs(path, exist_ok=True)
        return {"content": [{"type": "text", "text": run_git_command(path, ["init"])}]}
    if name == "git/status":
        path = args["path"]
        return {"content": [{"type": "text", "text": run_git_command(path, ["status", "--short", "--branch"])}]}
    if name == "git/commit":
        path, msg = args["path"], args["message"]
        run_git_command(path, ["add", "."])
        return {"content": [{"type": "text", "text": run_git_command(path, ["commit", "-m", msg])}]}
    raise ValueError(f"Unknown tool: {name}")

def main():
    for line in sys.stdin:
        try:
            data = json.loads(line)
            mid, method, params = data.get("id"), data.get("method"), data.get("params", {}) or {}
            if method == "initialize":
                print(json.dumps(ok(mid, {"protocolVersion": "2024-08-01", "server": "git"})))
                sys.stdout.flush()
            elif method == "tools/list":
                print(json.dumps(ok(mid, {"tools": TOOLS})))
                sys.stdout.flush()
            elif method == "tools/call":
                name, args = params.get("name"), params.get("arguments", {}) or {}
                try:
                    result = handle_call(name, args)
                    print(json.dumps(ok(mid, result)))
                except Exception as e:
                    print(json.dumps(err(mid, -32000, str(e))))
                sys.stdout.flush()
            else:
                print(json.dumps(err(mid, -32601, f"Method not found: {method}")))
                sys.stdout.flush()
        except Exception as e:
            print(json.dumps(err(None, -32700, f"Parse error: {e}")))
            sys.stdout.flush()

if __name__ == "__main__":
    main()
