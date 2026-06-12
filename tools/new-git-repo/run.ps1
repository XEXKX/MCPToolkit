<#
.SYNOPSIS
    Inicializuje git repo ze složky, vytvoří GitHub repozitář a nastaví auto-push při uložení.

.DESCRIPTION
    Nástroj pro rychlé propojení lokální složky s GitHubem:
    1. Detekuje typ projektu (Python / Node / Electron / Mix) a vygeneruje .gitignore
    2. Inicializuje git, provede první commit
    3. Vytvoří GitHub repozitář přes API (vyžaduje -Token)
    4. Nastaví remote origin a pushne
    5. Vytvoří auto-push FileSystemWatcher skript
    6. Přidá startup spouštěč do Windows Startup složky

.PARAMETER Path
    Cesta ke složce (povinný). Příklad: "C:\MujProjekt"

.PARAMETER RepoName
    Název GitHub repozitáře. Výchozí: název složky.

.PARAMETER GitHubUser
    GitHub uživatelské jméno. Výchozí: XEXKX

.PARAMETER Token
    GitHub Personal Access Token (PAT) s oprávněním 'repo'.
    Vytvoř na: https://github.com/settings/tokens/new?scopes=repo
    Lze také uložit do proměnné prostředí GITHUB_TOKEN.

.PARAMETER Private
    Přepínač — vytvoří privátní repozitář. Výchozí: veřejný.

.PARAMETER SkipGitHub
    Přeskočí vytváření GitHub repo (pouze lokální git init + auto-push).

.PARAMETER DebounceSeconds
    Kolik sekund čekat po poslední změně před commitem. Výchozí: 15.

.EXAMPLE
    .\New-GitRepo.ps1 -Path "C:\MujProjekt" -Token "ghp_abc123"

.EXAMPLE
    .\New-GitRepo.ps1 -Path "C:\MujProjekt" -RepoName "muj-projekt" -Private -Token "ghp_abc123"

.EXAMPLE
    .\New-GitRepo.ps1 -Path "C:\MujProjekt" -SkipGitHub
#>

