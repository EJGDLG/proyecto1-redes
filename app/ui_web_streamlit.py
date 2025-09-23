# app/ui_web_streamlit.py
# --- FIX de imports y loop para Windows ---
import sys, asyncio
from pathlib import Path

# Añade la raíz del proyecto (…/proyecto-mcp-final) al sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# En Windows, usa loop compatible con subprocess
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
# --- FIN FIX ---


import os, json, asyncio, time
import sys, asyncio
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
from app.host.mcp_client import MCPClientManager
from app.host.tool_router import OPENAI_TOOLS

load_dotenv()
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

@st.cache_resource(show_spinner=False)
def get_clients():
    # Inicia el MCP manager una sola vez
    cfg = json.load(open("app/host/servers.config.json","r",encoding="utf-8"))
    mgr = MCPClientManager(cfg)
    asyncio.run(mgr.start_all())
    return mgr

@st.cache_resource(show_spinner=False)
def get_openai():
    return OpenAI()

def save_llm_log(direction, payload):
    Path("logs").mkdir(exist_ok=True, parents=True)
    with open(Path("logs")/f"llm-{time.strftime('%Y%m%d')}.jsonl","a",encoding="utf-8") as f:
        rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "direction": direction, **payload}
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

st.set_page_config(page_title="MCP Web Chat", layout="wide")
st.title(" MCP Web Chat (Streamlit)")
st.caption(f"Modelo: {MODEL}")

if "messages" not in st.session_state:
    st.session_state.messages = [{
        "role":"system",
        "content":("You are an MCP-capable assistant. "
                   "If a user asks to read/write files, analyze code, or run repo actions, "
                   "use the 'mcp_call' tool with the appropriate server and method.")
    }]

mgr = get_clients()
client = get_openai()

with st.sidebar:
    st.subheader("Herramientas MCP")
    if st.button("Listar tools (local-complexity)"):
        res = asyncio.run(mgr.call("local-complexity","tools/list",{}))
        st.code(json.dumps(res, indent=2, ensure_ascii=False), language="json")
    st.divider()
    st.write("Logs en `logs/`")

# Mostrar historial
for m in st.session_state.messages:
    if m["role"] != "system":
        st.chat_message(m["role"]).write(m["content"])

prompt = st.chat_input("Escribe tu mensaje…")
if prompt:
    st.session_state.messages.append({"role":"user","content":prompt})
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
                if tc.type != "function": continue
                fn = tc.function.name
                args = json.loads(tc.function.arguments or "{}")
                if fn != "mcp_call":
                    tool_msgs.append({"role":"tool","tool_call_id":tc.id,"name":fn,"content":"Unsupported tool"})
                    continue
                try:
                    result = asyncio.run(mgr.call(args["server"], args["method"], args.get("params", {})))
                    tool_msgs.append({"role":"tool","tool_call_id":tc.id,"name":"mcp_call",
                                      "content": json.dumps({"ok":True,"result":result}, ensure_ascii=False)})
                except Exception as e:
                    tool_msgs.append({"role":"tool","tool_call_id":tc.id,"name":"mcp_call",
                                      "content": json.dumps({"ok":False,"error":str(e)}, ensure_ascii=False)})

        st.session_state.messages.append({"role":"assistant","content":msg.content or "", "tool_calls": msg.tool_calls})
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
        st.session_state.messages.append({"role":"assistant","content":final_text})
    else:
        # Respuesta directa
        final_text = msg.content or "_(sin contenido)_"
        st.chat_message("assistant").write(final_text)
        st.session_state.messages.append({"role":"assistant","content":final_text})
