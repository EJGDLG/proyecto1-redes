# Proyecto MCP – Host + Servidor Local + OpenAI

## Requisitos
- Python 3.11+
- Clave OpenAI (variable `OPENAI_API_KEY`)
- Opcional: servidores MCP oficiales (filesystem, git) si deseas integrarlos

## Setup
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env   # (o crea .env) y pega tu OPENAI_API_KEY
