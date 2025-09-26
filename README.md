# MCP Final Project – Streamlit Client & Remote MCP Servers

##  Overview
This project implements the **Model Context Protocol (MCP)** without relying on external SDKs.  
Communication is performed directly via **JSON-RPC 2.0** using both **stdio** and **HTTP transports**.  

The system provides:  
- A **Streamlit Web UI** (`ui_web_streamlit.py`) that integrates with multiple MCP servers.  
- Local MCP servers for **Filesystem** and **Git**.  
- A **Remote MCP server** exposing **RSA cryptography** and **Geospatial Maps** tools.  
- Example support for external servers (e.g., **Movies Chatbot MCP**).  

The project demonstrates how an LLM can interact with MCP servers to perform complex workflows using natural language.

---

##  Features
- **Filesystem tools**: read, write, list, delete files.  
- **Git tools**: init, status, commit.  
- **RSA tools**: generate keys, encrypt, decrypt.  
- **Maps tool**: generate dual comparative maps using GeoJSON (e.g., Lake Atitlán 2020 vs 2025).  
- **Extensible architecture**: additional MCP servers can be integrated (e.g., Movies Chatbot).  
- **Streamlit chat interface**: interactive conversation + MCP tool invocations.  
- **Logs**: persistent logs of JSON-RPC traffic and LLM interactions.

---

##  Installation

### 1. Clone the repository
```bash
git clone https://github.com/EJGDLG/proyecto1-redes.git
cd proyecto-mcp-final
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Install official MCP servers (stdio transport)
You need the CLI binaries in your PATH. The official implementations are hosted by the MCP community/Anthropic. Install at least one of these variants:

- Filesystem MCP: `filesystem-mcp`  
- Git MCP: `git-mcp`

> Tip: If installed via Node.js packages, you can expose them with `npx`:  
> - `npx @modelcontextprotocol/server-filesystem`  
> - `npx @modelcontextprotocol/server-git`

### 4. Verify commands exist
```bash
which filesystem-mcp || where filesystem-mcp
which git-mcp         || where git-mcp
```

---

##  Configuration
This repo already includes `app/host/servers.config.json` with entries:
```json
{
  "servers": [
    {"name": "local-complexity", "command": ["python", "-u", "app/mcp_local/server.py"], "transport": "stdio"},
    {"name": "filesystem",       "command": ["filesystem-mcp"], "transport": "stdio", "optional": true},
    {"name": "git",              "command": ["git-mcp"],        "transport": "stdio", "optional": true},
    {"name": "remote-utils",     "command": ["python", "-u", "server_remote.py"], "transport": "http"}
  ]
}
```

---

##  Usage

### Option 1: Run the TUI (terminal)
```bash
# Windows
python -m app.ui_tui

# Linux/Mac
python -m app.ui_tui
```

### Option 2: Run the Web UI (Streamlit)
```bash
streamlit run app/ui_web_streamlit.py
```

If Streamlit does not auto-open your browser, visit:  
- [http://localhost:8501](http://localhost:8501)

---

##  Test Messages

### Filesystem MCP
1. Create file:  
   > "Create a file named `test.txt` with the content 'Hello MCP'."  
   → Calls `filesystem/write_file`.

2. Read file:  
   > "Read the content of `test.txt`."  
   → Calls `filesystem/read_file`.

3. List directory:  
   > "List all files in the current folder."  
   → Calls `filesystem/list_dir`.

4. Delete file:  
   > "Delete `test.txt`."  
   → Calls `filesystem/delete_file`.

### Git MCP
1. Init repo:  
   > "Initialize a Git repository in `./my_repo`."  
   → Calls `git/init`.

2. Status:  
   > "Show the status of the repo in `./my_repo`."  
   → Calls `git/status`.

3. Commit changes:  
   > "Commit all changes in `./my_repo` with message 'Added test.txt'."  
   → Calls `git/commit`.

### RSA & Maps (Remote MCP Server)
1. Generate keys:  
   > "Generate RSA keys with primes between 50 and 100."  

2. Encrypt:  
   > "Encrypt the number 25 with the public key."  

3. Decrypt:  
   > "Decrypt the encrypted number with the private key."  

4. Maps:  
   > "Generate a comparative map of Lake Atitlán between 2020 and 2025."  

---

##  Debugging

Minimal manual commands (sent via chat input if needed):

- List tools
```json
{"server":"filesystem","method":"tools/list"}
```

- Write file
```json
{"server":"filesystem","method":"tools/call","params":{"name":"filesystem/write_file","arguments":{"path":"README_MCP_DEMO.md","content":"Hello MCP"}}}
```

- Git init + commit
```json
{"server":"git","method":"tools/call","params":{"name":"git/init","arguments":{"path":"./demo_repo"}}}
{"server":"git","method":"tools/call","params":{"name":"git/commit","arguments":{"path":"./demo_repo","message":"first commit"}}}
```

---

## Logs
- **LLM interactions**: `logs/llm-YYYYMMDD.jsonl`  
- **MCP client I/O**: `logs/mcp-YYYYMMDD.jsonl` (created automatically on first MCP call)  

---

##  Demo checklist
- [ ] `filesystem` responds to `tools/list`.  
- [ ] Create a file via `tools/call`.  
- [ ] `git` responds to `tools/list`.  
- [ ] Init repo, add, commit via `tools/call`.  
- [ ] RSA keys, encryption/decryption tested.  
- [ ] Comparative map generated.  
- [ ] Logs show JSON-RPC send/recv for each step.  

---

##  Notes
- Keep dependencies updated with:  
  ```bash
  pip install --upgrade -r requirements.txt
  ```
- Streamlit errors/logs will also appear in the terminal where you launched it.
