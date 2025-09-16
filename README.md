
# Proyecto MCP – Versión Final (Host + Servidor Local + Prueba de Carga)

Incluye host en consola (OpenAI + tools), servidor MCP local (complejidad ciclomática),
prueba de carga y logs.

## Instalación
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env
```
## Host
```bash
python -m app.host.main
```
## Servidor solo
```bash
scripts\run_server.bat   # Windows
bash scripts/run_server.sh # Linux/Mac
```
## Prueba de carga
```bash
scripts\run_loadtest.bat
bash scripts/run_loadtest.sh
```
