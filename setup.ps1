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

# 3. vloz mcpServers do ~/.claude.json (TOTO je misto kde Claude Code CLI cte MCP servery)
Write-Host "`n[3/3] Registruji MCP servery do ~/.claude.json..." -ForegroundColor Yellow
$claudeJsonPath = "$env:USERPROFILE\.claude.json"
$mcpServers = (Get-Content ".\mcp.json" | ConvertFrom-Json).mcpServers

if (Test-Path $claudeJsonPath) {
    Copy-Item $claudeJsonPath "$claudeJsonPath.backup" -Force
    $cfg = Get-Content $claudeJsonPath -Raw | ConvertFrom-Json
} else {
    $cfg = [PSCustomObject]@{}
}
$cfg | Add-Member -NotePropertyName "mcpServers" -NotePropertyValue $mcpServers -Force
$cfg | ConvertTo-Json -Depth 20 | Set-Content $claudeJsonPath -Encoding UTF8
Write-Host "Zaregistrováno $($mcpServers.PSObject.Properties.Name.Count) serveru do $claudeJsonPath" -ForegroundColor Green

# 4. Overeni
Write-Host "`n=== Overeni (claude mcp list) ===" -ForegroundColor Cyan
$result = claude mcp list 2>&1
$ok = ($result | Select-String "✓ Connected").Count
$fail = ($result | Select-String "✗ Failed").Count
Write-Host "Connected: $ok | Failed: $fail" -ForegroundColor Yellow

Write-Host "`nHotovo! Restartuj Claude Code." -ForegroundColor Green