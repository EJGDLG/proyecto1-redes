import sys, asyncio

# 🔧 Fix: usar loop compatible con subprocess en Windows
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import os, json, asyncio, time
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from app.host.mcp_client import MCPClientManager
from app.host.tool_router import OPENAI_TOOLS
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table

load_dotenv()

MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
client = OpenAI()
console = Console()

def save_llm_log(direction, payload):
    Path("logs").mkdir(exist_ok=True, parents=True)
    with open(Path("logs")/f"llm-{time.strftime('%Y%m%d')}.jsonl","a",encoding="utf-8") as f:
        rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "direction": direction, **payload}
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

async def start_manager():
    import json
    cfg = json.load(open("app/host/servers.config.json","r",encoding="utf-8"))
    mgr = MCPClientManager(cfg)
    await mgr.start_all()
    return mgr

def header():
    t = Table.grid(expand=True)
    t.add_column(); t.add_column(justify="right")
    t.add_row("[bold]Proyecto MCP – Terminal UI[/bold]", f"[dim]Modelo:[/dim] {MODEL}")
    return Panel(t, style="cyan", padding=(1,2))

async def chat_loop():
    mgr = await start_manager()
    messages = [{
        "role": "system",
        "content": ("You are an MCP-capable assistant. "
                    "If a user asks to read/write files, analyze code, or run repo actions, "
                    "use the 'mcp_call' tool with the appropriate server and method.")
    }]

    console.print(header())
    console.print(Panel("Comandos: [bold]/exit[/bold] salir · [bold]/tools[/bold] listar herramientas.", style="green"))

    while True:
        user = console.input("[bold magenta]Tú >[/bold magenta] ").strip()
        if user.lower() in ("exit","/exit","quit"): 
            console.print("[dim]Saliendo...[/dim]")
            break
        if user.lower() in ("/tools","tools"):
            tools = await mgr.call("local-complexity", "tools/list", {})
            console.print(Panel(Markdown(f"### Tools Locales\n```json\n{json.dumps(tools, indent=2, ensure_ascii=False)}\n```"), title="tools/list"))
            continue

        messages.append({"role":"user","content":user})

        save_llm_log("send", {"messages": messages})
        r = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=OPENAI_TOOLS,
            tool_choice="auto",
            temperature=0.2
        )
        save_llm_log("recv", {"raw": r.model_dump()})
        msg = r.choices[0].message

        tool_msgs = []
        if msg.tool_calls:
            console.print(Panel("[dim]Invocando herramientas MCP...[/dim]", style="blue"))
            for tc in msg.tool_calls:
                if tc.type != "function": continue
                fn = tc.function.name
                args = json.loads(tc.function.arguments or "{}")
                if fn != "mcp_call":
                    tool_msgs.append({"role": "tool", "tool_call_id": tc.id,
                                      "name": fn, "content": f"Unsupported tool {fn}"})
                    continue
                try:
                    result = await mgr.call(args["server"], args["method"], args.get("params", {}))
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

            messages.append({"role":"assistant","content":msg.content or "", "tool_calls": msg.tool_calls})
            messages.extend(tool_msgs)

            save_llm_log("send", {"messages": messages[-12:]})
            r2 = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                temperature=0.2
            )
            save_llm_log("recv", {"raw": r2.model_dump()})
            final_text = r2.choices[0].message.content
            console.print(Panel(Markdown(final_text or "_(sin contenido)_"), title="Asistente"))
            messages.append({"role":"assistant","content":final_text})
        else:
            console.print(Panel(Markdown(msg.content or "_(sin contenido)_"), title="Asistente"))
            messages.append({"role":"assistant","content":msg.content})

if __name__ == "__main__":
    asyncio.run(chat_loop())
