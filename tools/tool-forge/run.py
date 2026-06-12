#!/usr/bin/env python3
"""
Tool Forge — generátor nástrojů pro MCPToolkit
Použití: python run.py --goal "Co má tool dělat" [--start "..."] [--runtime ps1|py|js]
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from datetime import date

# ── Cesty ─────────────────────────────────────────────────────────────────────
FORGE_DIR   = Path(__file__).parent
TOOLKIT_ROOT = FORGE_DIR.parent.parent
MANIFEST    = TOOLKIT_ROOT / "manifest.json"
TOOLS_DIR   = TOOLKIT_ROOT / "tools"

# ── Systémový prompt pro generování ───────────────────────────────────────────
SYSTEM_PROMPT = """You are Tool Forge, an expert at creating portable, reusable tools for AI agent systems.

Given a goal, you generate:
1. A tool.yaml manifest (machine-readable metadata for small models)
2. A working implementation script (run.ps1 or run.py)

RULES FOR tool.yaml:
- name: snake_case, short (2-3 words max)
- description: exactly 1 sentence, starts with a verb, max 120 chars
- all inputs listed with type (string|bool|int), required (true/false), description
- outputs: 1 sentence describing what the tool produces
- call: exact command template using {tool_dir} and {param_name} placeholders
- tags: 2-4 relevant lowercase tags
- tested: false (always)

RULES FOR implementation:
- Must work standalone (no imports beyond stdlib + specified deps)
- Must handle missing optional params gracefully
- Must print a clear success/error message at the end
- PowerShell: use param() block, Write-Host for output
- Python: use argparse, print() for output, sys.exit(1) on error

OUTPUT FORMAT (exactly):
<TOOL_YAML>
...yaml content...
</TOOL_YAML>
<IMPLEMENTATION>
...script content...
</IMPLEMENTATION>
<TOOL_NAME>snake_case_name</TOOL_NAME>
"""

def build_user_prompt(goal: str, start: str, runtime: str, constraints: str) -> str:
    parts = [f"Goal: {goal}"]
    if start:       parts.append(f"Starting state / inputs: {start}")
    if constraints: parts.append(f"Constraints: {constraints}")
    parts.append(f"Runtime: {runtime} ({'PowerShell .ps1' if runtime == 'ps1' else 'Python .py' if runtime == 'py' else 'Node.js .js'})")
    parts.append("Generate the tool now.")
    return "\n".join(parts)

def call_claude(goal: str, start: str, runtime: str, constraints: str, model: str) -> str:
    try:
        import anthropic
    except ImportError:
        print("Instaluji anthropic SDK...", flush=True)
        subprocess.check_call([sys.executable, "-m", "pip", "install", "anthropic", "-q"])
        import anthropic

    client = anthropic.Anthropic()
    print(f"Volám {model} pro generování nástroje...", flush=True)

    msg = client.messages.create(
        model=model,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": build_user_prompt(goal, start, runtime, constraints)}]
    )
    return msg.content[0].text

def parse_response(response: str) -> tuple[str, str, str]:
    yaml_match  = re.search(r"<TOOL_YAML>(.*?)</TOOL_YAML>", response, re.DOTALL)
    impl_match  = re.search(r"<IMPLEMENTATION>(.*?)</IMPLEMENTATION>", response, re.DOTALL)
    name_match  = re.search(r"<TOOL_NAME>(.*?)</TOOL_NAME>", response, re.DOTALL)

    if not (yaml_match and impl_match and name_match):
        print("CHYBA: Model nevrátil očekávaný formát.", file=sys.stderr)
        print("Raw response:", response[:500], file=sys.stderr)
        sys.exit(1)

    return (
        yaml_match.group(1).strip(),
        impl_match.group(1).strip(),
        name_match.group(1).strip()
    )

def save_tool(name: str, yaml_content: str, impl_content: str, runtime: str):
    tool_dir = TOOLS_DIR / name
    if tool_dir.exists():
        print(f"CHYBA: Nástroj '{name}' již existuje v {tool_dir}", file=sys.stderr)
        sys.exit(1)

    tool_dir.mkdir(parents=True)

    # tool.yaml
    (tool_dir / "tool.yaml").write_text(yaml_content, encoding="utf-8")

    # implementace
    ext = {"ps1": "run.ps1", "py": "run.py", "js": "run.js"}.get(runtime, f"run.{runtime}")
    (tool_dir / ext).write_text(impl_content, encoding="utf-8")

    print(f"✓ Nástroj uložen: {tool_dir}")
    return tool_dir

def update_manifest(name: str, yaml_content: str, tool_dir: Path):
    """Parsuje tool.yaml a přidá záznam do manifest.json"""
    import yaml as yaml_lib
    try:
        tool_meta = yaml_lib.safe_load(yaml_content)
    except Exception:
        # Fallback: minimální záznam bez parsování
        tool_meta = {"name": name, "description": "Auto-generated tool"}

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    # Uprav call cestu na relativní
    if "call" in tool_meta:
        tool_meta["call"] = tool_meta["call"].replace("{tool_dir}", f"tools/{name}")

    tool_meta["tool_dir"] = f"tools/{name}"
    tool_meta.setdefault("tested", False)

    # Odstraň existující záznam pokud existuje (re-generace)
    manifest["tools"] = [t for t in manifest["tools"] if t.get("name") != name]
    manifest["tools"].append(tool_meta)

    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✓ Zapsáno do manifest.json")

def git_commit(name: str):
    try:
        subprocess.run(["git", "-C", str(TOOLKIT_ROOT), "add", "."],         check=True, capture_output=True)
        subprocess.run(["git", "-C", str(TOOLKIT_ROOT), "commit", "-m",
                        f"tool-forge: add {name} ({date.today()})"],          check=True, capture_output=True)
        result = subprocess.run(["git", "-C", str(TOOLKIT_ROOT), "push"],
                                capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✓ Pushnuté na GitHub")
        else:
            print(f"⚠ Commit OK, push selhal (nastav remote): {result.stderr.strip()}")
    except subprocess.CalledProcessError as e:
        print(f"⚠ Git chyba: {e}")

def main():
    parser = argparse.ArgumentParser(description="Tool Forge — generátor nástrojů")
    parser.add_argument("--goal",        required=True,  help="Co má nástroj dělat")
    parser.add_argument("--start",       default="",     help="Výchozí stav / vstupy")
    parser.add_argument("--runtime",     default="ps1",  choices=["ps1","py","js"])
    parser.add_argument("--constraints", default="",     help="Omezení / požadavky")
    parser.add_argument("--model",       default="claude-sonnet-4-6")
    parser.add_argument("--no-git",      action="store_true", help="Neprovádět git commit")
    args = parser.parse_args()

    print(f"\n🔨 Tool Forge")
    print(f"   Cíl:     {args.goal}")
    print(f"   Runtime: {args.runtime}")
    print()

    # Generuj
    response = call_claude(args.goal, args.start, args.runtime, args.constraints, args.model)
    yaml_content, impl_content, name = parse_response(response)

    print(f"   Název:   {name}")

    # Ulož
    tool_dir = save_tool(name, yaml_content, impl_content, args.runtime)

    # Manifest
    try:
        import yaml  # noqa
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyyaml", "-q"])
    update_manifest(name, yaml_content, tool_dir)

    # Git
    if not args.no_git:
        git_commit(name)

    print(f"\n✅ Hotovo! Nástroj '{name}' je připraven.")
    print(f"   Složka:  {tool_dir}")
    print(f"   Volání:  viz manifest.json → tools['{name}'].call")

if __name__ == "__main__":
    main()
