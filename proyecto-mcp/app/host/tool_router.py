from pydantic import BaseModel, Field

# Esquema de la tool que verá el modelo
class McpCallArgs(BaseModel):
    server: str = Field(..., description="Nombre del servidor MCP a usar.")
    method: str = Field(..., description="Método MCP, p.ej. 'tools/call'.")
    params: dict = Field(default_factory=dict, description="Parámetros del método.")

OPENAI_TOOLS = [{
    "type": "function",
    "function": {
        "name": "mcp_call",
        "description": "Invoca un método MCP (JSON-RPC) en el servidor elegido.",
        "parameters": {
            "type": "object",
            "properties": {
                "server": {"type": "string"},
                "method": {"type": "string"},
                "params": {"type": "object"}
            },
            "required": ["server", "method"]
        }
    }
}]
