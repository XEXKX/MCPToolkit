#requires -Version 5.1
<#
MCPToolkit setup — installs all MCP servers and registers them with a chosen client.

Usage:
    .\setup.ps1                    # default: claude-code
    .\setup.ps1 -Client cursor
    .\setup.ps1 -Client claude-desktop
    .\setup.ps1 -SkipInstall       # only re-register config, no npm/pip install
#>
param(
    [ValidateSet("claude-code","cursor","claude-desktop","hermes")]
    [string]$Client = "claude-code",
    [switch]$SkipInstall
)

Set-Location $PSScriptRoot
$ErrorActionPreference = "Stop"

Write-Host "=== MCPToolkit Setup ===" -ForegroundColor Cyan
Write-Host "Target client: $Client`n" -ForegroundColor Cyan

# ----- 1. Detekce runtime -----
function Test-Cmd($name) { $null -ne (Get-Command $name -ErrorAction SilentlyContinue) }

Write-Host "[1/4] Detekuji runtime..." -ForegroundColor Yellow
$missing = @()
foreach ($cmd in @("git","node","npm","npx","python","pip")) {
    if (Test-Cmd $cmd) {
        Write-Host "  OK  $cmd" -ForegroundColor Green
    } else {
        Write-Host "  CHYBI  $cmd" -ForegroundColor Red
        $missing += $cmd
    }
}
if (-not (Test-Cmd "uvx")) {
    Write-Host "  CHYBI  uvx (pip install uv)" -ForegroundColor Red
    $missing += "uvx"
}
if ($missing.Count -gt 0) {
    Write-Host "`nNainstaluj chybejici nastroje a spust znovu." -ForegroundColor Red
    Write-Host "  Node.js:  https://nodejs.org" -ForegroundColor Yellow
    Write-Host "  Python:   https://python.org" -ForegroundColor Yellow
    Write-Host "  uv:       pip install uv" -ForegroundColor Yellow
    exit 1
}

# ----- 2. Instalace balicku -----
if (-not $SkipInstall) {
    Write-Host "`n[2/4] Instaluji npm MCP servery..." -ForegroundColor Yellow
    npm install
    if ($LASTEXITCODE -ne 0) { Write-Host "npm install selhal!" -ForegroundColor Red; exit 1 }

    Write-Host "`n  Instaluji Python MCP servery..." -ForegroundColor Yellow
    pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { Write-Host "pip install selhal!" -ForegroundColor Red; exit 1 }
} else {
    Write-Host "`n[2/4] -SkipInstall: preskakuji npm/pip" -ForegroundColor Yellow
}

# ----- 3. Nacti .env a inject do mcp.json -----
Write-Host "`n[3/4] Pripravuji konfiguraci..." -ForegroundColor Yellow

$envFile = Join-Path $PSScriptRoot ".env"
$envVars = @{}
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
            $k, $v = $line -split "=", 2
            $envVars[$k.Trim()] = $v.Trim()
        }
    }
    Write-Host "  Nacteno $($envVars.Count) promennych z .env" -ForegroundColor Green
} else {
    Write-Host "  .env nenalezen - tokeny zustavaji jako placeholdery" -ForegroundColor Yellow
    Write-Host "  Zkopiruj .env.example -> .env a vypln hodnoty." -ForegroundColor Yellow
}

# Nahrad {PLACEHOLDER} -> hodnota z .env
$mcpRaw = Get-Content ".\mcp.json" -Raw
foreach ($k in $envVars.Keys) {
    if ($envVars[$k]) {
        $mcpRaw = $mcpRaw -replace ("\{" + [regex]::Escape($k) + "\}"), $envVars[$k]
    }
}
$mcpServers = ($mcpRaw | ConvertFrom-Json).mcpServers

# ----- 4. Registrace do klienta -----
Write-Host "`n[4/4] Registruji $($mcpServers.PSObject.Properties.Name.Count) serveru do '$Client'..." -ForegroundColor Yellow

if ($Client -eq "hermes") {
    & "$PSScriptRoot\install-hermes.ps1" -SkipInstall
    exit $LASTEXITCODE
}

switch ($Client) {
    "claude-code" {
        $path = "$env:USERPROFILE\.claude.json"
    }
    "claude-desktop" {
        $path = "$env:APPDATA\Claude\claude_desktop_config.json"
    }
    "cursor" {
        $path = "$env:USERPROFILE\.cursor\mcp.json"
    }
}

$dir = Split-Path $path -Parent
if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }

if (Test-Path $path) {
    Copy-Item $path "$path.backup" -Force
    $cfg = Get-Content $path -Raw | ConvertFrom-Json
} else {
    $cfg = [PSCustomObject]@{}
}
$cfg | Add-Member -NotePropertyName "mcpServers" -NotePropertyValue $mcpServers -Force
$cfg | ConvertTo-Json -Depth 20 | Set-Content $path -Encoding UTF8
Write-Host "  Zapsano do: $path" -ForegroundColor Green

# Overeni (jen pro claude-code)
if ($Client -eq "claude-code" -and (Test-Cmd "claude")) {
    Write-Host "`n=== Overeni (claude mcp list) ===" -ForegroundColor Cyan
    $result = claude mcp list 2>&1
    $ok = ($result | Select-String "Connected").Count
    $fail = ($result | Select-String "Failed").Count
    Write-Host "Connected: $ok | Failed: $fail" -ForegroundColor Yellow
}

Write-Host "`nHotovo! Restartuj '$Client' a tools budou dostupne." -ForegroundColor Green
