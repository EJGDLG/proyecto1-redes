from pydantic import BaseModel, Field

class McpCallArgs(BaseModel):
    server: str = Field(..., description="Nombre del servidor MCP a usar.")
    method: str = Field(..., description="Método MCP, siempre 'tools/call'.")
    params: dict = Field(
        default_factory=dict,
        description=(
            "Parámetros del método. "
            "Siempre debe incluir:\n"
            "  - name: nombre exacto de la herramienta disponible.\n"
            "  - arguments: diccionario con los parámetros requeridos por esa herramienta."
        )
    )

OPENAI_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "mcp_call",
            "description": (
                "Llama a un servidor MCP.\n\n"
                "📂 Filesystem tools:\n"
                "- filesystem/write_file: argumentos = { 'path': str, 'content': str }\n"
                "- filesystem/read_file: argumentos = { 'path': str }\n"
                "- filesystem/list_dir: argumentos = { 'path': str }\n"
                "- filesystem/delete_file: argumentos = { 'path': str }\n\n"
                "🌿 Git tools:\n"
                "- git/init: argumentos = { 'path': str }\n"
                "- git/status: argumentos = { 'path': str }\n"
                "- git/commit: argumentos = { 'path': str, 'message': str }\n\n"
                "🔐 RSA tools (remote-utils):\n"
                "- rsa/generate_keys: argumentos = { 'rango_inferior': int, 'rango_superior': int }\n"
                "- rsa/encrypt: argumentos = { 'mensaje': int, 'e': int, 'n': int }\n"
                "- rsa/decrypt: argumentos = { 'mensaje_cifrado': int, 'd': int, 'n': int }\n\n"
                "🗺️ Maps tools (remote-utils):\n"
                "- maps/dualmap: argumentos = { 'lake': 'Atitlan'|'Amatitlan', 'period_a': str, 'period_b': str }\n\n"
                "Siempre usa el nombre exacto de la tool y los argumentos correctos."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "server": {
                        "type": "string",
                        "enum": ["filesystem", "git", "remote-utils"]
                    },
                    "method": {
                        "type": "string",
                        "enum": ["tools/call"]
                    },
                    "params": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "arguments": {"type": "object"}
                        },
                        "required": ["name", "arguments"]
                    }
                },
                "required": ["server", "method", "params"]
            }
        }
    }
]
