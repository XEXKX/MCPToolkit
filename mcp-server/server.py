#!/usr/bin/env python3
"""
MCPToolkit MCP Server
Čte manifest.json a dynamicky vystavuje všechny nástroje jako MCP tools.
Spuštění: python server.py
Připojení: přidej do ~/.claude/settings.json nebo hermes config.yaml
"""
import json
import subprocess
import sys
from pathlib import Path

TOOLKIT_ROOT = Path(__file__).parent.parent
MANIFEST_PATH = TOOLKIT_ROOT / "manifest.json"

def load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

def build_input_schema(tool: dict) -> dict:
    """Převede inputs z tool.yaml na JSON Schema pro MCP"""
    properties = {}
    required = []
    for inp in tool.get("inputs", []):
        name = inp["name"]
        type_map = {"string": "string", "bool": "boolean", "int": "integer"}
        prop = {
            "type": type_map.get(inp.get("type", "string"), "string"),
            "description": inp.get("description", "")
        }
        if "default" in inp:
            prop["default"] = inp["default"]
        properties[name] = prop
        if inp.get("required", False):
            required.append(name)
    return {"type": "object", "properties": properties, "required": required}

def resolve_call(tool: dict, args: dict) -> list[str]:
    """Sestaví příkaz z call template a předaných argumentů"""
    call_template = tool.get("call", "")
    tool_dir = str(TOOLKIT_ROOT / tool.get("tool_dir", f"tools/{tool['name']}"))
    call_template = call_template.replace("{tool_dir}", tool_dir)

    for key, val in args.items():
        call_template = call_template.replace(f"{{{key}}}", str(val) if val is not None else "")

    # Odstraň nevyplněné placeholdery
    import re
    call_template = re.sub(r"\s*\{\w+\}", "", call_template).strip()

    return call_template.split()

def run_tool(tool: dict, args: dict) -> str:
    try:
        cmd = resolve_call(tool, args)
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(TOOLKIT_ROOT)
        )
        output = result.stdout.strip()
        if result.returncode != 0:
            error = result.stderr.strip()
            return f"CHYBA (exit {result.returncode}):\n{error}\n{output}"
        return output or "Tool dokončen bez výstupu."
    except subprocess.TimeoutExpired:
        return "CHYBA: Tool překročil timeout 120s."
    except FileNotFoundError as e:
        return f"CHYBA: Příkaz nenalezen — {e}"
    except Exception as e:
        return f"CHYBA: {e}"

def main():
    try:
        import mcp.server.stdio as stdio
        import mcp.types as types
        from mcp.server import Server
    except ImportError:
        print("Instaluji mcp SDK...", flush=True)
        subprocess.check_call([sys.executable, "-m", "pip", "install", "mcp", "-q"])
        import mcp.server.stdio as stdio
        import mcp.types as types
        from mcp.server import Server

    manifest = load_manifest()
    server = Server(manifest["name"])

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        manifest = load_manifest()  # hot-reload
        return [
            types.Tool(
                name=tool["name"],
                description=tool["description"],
                inputSchema=build_input_schema(tool)
            )
            for tool in manifest.get("tools", [])
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
        manifest = load_manifest()
        tool = next((t for t in manifest["tools"] if t["name"] == name), None)
        if not tool:
            return [types.TextContent(type="text", text=f"Nástroj '{name}' nenalezen v manifest.json")]
        output = run_tool(tool, arguments)
        return [types.TextContent(type="text", text=output)]

    import asyncio
    asyncio.run(stdio.stdio_server(server))

if __name__ == "__main__":
    main()
