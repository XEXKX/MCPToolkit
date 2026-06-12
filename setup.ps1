Write-Host "=== MCPToolkit Setup ===" -ForegroundColor Cyan

# Vždy pracuj ve složce repozitáře, bez ohledu odkud je skript spuštěn
Set-Location $PSScriptRoot

# 1. npm servery
Write-Host "`n[1/3] Instaluji npm MCP servery..." -ForegroundColor Yellow
npm install
if ($LASTEXITCODE -ne 0) { Write-Host "npm install selhal!" -ForegroundColor Red; exit 1 }

# 2. pip servery
Write-Host "`n[2/3] Instaluji Python MCP servery..." -ForegroundColor Yellow
pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { Write-Host "pip install selhal!" -ForegroundColor Red; exit 1 }

# 3. vloz mcpServers do settings.json
Write-Host "`n[3/3] Registruji MCP servery do Claude settings.json..." -ForegroundColor Yellow
$settingsPath = "$env:USERPROFILE\.claude\settings.json"
$mcpServers = (Get-Content ".\mcp.json" | ConvertFrom-Json).mcpServers

if (Test-Path $settingsPath) {
    $settings = Get-Content $settingsPath | ConvertFrom-Json
} else {
    $settings = [PSCustomObject]@{}
}
$settings | Add-Member -NotePropertyName "mcpServers" -NotePropertyValue $mcpServers -Force
$settings | ConvertTo-Json -Depth 10 | Set-Content $settingsPath -Encoding UTF8
Write-Host "Zaregistrováno do $settingsPath" -ForegroundColor Green

Write-Host "`nHotovo! Restartuj Claude Code." -ForegroundColor Green