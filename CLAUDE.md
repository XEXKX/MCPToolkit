# MCPToolkit — instrukce pro agenty

## Co je tento repozitář
Osobní knihovna nástrojů přenositelná mezi AI agenty přes MCP protokol.
Lokální cesta: `C:\MCPToolkit`
GitHub: https://github.com/XEXKX/MCPToolkit

## Jak navigovat nástroje (PŘEČTI VŽDY)
1. Načti `manifest.json` — obsahuje všechny nástroje s popisem a parametry (~2 KB)
2. Vyber nástroj podle `description` a `tags`
3. Načti `tools/<jmeno>/tool.yaml` pro detaily (volitelné)
4. Zavolej tool přes MCP nebo přímé spuštění dle `call` template

**NIKDY nečti implementační soubory (run.ps1, run.py) pokud to není nutné.**

## Přidání nového nástroje
Zavolej `tool-forge` s popisem cíle:
```
tool-forge --goal "Co má nástroj dělat" --runtime ps1
```
Forge automaticky vytvoří tool.yaml + implementaci + zapíše do manifest.json.

## MCP server
Spuštění: `python C:\MCPToolkit\mcp-server\server.py`
Všechny nástroje z manifest.json jsou pak dostupné jako MCP tools.

## Uložení GitHub tokenu
```powershell
$env:GITHUB_TOKEN = "ghp_..."
# nebo permanentně:
[System.Environment]::SetEnvironmentVariable("GITHUB_TOKEN","ghp_...","User")
```
