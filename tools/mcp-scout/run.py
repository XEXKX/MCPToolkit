#!/usr/bin/env python3
"""
mcp-scout — Integrator existujicich MCP serveru do MCPToolkitu.
Pouziti: python3 run.py --action list|install|search [--name X] [--category X] [--keyword X]
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

TOOL_DIR     = Path(__file__).parent
TOOLKIT_ROOT = TOOL_DIR.parent.parent
CATALOG      = TOOL_DIR / "catalog.json"
MCP_JSON     = Path.home() / ".claude" / "mcp.json"

CATEGORIES = {
    "code":    "Code generation & dev tools",
    "system":  "Windows 11 & Linux system control",
    "browser": "Web browser automation",
    "data":    "Data files (SQL, Excel, CSV)",
    "text":    "Text & document processing",
}

def load_catalog() -> list[dict]:
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    return data["servers"]

def load_mcp_json() -> dict:
    if MCP_JSON.exists():
        return json.loads(MCP_JSON.read_text(encoding="utf-8"))
    return {"mcpServers": {}}

def save_mcp_json(data: dict):
    MCP_JSON.parent.mkdir(parents=True, exist_ok=True)
    MCP_JSON.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def action_list(category: str | None):
    servers = load_catalog()
    if category and category != "all":
        servers = [s for s in servers if s["category"] == category]

    mcp_cfg = load_mcp_json()
    installed = set(mcp_cfg.get("mcpServers", {}).keys())

    current_cat = None
    for s in sorted(servers, key=lambda x: (x["category"], x["name"])):
        if s["category"] != current_cat:
            current_cat = s["category"]
            label = CATEGORIES.get(current_cat, current_cat.upper())
            print(f"\n[{current_cat.upper()}] {label}")
            print("-" * 50)
        status = "[installed]" if s["name"] in installed else ""
        print(f"  {s['name']:<22} {s['description'][:60]}  {status}")

    print(f"\nCelkem: {len(servers)} serveru | Nainstalovat: python3 run.py --action install --name <name>")

def action_search(keyword: str):
    servers = load_catalog()
    kw = keyword.lower()
    results = [s for s in servers if
               kw in s["name"].lower() or
               kw in s["description"].lower() or
               any(kw in t for t in s.get("tags", []))]
    if not results:
        print(f"Zadny vysledek pro '{keyword}'")
        return
    for s in results:
        print(f"  {s['name']:<22} [{s['category']}]  {s['description'][:70]}")

def _json_escape(s: str) -> str:
    """Escape string so it is safe to embed as a JSON value (no raw backslashes)."""
    return s.replace("\\", "\\\\")

def resolve_placeholders(cfg: dict, name: str) -> dict:
    """Nahrad {placeholder} v mcp_config hodnotami od uzivatele nebo defaults."""
    cfg_str = json.dumps(cfg)
    defaults = {
        "{allowed_dirs}": _json_escape(str(Path.home())),
        "{repo_path}":    _json_escape(str(TOOLKIT_ROOT)),
        "{db_path}":      _json_escape(str(Path.home() / "data.db")),
        "{connection_string}": "postgresql://localhost/mydb",
        "{install_dir}":  _json_escape(str(TOOLKIT_ROOT / "external" / name)),
        "{GITHUB_TOKEN}": os.environ.get("GITHUB_TOKEN", "YOUR_GITHUB_TOKEN"),
    }
    for placeholder, value in defaults.items():
        cfg_str = cfg_str.replace(placeholder, value)
    return json.loads(cfg_str)

def install_npm(package: str, name: str) -> bool:
    print(f"Instaluji npm balicek: {package}")
    r = subprocess.run(f"npm install -g {package}", shell=True, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"npm install selhal: {r.stderr[:200]}")
        return False
    return True

def install_pip(package: str) -> bool:
    print(f"Instaluji pip balicek: {package}")
    r = subprocess.run([sys.executable, "-m", "pip", "install", package, "-q"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(f"pip install selhal: {r.stderr[:200]}")
        return False
    return True

def install_uvx(package: str) -> bool:
    print(f"Instaluji uvx balicek: {package}")
    r = subprocess.run(f"uvx {package} --help", shell=True, capture_output=True, text=True, timeout=30)
    return True  # uvx installs on demand

def git_clone_external(repo: str, name: str) -> Path | None:
    dest = TOOLKIT_ROOT / "external" / name
    if dest.exists():
        print(f"Jiz naklonovan: {dest}")
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    url = f"https://github.com/{repo}.git"
    print(f"Klonuji {url}...")
    r = subprocess.run(f'git clone --depth=1 {url} "{dest}"',
                       shell=True, capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        print(f"git clone selhal: {r.stderr[:200]}")
        return None
    return dest

def action_install(name: str, dry_run: bool):
    servers = load_catalog()
    server = next((s for s in servers if s["name"] == name), None)

    if not server:
        print(f"Server '{name}' nenalezen v katalogu.")
        print("Pouzij --action list pro zobrazeni dostupnych serveru.")
        sys.exit(1)

    print(f"\nInstalace: {server['display']}")
    print(f"Popis: {server['description']}")
    print(f"Zdroj: github.com/{server['repo']}")

    if dry_run:
        print(f"\n[dry-run] Instalacni prikaz: {server['install']}")
        print(f"[dry-run] MCP config: {json.dumps(server['mcp_config'], indent=2)}")
        return

    install_info = server["install"]
    success = False

    if install_info["type"] == "npx":
        success = install_npm(install_info["package"], name)
    elif install_info["type"] in ("uvx", "uv"):
        success = install_uvx(install_info["package"])
        success = True  # uvx is always "installed" on demand
    elif install_info["type"] == "pip":
        success = install_pip(install_info["package"])
    elif install_info["type"] == "git+pip":
        dest = git_clone_external(server["repo"], name)
        if dest:
            req = dest / "requirements.txt"
            if req.exists():
                subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(req), "-q"])
            for dep in install_info.get("requires", []):
                install_pip(dep)
            success = True
    else:
        print(f"Neznam typ instalace: {install_info['type']}")

    if not success:
        print(f"\nInstalace selhala. Zkus rucni postup: https://github.com/{server['repo']}")
        sys.exit(1)

    # Zaregistruj do ~/.claude/mcp.json
    mcp_cfg = load_mcp_json()
    resolved_config = resolve_placeholders(server["mcp_config"], name)
    mcp_cfg.setdefault("mcpServers", {})[name] = resolved_config
    save_mcp_json(mcp_cfg)
    print(f"Zaregistrovan do {MCP_JSON}")

    # Zaregistruj do MCPToolkit manifest jako externiho providera
    manifest_path = TOOLKIT_ROOT / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.setdefault("external_mcps", [])
    manifest["external_mcps"] = [e for e in manifest["external_mcps"] if e.get("name") != name]
    manifest["external_mcps"].append({
        "name": name,
        "display": server["display"],
        "description": server["description"],
        "category": server["category"],
        "tags": server["tags"],
        "repo": f"https://github.com/{server['repo']}",
        "mcp_config": resolved_config
    })
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Zaregistrovan do manifest.json [external_mcps]")

    print(f"\nServer '{name}' je pripraveny. Restartuj Claude Code / agenta pro nacteni.")

def main():
    parser = argparse.ArgumentParser(description="mcp-scout: integrator externich MCP serveru")
    parser.add_argument("--action",   required=True, choices=["list","install","search"])
    parser.add_argument("--name",     default="")
    parser.add_argument("--category", default="all")
    parser.add_argument("--keyword",  default="")
    parser.add_argument("--dry-run",  action="store_true")
    args = parser.parse_args()

    if args.action == "list":
        action_list(args.category if args.category != "all" else None)
    elif args.action == "search":
        if not args.keyword:
            print("Pro search zadej --keyword")
            sys.exit(1)
        action_search(args.keyword)
    elif args.action == "install":
        if not args.name:
            print("Pro install zadej --name")
            sys.exit(1)
        action_install(args.name, args.dry_run)

if __name__ == "__main__":
    main()
