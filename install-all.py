#!/usr/bin/env python3
"""Batch installer for all MCPToolkit catalog servers."""
import json, subprocess, sys, time
from pathlib import Path

CATALOG = Path(__file__).parent / "tools/mcp-scout/catalog.json"
RUN_PY  = Path(__file__).parent / "tools/mcp-scout/run.py"

data    = json.loads(CATALOG.read_text(encoding="utf-8"))
servers = data["servers"]

# Servery, ktere preskocime (vyzaduji velke runtime / specialni setup)
SKIP = {
    "windows-control",  # git+pip + pyautogui, potrebuje manual setup
    "home-assistant",   # potrebuje bezici HA instanci
    "mindsdb",          # extremne velky balicek (>1GB)
    "tmux",             # jen pro Linux
}

ok, fail, skip = [], [], []

for s in servers:
    name = s["name"]
    if name in SKIP:
        skip.append(name)
        print(f"[SKIP]  {name}")
        continue

    print(f"\n{'='*60}")
    print(f"[{servers.index(s)+1}/{len(servers)}] Instaluji: {name}")
    print(f"{'='*60}")

    r = subprocess.run(
        [sys.executable, str(RUN_PY), "--action", "install", "--name", name],
        timeout=180
    )
    if r.returncode == 0:
        ok.append(name)
    else:
        fail.append(name)

print(f"\n\n{'='*60}")
print(f"VYSLEDEK: {len(ok)} ok | {len(fail)} selhalo | {len(skip)} preskoceno")
if ok:
    print(f"\nNainstalovan ({len(ok)}): {', '.join(ok)}")
if fail:
    print(f"\nSelhalo ({len(fail)}): {', '.join(fail)}")
if skip:
    print(f"\nPreskoceno ({len(skip)}): {', '.join(skip)}")
print("\nRestartuj Claude Code pro nacteni novych MCP serveru.")
