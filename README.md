## Install official MCP servers (stdio transport)
You need the CLI binaries in your PATH. The official implementations are hosted by the MCP community/Anthropic. Install at least one of these variants:

- Filesystem MCP: `filesystem-mcp`
- Git MCP: `git-mcp`

> Tip: If you installed via Node.js packages, expose them with `npx`:
> - `npx @modelcontextprotocol/server-filesystem`
> - `npx @modelcontextprotocol/server-git`

## Verify commands exist
```bash
which filesystem-mcp || where filesystem-mcp
which git-mcp         || where git-mcp
```

## servers.config.json (already present)
This repo already includes `app/host/servers.config.json` with entries:
```json
{
  "servers": [
    {"name": "local-complexity", "command": ["python", "-u", "app/mcp_local/server.py"], "transport": "stdio"},
    {"name": "filesystem",       "command": ["filesystem-mcp"], "transport": "stdio", "optional": true},
    {"name": "git",              "command": ["git-mcp"],        "transport": "stdio", "optional": true}
  ]
}
```

## Run the Host (TUI) and test
```bash
# Windows
python -m app.ui_tui
# Linux/Mac
python -m app.ui_tui
```

Now type a prompt such as:
> List the tools on the `filesystem` server and then create a file named `README_MCP_DEMO.md` with the content "Hola MCP". Use the `mcp_call` tool. After that, initialize a Git repo under `./demo_repo`, add the file, and commit with the message "primer commit".

The model is configured to use function-calling with the tool `mcp_call`. It should produce a sequence of `tools/list` followed by `tools/call` JSON-RPC calls to the `filesystem` and `git` servers, respectively.

## Minimal manual commands (for debugging)
If you prefer to trigger the calls explicitly via chat:

1) List tools
```json
{"server":"filesystem","method":"tools/list"}
```
2) Create a file (replace `TOOL_NAME` with the one that writes files from the list)
```json
{"server":"filesystem","method":"tools/call","params":{"name":"TOOL_NAME","arguments":{"path":"README_MCP_DEMO.md","content":"Hola MCP"}}}
```
3) Git init, add, commit (use the tool names returned by `git` server `tools/list`)
```json
{"server":"git","method":"tools/call","params":{"name":"GIT_INIT","arguments":{"path":"./demo_repo"}}}
{"server":"git","method":"tools/call","params":{"name":"GIT_ADD","arguments":{"path":"README_MCP_DEMO.md"}}}
{"server":"git","method":"tools/call","params":{"name":"GIT_COMMIT","arguments":{"message":"primer commit"}}}
```

## Logs
- LLM interactions: `logs/llm-YYYYMMDD.jsonl`
- MCP client I/O: `logs/mcp-YYYYMMDD.jsonl` (auto-created when the first MCP call happens)

## Demo checklist to satisfy rubric item 2
- [ ] `filesystem` responds to `tools/list`
- [ ] Create file via `tools/call`
- [ ] `git` responds to `tools/list`
- [ ] Init repo, add, commit via `tools/call`
- [ ] Logs show JSON-RPC send/recv for each step

##  Instalación

1. **Clonar o descargar el repositorio**  
   ```bash
   git clone https://github.com/EJGDLG/proyecto1-redes.git
   cd proyecto-mcp-final

---
## Instalar dependencias
pip install -r requirements.txt

---
## Uso
1. Ejecutar la interfaz TUI
python main.py --tui

2. Ejecutar la interfaz web con Streamlit
streamlit run app/web/streamlit_app.py

---
## Funcionalidades

Pendiente

## mensajes de prueba
- Flujo integrado (todo junto)

Crear archivo

1. Crea un archivo llamado test.txt con el contenido "Hola MCP".


→ Llama filesystem/write_file

Leer archivo
2. 
Lee el contenido de test.txt.


→ Llama filesystem/read_file

Listar directorio

3. Muéstrame todos los archivos en la carpeta actual.


→ Llama filesystem/list_dir

Eliminar archivo

4.Borra el archivo test.txt.


→ Llama filesystem/delete_file

🔧 Pruebas para Git (cuando ya tengas git_mcp.py en stdio)

Inicializar repo

1. Inicializa un repositorio Git en la carpeta ./mi_repo


→ Llama git/init

Ver estado

2. Dame el estado del repositorio en ./mi_repo


→ Llama git/status

Commit cambios

3. Haz commit en ./mi_repo con el mensaje "Se agregó test.txt".

- RCA 

1. Genera llaves RSA con primos entre 50 y 100.

2. Encripta el número 25 con la clave pública generada.

3. Desencripta el número cifrado con la clave privada.

4. Genera un mapa comparativo del lago Atitlán entre 2020 y 2025 y dime la ruta del HTML.

## Notas

- Si Streamlit no abre el navegador automáticamente, accede manualmente a URL.

- Los logs y errores se registran en la terminal o consola de Streamlit.

- Se recomienda mantener las dependencias actualizadas con: