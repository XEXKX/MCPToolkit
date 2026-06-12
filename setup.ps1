Write-Host "=== MCPToolkit Setup ===" -ForegroundColor Cyan

# 1. npm servery
Write-Host "`n[1/3] Instaluji npm MCP servery..." -ForegroundColor Yellow
npm install
if ($LASTEXITCODE -ne 0) { Write-Host "npm install selhal!" -ForegroundColor Red; exit 1 }

# 2. pip servery
Write-Host "`n[2/3] Instaluji Python MCP servery..." -ForegroundColor Yellow
pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { Write-Host "pip install selhal!" -ForegroundColor Red; exit 1 }

# 3. zkopiruj mcp.json do Claude
Write-Host "`n[3/3] Kopíruji mcp.json do Claude..." -ForegroundColor Yellow
$dest = "$env:USERPROFILE\.claude\mcp.json"
Copy-Item ".\mcp.json" $dest -Force
Write-Host "Zkopírováno do $dest" -ForegroundColor Green

Write-Host "`nHotovo! Restartuj Claude Code." -ForegroundColor Green