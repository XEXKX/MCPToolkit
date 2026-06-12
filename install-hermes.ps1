#requires -Version 5.1
<#
Register MCPToolkit servers into Hermes Agent config.yaml.
Reads mcp.json (+ .env for token injection) and writes mcp_servers section.
#>
param([switch]$SkipInstall)

Set-Location $PSScriptRoot
$ErrorActionPreference = "Stop"

Write-Host "=== MCPToolkit -> Hermes Agent ===" -ForegroundColor Cyan

# 1. Lokalizuj Hermes
$hermesHome = if ($env:HERMES_HOME) { $env:HERMES_HOME } else { "$env:LOCALAPPDATA\hermes" }
$hermesConfig = Join-Path $hermesHome "config.yaml"
$hermesPython = Join-Path $hermesHome "hermes-agent\venv\Scripts\python.exe"

if (-not (Test-Path $hermesConfig)) { Write-Host "Hermes config nenalezen: $hermesConfig" -ForegroundColor Red; exit 1 }
if (-not (Test-Path $hermesPython)) { Write-Host "Hermes venv python nenalezen: $hermesPython" -ForegroundColor Red; exit 1 }
Write-Host "Hermes home: $hermesHome" -ForegroundColor Green

# 2. Nacti .env do hash mapy
$envVars = @{}
if (Test-Path ".\.env") {
    Get-Content ".\.env" | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
            $k, $v = $line -split "=", 2
            if ($v.Trim()) { $envVars[$k.Trim()] = $v.Trim() }
        }
    }
    Write-Host "Nacteno $($envVars.Count) tokenu z .env" -ForegroundColor Green
}

# 3. Inject tokenu do mcp.json -> docasny soubor
$mcpRaw = Get-Content ".\mcp.json" -Raw
foreach ($k in $envVars.Keys) {
    $mcpRaw = $mcpRaw -replace ("\{" + [regex]::Escape($k) + "\}"), $envVars[$k]
}
$tmpJson = Join-Path $env:TEMP "mcptoolkit_inject.json"
$mcpRaw | Set-Content $tmpJson -Encoding UTF8

# 4. Python skript: nacti JSON, nacti YAML, merge mcp_servers, zapis YAML
$pyScript = @"
import json, sys, shutil, subprocess

# Zajisti PyYAML v Hermes venv
try:
    import yaml
except ImportError:
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--quiet', 'pyyaml'])
    import yaml

src = r'$tmpJson'
dst = r'$hermesConfig'

shutil.copy(dst, dst + '.backup')
with open(src, encoding='utf-8') as f:
    mcp_servers = json.load(f)['mcpServers']
with open(dst, encoding='utf-8') as f:
    cfg = yaml.safe_load(f) or {}

cfg['mcp_servers'] = mcp_servers
with open(dst, 'w', encoding='utf-8') as f:
    yaml.safe_dump(cfg, f, default_flow_style=False, sort_keys=True, allow_unicode=True)
print(f'Zapsano {len(mcp_servers)} serveru')
"@

$pyTmp = Join-Path $env:TEMP "mcptoolkit_to_hermes.py"
$pyScript | Set-Content $pyTmp -Encoding UTF8

Write-Host "`nKonvertuji a zapisuju do Hermes config.yaml..." -ForegroundColor Yellow
& $hermesPython $pyTmp
if ($LASTEXITCODE -ne 0) { Write-Host "Selhalo!" -ForegroundColor Red; exit 1 }

# 5. Overeni
Write-Host "`n=== hermes mcp list ===" -ForegroundColor Cyan
$hermesExe = Join-Path $hermesHome "hermes-agent\venv\Scripts\hermes.exe"
& $hermesExe mcp list 2>&1 | Select-Object -First 50

Remove-Item $tmpJson -Force
Remove-Item $pyTmp -Force
Write-Host "`nHotovo. Restartuj Hermes Agent (zavri tray ikonu a spust znovu)." -ForegroundColor Green
