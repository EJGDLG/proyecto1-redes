# app/ui_web_streamlit.py

# --- FIX de imports, ruta del proyecto y loop para Windows ---
import os, sys, json, time, asyncio, threading
from pathlib import Path

# Añade la raíz del proyecto (…/proyecto-mcp-final) al sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# En Windows, usa loop compatible con subprocess (para MCP por stdio)
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
# --- FIN FIX ---

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

from app.host.mcp_client import MCPClientManager
from app.host.tool_router import OPENAI_TOOLS

load_dotenv()
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# ---------- Utilidades de serialización para logs ----------
from typing import Any

def jsonable(obj: Any):
    """Convierte cualquier objeto (incluyendo pydantic/SDK OpenAI) a algo JSON-serializable."""
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    if isinstance(obj, dict):
        return {k: jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [jsonable(v) for v in obj]
    if hasattr(obj, "model_dump"):
        try:
            return jsonable(obj.model_dump())
        except Exception:
            pass
    if hasattr(obj, "dict"):
        try:
            return jsonable(obj.dict())
        except Exception:
            pass
    return str(obj)

def serialize_tool_calls(tool_calls):
    out = []
    for tc in (tool_calls or []):
        try:
            fn = getattr(tc, "function", None)
            out.append({
                "id": getattr(tc, "id", None),
                "type": getattr(tc, "type", None),
                "function": {
                    "name": getattr(fn, "name", None) if fn else None,
                    "arguments": getattr(fn, "arguments", None) if fn else None,
                }
            })
        except Exception:
            out.append(jsonable(tc))
    return out
# -----------------------------------------------------------

# --------- Runner asíncrono: un loop dedicado en un hilo ----
class AsyncRunner:
    def __init__(self):
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.loop.run_forever, daemon=True)
        self.thread.start()
    def run(self, coro):
        fut = asyncio.run_coroutine_threadsafe(coro, self.loop)
        return fut.result()
    def stop(self):
        try:
            self.loop.call_soon_threadsafe(self.loop.stop)
            self.thread.join(timeout=2)
        except Exception:
            pass
# -----------------------------------------------------------

@st.cache_resource(show_spinner=False)
def get_runtime():
    # 1) Arranca un loop dedicado
    runner = AsyncRunner()
    # 2) Carga config y levanta MCP clients dentro de ese loop
    with open("app/host/servers.config.json", "r", encoding="utf-8") as f:
        cfg = json.load(f)
    mgr = MCPClientManager(cfg)
    runner.run(mgr.start_all())
    # 3) Cliente OpenAI (sync)
    client = OpenAI()
    return runner, mgr, client

def save_llm_log(direction, payload):
    Path("logs").mkdir(exist_ok=True, parents=True)
    rec = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "direction": direction,
        **payload
    }
    with open(Path("logs") / f"llm-{time.strftime('%Y%m%d')}.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(jsonable(rec), ensure_ascii=False) + "\n")

st.set_page_config(page_title="MCP Web Chat", layout="wide")
st.title("MCP Web Chat (Streamlit)")
st.caption(f"Modelo: {MODEL}")

if "messages" not in st.session_state:
    st.session_state.messages = [{
        "role": "system",
        "content": (
            "You are an MCP-capable assistant. "
            "If a user asks to read/write files, analyze code, or run repo actions, "
            "use the 'mcp_call' tool with the appropriate server and method."
        )
    }]

runner, mgr, client = get_runtime()

with st.sidebar:
    st.subheader("Herramientas MCP")
    if st.button("Listar tools (local-complexity)"):
        try:
            res = runner.run(mgr.call("local-complexity", "tools/list", {}))
            st.code(json.dumps(res, indent=2, ensure_ascii=False), language="json")
        except Exception as e:
            st.error(str(e))
    cols = st.columns(3)
    if cols[0].button("tools/list filesystem"):
        try:
            res = runner.run(mgr.call("filesystem", "tools/list", {}))
            st.code(json.dumps(res, indent=2, ensure_ascii=False), language="json")
        except Exception as e:
            st.error(str(e))
    if cols[1].button("tools/list git"):
        try:
            res = runner.run(mgr.call("git", "tools/list", {}))
            st.code(json.dumps(res, indent=2, ensure_ascii=False), language="json")
        except Exception as e:
            st.error(str(e))
    if cols[2].button("tools/list remote-utils"):
        try:
            res = runner.run(mgr.call("remote-utils", "tools/list", {}))
            st.code(json.dumps(res, indent=2, ensure_ascii=False), language="json")
        except Exception as e:
            st.error(str(e))
    st.divider()
    st.write("Logs en `logs/`")

# Mostrar historial
for m in st.session_state.messages:
    if m["role"] != "system":
        st.chat_message(m["role"]).write(m["content"])

prompt = st.chat_input("Escribe tu mensaje…")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    # Turno 1 (permite tool-calls)
    save_llm_log("send", {"messages": st.session_state.messages})
    r = client.chat.completions.create(
        model=MODEL,
        messages=st.session_state.messages,
        tools=OPENAI_TOOLS,
        tool_choice="auto",
        temperature=0.2
    )
    save_llm_log("recv", {"raw": r.model_dump()})
    msg = r.choices[0].message

    tool_msgs = []
    if msg.tool_calls:
        with st.status("Invocando herramientas MCP…", expanded=False):
            for tc in msg.tool_calls:
                if tc.type != "function":
                    continue
                fn = tc.function.name
                args = json.loads(tc.function.arguments or "{}")

                if fn != "mcp_call":
                    tool_msgs.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "name": fn,
                        "content": "Unsupported tool"
                    })
                    continue

                try:
                    # Ejecuta llamadas MCP dentro del loop dedicado
                    result = runner.run(mgr.call(args["server"], args["method"], args.get("params", {})))
                    tool_msgs.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "name": "mcp_call",
                        "content": json.dumps({"ok": True, "result": result}, ensure_ascii=False)
                    })
                except Exception as e:
                    tool_msgs.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "name": "mcp_call",
                        "content": json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)
                    })

        # Guarda tool_calls como dicts serializables
        st.session_state.messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": serialize_tool_calls(msg.tool_calls)
        })
        # Añade los mensajes de herramientas
        st.session_state.messages.extend(tool_msgs)

        # Turno 2 (cierre)
        save_llm_log("send", {"messages": st.session_state.messages[-12:]})
        r2 = client.chat.completions.create(
            model=MODEL,
            messages=st.session_state.messages,
            temperature=0.2
        )
        save_llm_log("recv", {"raw": r2.model_dump()})
        final_text = r2.choices[0].message.content or "_(sin contenido)_"
        st.chat_message("assistant").write(final_text)
        st.session_state.messages.append({"role": "assistant", "content": final_text})
    else:
        # Respuesta directa
        final_text = msg.content or "_(sin contenido)_"
        st.chat_message("assistant").write(final_text)
        st.session_state.messages.append({"role": "assistant", "content": final_text})
