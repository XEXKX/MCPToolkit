# MCPToolkit

Personal MCP toolkit — 40+ MCP servers and 3 custom tools, deployable to any machine with one command.

## Quick start

```powershell
git clone https://github.com/XEXKX/MCPToolkit C:\MCPToolkit
cd C:\MCPToolkit
Copy-Item .env.example .env       # fill in tokens you need
.\setup.ps1                       # default: register with Claude Code
```

Then restart your MCP client. `claude mcp list` should show 30+ Connected servers.

## Prerequisites

| Tool | Install |
|------|---------|
| Git | https://git-scm.com |
| Node.js (with npm/npx) | https://nodejs.org |
| Python 3.12+ (with pip) | https://python.org |
| uv (provides `uvx`) | `pip install uv` |

`setup.ps1` checks all of these and exits with a clear message if anything is missing.

## Supported clients

```powershell
.\setup.ps1 -Client claude-code       # ~/.claude.json (default)
.\setup.ps1 -Client cursor            # ~/.cursor/mcp.json
.\setup.ps1 -Client claude-desktop    # %APPDATA%\Claude\claude_desktop_config.json
.\setup.ps1 -Client hermes            # $HERMES_HOME/config.yaml (mcp_servers key)
```

Existing config is backed up to `<path>.backup` before being overwritten.

## API tokens

Servers like Notion, Slack, Linear, Cloudflare need real tokens. Workflow:

1. `Copy-Item .env.example .env`
2. Fill in only the keys you actually use — empty values stay as `{PLACEHOLDER}` and those servers will fail silently (others keep working).
3. Re-run `.\setup.ps1` — it reads `.env` and injects values into the registered config.

`.env` is gitignored. Never commit secrets.

## What's inside

- **`mcp.json`** — single source of truth: 44 MCP server definitions with placeholder tokens
- **`package.json` / `requirements.txt`** — pinnable dependency manifests
- **`setup.ps1`** — runtime check + install + token inject + per-client registration
- **`tools/`** — 3 custom tools (tool-forge, new-git-repo, mcp-scout)
- **`manifest.json`** — toolkit metadata, registers both custom tools and external servers

## Re-register without reinstalling

After editing `.env` or `mcp.json`:

```powershell
.\setup.ps1 -SkipInstall
```

Skips `npm install` and `pip install`, only updates the client config.

## Troubleshooting

- **`claude mcp list` shows "Failed to connect"** — usually missing token in `.env`, or server needs a service running locally (Obsidian, MotherDuck, Snowflake). Check the per-server docs.
- **Python servers fail** — `mcp.json` points to `Python312\Scripts\*.exe`. On other machines, adjust paths or use the symlinks `pip install` creates in your active Python's `Scripts/` folder.
- **MCP works in `claude mcp list` but not in a running session** — restart the client fully (close and reopen the app), not just a chat.

## Repository

https://github.com/XEXKX/MCPToolkit