param(
    [Parameter(Mandatory)][string]$Path,
    [string]$RepoName      = "",
    [string]$GitHubUser    = "XEXKX",
    [string]$Token         = $env:GITHUB_TOKEN,
    [switch]$Private,
    [switch]$SkipGitHub,
    [int]$DebounceSeconds  = 15
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── Helpers ──────────────────────────────────────────────────────────────────

function Write-Step($msg) { Write-Host "`n▶ $msg" -ForegroundColor Cyan }
function Write-OK($msg)   { Write-Host "  ✓ $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "  ⚠ $msg" -ForegroundColor Yellow }
function Write-Err($msg)  { Write-Host "  ✗ $msg" -ForegroundColor Red }

# ── Validace cesty ────────────────────────────────────────────────────────────

$Path = (Resolve-Path $Path).Path
if (-not (Test-Path $Path -PathType Container)) {
    Write-Err "Složka '$Path' neexistuje."
    exit 1
}
if ($RepoName -eq "") { $RepoName = (Split-Path $Path -Leaf) }

Write-Host ""
Write-Host "══════════════════════════════════════════" -ForegroundColor Magenta
Write-Host "  New-GitRepo: $RepoName" -ForegroundColor Magenta
Write-Host "  Složka: $Path" -ForegroundColor Gray
Write-Host "  GitHub: github.com/$GitHubUser/$RepoName" -ForegroundColor Gray
Write-Host "══════════════════════════════════════════" -ForegroundColor Magenta

# ── 1. Detekce typu projektu ──────────────────────────────────────────────────

Write-Step "Detekuji typ projektu..."

$hasNode     = (Test-Path "$Path\package.json") -or (Test-Path "$Path\node_modules")
$hasPython   = (Test-Path "$Path\requirements.txt") -or (Test-Path "$Path\pyproject.toml") -or
               (Get-ChildItem $Path -Filter "*.py" -File -ErrorAction SilentlyContinue | Select-Object -First 1)
$hasElectron = (Test-Path "$Path\electron") -or
               (Get-ChildItem $Path -Recurse -Depth 2 -Filter "electron" -EA SilentlyContinue | Select-Object -First 1)
$hasVenv     = (Test-Path "$Path\venv") -or (Test-Path "$Path\.venv")
$hasOllama   = (Test-Path "$Path\models\blobs")

$projectType = @()
if ($hasElectron) { $projectType += "Electron" }
if ($hasNode)     { $projectType += "Node.js" }
if ($hasPython)   { $projectType += "Python" }
if ($projectType.Count -eq 0) { $projectType += "Generic" }
Write-OK "Typ projektu: $($projectType -join ' + ')"

# ── 2. .gitignore ─────────────────────────────────────────────────────────────

Write-Step "Generuji .gitignore..."

$gitignorePath = "$Path\.gitignore"
$existingContent = ""
if (Test-Path $gitignorePath) {
    $existingContent = Get-Content $gitignorePath -Raw
    Write-Warn "Existující .gitignore nalezen — doplním chybějící záznamy."
}

$blocks = [System.Collections.Generic.List[string]]::new()

# Vždy přidej tyto bloky
$blocks.Add(@"
# OS / IDE
desktop.ini
.DS_Store
Thumbs.db
.idea/
.vscode/
*.swp
"@)

$blocks.Add(@"
# Env soubory (mohou obsahovat secrets)
.env
.env.local
.env.*.local
auth.json
"@)

if ($hasPython -or $hasVenv) {
    $blocks.Add(@"
# Python
__pycache__/
*.pyc
*.pyo
*.egg-info/
.mypy_cache/
.pytest_cache/
.ruff_cache/
venv/
.venv/
"@)
}

if ($hasNode -or $hasElectron) {
    $blocks.Add(@"
# Node / Electron (velké složky s balíčky)
node_modules/
dist/
build/
out/
.next/
.nuxt/
*.lock
package-lock.json
"@)
}

if ($hasElectron) {
    $blocks.Add(@"
# Electron build artefakty
electron/
app-builder-bin/
release/
"@)
}

if ($hasOllama) {
    $blocks.Add(@"
# Ollama modely (binární, stovky GB)
models/blobs/
models/manifests/
"@)
}

# Runtime data (časté ve všech projektech)
$blocks.Add(@"
# Runtime / cache / logy
*.log
*.db
*.db-wal
*.db-shm
*.sqlite
*.sqlite-wal
*.sqlite-shm
cache/
audio_cache/
image_cache/
sessions/
sandboxes/
memories/
state-snapshots/
__pycache__/
# Binární spustitelné soubory
*.exe
bin/
"@)

# Vyfiltruj záznamy, které již v .gitignore jsou
$newEntries = [System.Collections.Generic.List[string]]::new()
foreach ($block in $blocks) {
    $lines = $block -split "`n" | Where-Object { $_.Trim() -ne "" -and -not $_.StartsWith("#") }
    $missing = $lines | Where-Object { $existingContent -notmatch [regex]::Escape($_.Trim()) }
    if ($missing) { $newEntries.Add($block) }
}

if ($newEntries.Count -gt 0) {
    $separator = if ($existingContent -ne "") { "`n`n# --- přidáno New-GitRepo ---`n" } else { "" }
    $combined = $existingContent + $separator + ($newEntries -join "`n`n")
    Set-Content -Path $gitignorePath -Value $combined -Encoding UTF8
    Write-OK ".gitignore uložen: $gitignorePath"
} else {
    Write-OK ".gitignore již obsahuje vše potřebné."
}

# ── 3. Git init + commit ──────────────────────────────────────────────────────

Write-Step "Inicializuji git repozitář..."

Push-Location $Path

if (Test-Path ".git") {
    Write-Warn "Git repo již existuje — přeskakuji init."
} else {
    git init -b main | Out-Null
    git config user.email "elizejkuben1@gmail.com"
    git config user.name  "XEXKX"
    Write-OK "git init dokončen (větev: main)"
}

git add . 2>&1 | Out-Null
$status = git status --porcelain
if ($status) {
    $timestamp = Get-Date -Format "yyyy-MM-dd"
    git commit -m "Initial commit — $RepoName ($timestamp)" 2>&1 | Out-Null
    Write-OK "První commit vytvořen."
} else {
    Write-Warn "Žádné soubory ke commitu (vše ignorováno nebo repo prázdné)."
}

Pop-Location

# ── 4. GitHub repo přes API ───────────────────────────────────────────────────

if (-not $SkipGitHub) {
    Write-Step "Vytvářím GitHub repozitář '$RepoName'..."

    if (-not $Token) {
        Write-Err "Chybí GitHub token. Předej -Token 'ghp_...' nebo nastav proměnnou GITHUB_TOKEN."
        Write-Warn "Repozitář musíš vytvořit ručně na github.com/new, pak spusť skript znovu nebo nastav remote manuálně:"
        Write-Host "  git -C `"$Path`" remote add origin https://github.com/$GitHubUser/$RepoName.git" -ForegroundColor Gray
        Write-Host "  git -C `"$Path`" push -u origin main" -ForegroundColor Gray
    } else {
        try {
            $headers = @{
                Authorization = "Bearer $Token"
                Accept        = "application/vnd.github+json"
                "X-GitHub-Api-Version" = "2022-11-28"
            }
            $body = @{
                name        = $RepoName
                private     = [bool]$Private
                auto_init   = $false
                description = "Auto-created by New-GitRepo.ps1"
            } | ConvertTo-Json

            $response = Invoke-RestMethod -Uri "https://api.github.com/user/repos" `
                -Method Post -Headers $headers -Body $body -ContentType "application/json"

            $cloneUrl = $response.clone_url
            Write-OK "GitHub repo vytvořen: $cloneUrl"

            Push-Location $Path
            $remotes = git remote
            if ($remotes -contains "origin") {
                git remote set-url origin $cloneUrl
                Write-OK "Remote origin aktualizován."
            } else {
                git remote add origin $cloneUrl
                Write-OK "Remote origin přidán."
            }
            git push -u origin main 2>&1 | Write-Host
            Pop-Location
            Write-OK "První push na GitHub dokončen."
        } catch {
            Pop-Location -ErrorAction SilentlyContinue
            if ($_.Exception.Response.StatusCode -eq 422) {
                Write-Warn "Repozitář '$RepoName' již na GitHubu existuje. Nastavuji pouze remote..."
                Push-Location $Path
                $cloneUrl = "https://github.com/$GitHubUser/$RepoName.git"
                $remotes = git remote
                if ($remotes -contains "origin") {
                    git remote set-url origin $cloneUrl
                } else {
                    git remote add origin $cloneUrl
                }
                git push -u origin main 2>&1 | Write-Host
                Pop-Location
            } else {
                Write-Err "Chyba při vytváření GitHub repo: $_"
            }
        }
    }
}

# ── 5. Auto-push watcher skript ───────────────────────────────────────────────

Write-Step "Generuji auto-push watcher..."

$watcherPath = "$Path\_autopush.ps1"

$watcherScript = @"
# Auto-push watcher pro: $Path
# Generováno pomocí New-GitRepo.ps1

`$watchPath = "$Path"
`$debounceSeconds = $DebounceSeconds

`$watcher = New-Object System.IO.FileSystemWatcher
`$watcher.Path = `$watchPath
`$watcher.IncludeSubdirectories = `$true
`$watcher.EnableRaisingEvents = `$false

`$ignorePatterns = @('\.git', '__pycache__', '\.pyc$', '\.log$', '\.sqlite', '_autopush',
                    '\.venv', 'node_modules', '\.pytest_cache', '\.ruff_cache', 'electron')

function Should-Ignore(`$path) {
    foreach (`$pattern in `$script:ignorePatterns) {
        if (`$path -match `$pattern) { return `$true }
    }
    return `$false
}

function Start-CommitTimer {
    if (`$script:timer) { `$script:timer.Stop(); `$script:timer.Dispose() }
    `$script:timer = New-Object System.Timers.Timer
    `$script:timer.Interval = `$debounceSeconds * 1000
    `$script:timer.AutoReset = `$false
    Register-ObjectEvent -InputObject `$script:timer -EventName Elapsed -Action {
        `$ts = Get-Date -Format "yyyy-MM-dd HH:mm"
        Write-Host "[`$ts] Detekována změna — commituji..." -ForegroundColor Cyan
        Set-Location "$Path"
        `$status = git status --porcelain
        if (`$status) {
            git add .
            git commit -m "auto: `$ts"
            git push 2>&1 | Write-Host
            Write-Host "[`$ts] Push dokončen." -ForegroundColor Green
        }
    } | Out-Null
    `$script:timer.Start()
}

`$action = {
    `$p = `$Event.SourceEventArgs.FullPath
    if (-not (Should-Ignore `$p)) { Start-CommitTimer }
}

`$watcher.EnableRaisingEvents = `$true
Register-ObjectEvent -InputObject `$watcher -EventName Changed -Action `$action | Out-Null
Register-ObjectEvent -InputObject `$watcher -EventName Created -Action `$action | Out-Null
Register-ObjectEvent -InputObject `$watcher -EventName Deleted -Action `$action | Out-Null
Register-ObjectEvent -InputObject `$watcher -EventName Renamed -Action `$action | Out-Null

Write-Host "Auto-push spuštěn pro: `$watchPath (debounce: ${DebounceSeconds}s)" -ForegroundColor Green
while (`$true) { Wait-Event -Timeout 1 }
"@

Set-Content -Path $watcherPath -Value $watcherScript -Encoding UTF8
Write-OK "Watcher uložen: $watcherPath"

# ── 6. Windows Startup VBS ────────────────────────────────────────────────────

Write-Step "Přidávám do Windows Startup..."

$startupFolder = [Environment]::GetFolderPath("Startup")
$vbsName = "GitAutoPush-$RepoName.vbs"
$vbsPath = "$startupFolder\$vbsName"

$vbsContent = @"
Set objShell = CreateObject("WScript.Shell")
objShell.Run "pwsh.exe -WindowStyle Hidden -NonInteractive -ExecutionPolicy Bypass -File $watcherPath", 0, False
"@

Set-Content -Path $vbsPath -Value $vbsContent -Encoding ASCII
Write-OK "Startup záznam: $vbsPath"

# ── Hotovo ────────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "══════════════════════════════════════════" -ForegroundColor Magenta
Write-Host "  Hotovo! Shrnutí:" -ForegroundColor Magenta
Write-Host "  Repo:       $Path" -ForegroundColor Gray
if (-not $SkipGitHub -and $Token) {
    Write-Host "  GitHub:     https://github.com/$GitHubUser/$RepoName" -ForegroundColor Gray
}
Write-Host "  Auto-push:  $watcherPath (spustí se při příštím přihlášení)" -ForegroundColor Gray
Write-Host "  Spustit teď: pwsh -File `"$watcherPath`"" -ForegroundColor Yellow
Write-Host "══════════════════════════════════════════" -ForegroundColor Magenta
