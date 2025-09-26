# filesystem_mcp.py (versión stdio JSON-RPC)
import sys, os, json

TOOLS = [
    {
        "name": "filesystem/write_file",
        "description": "Crea o sobrescribe un archivo con contenido.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"}
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "filesystem/read_file",
        "description": "Lee el contenido de un archivo.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"}
            },
            "required": ["path"]
        }
    },
    {
        "name": "filesystem/list_dir",
        "description": "Lista los archivos en un directorio.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"}
            },
            "required": ["path"]
        }
    },
    {
        "name": "filesystem/delete_file",
        "description": "Elimina un archivo.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"}
            },
            "required": ["path"]
        }
    }
]

def ok(id, result):
    return {"jsonrpc": "2.0", "id": id, "result": result}

def err(id, code, message):
    return {"jsonrpc": "2.0", "id": id, "error": {"code": code, "message": message}}

def handle_call(name, args):
    if name == "filesystem/write_file":
        path, content = args["path"], args["content"]
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return {"content": [{"type": "text", "text": f"Archivo {path} creado"}]}
    if name == "filesystem/read_file":
        path = args["path"]
        if not os.path.exists(path):
            raise FileNotFoundError(f"Archivo {path} no existe")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        return {"content": [{"type": "text", "text": content}]}
    if name == "filesystem/list_dir":
        path = args["path"]
        if not os.path.isdir(path):
            raise NotADirectoryError(f"{path} no es un directorio válido")
        files = os.listdir(path)
        return {"content": [{"type": "json", "data": {"files": files}}]}
    if name == "filesystem/delete_file":
        path = args["path"]
        if not os.path.exists(path):
            raise FileNotFoundError(f"Archivo {path} no existe")
        os.remove(path)
        return {"content": [{"type": "text", "text": f"Archivo {path} eliminado"}]}
    raise ValueError(f"Unknown tool: {name}")

def main():
    for line in sys.stdin:
        try:
            data = json.loads(line)
            mid, method, params = data.get("id"), data.get("method"), data.get("params", {}) or {}
            if method == "initialize":
                print(json.dumps(ok(mid, {"protocolVersion": "2024-08-01", "server": "filesystem"})))
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
