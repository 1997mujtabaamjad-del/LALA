# LALA — Windows one-line installer.
#   Direct:  powershell -ExecutionPolicy Bypass -File scripts\install.ps1
#   One-liner (any PC, no git needed):
#   iwr https://raw.githubusercontent.com/1997mujtabaamjad-del/LALA/arena/019fcde4-lala/scripts/install.ps1 -UseBasicParsing | iex
$ErrorActionPreference = 'Stop'
$branch = 'arena/019fcde4-lala'
$repo   = '1997mujtabaamjad-del/LALA'
$dir    = "$HOME\LALA"

function Has($c) { Get-Command $c -ErrorAction SilentlyContinue }

Write-Host "==============================================="
Write-Host "  LALA one-click install (Windows)"
Write-Host "==============================================="

# 1. get the code (git if present, else zip download)
if (!(Test-Path "$dir\install.bat")) {
    if (Has git) {
        Write-Host "-> cloning $branch …"
        git clone -q --branch $branch "https://github.com/$repo.git" $dir
    } else {
        Write-Host "-> downloading $branch zip …"
        $zip = "$env:TEMP\lala.zip"
        Invoke-WebRequest "https://github.com/$repo/archive/refs/heads/$branch.zip" -OutFile $zip -UseBasicParsing
        Expand-Archive $zip -DestinationPath "$env:TEMP\lala" -Force
        if (Test-Path $dir) { Remove-Item $dir -Recurse -Force }
        Move-Item "$env:TEMP\lala\LALA-*" $dir -Force
    }
}
Set-Location $dir

# 2. python env + deps  (accepts `python` OR the `py` launcher)
$script:usepy = $false
if (Has python3.14) { }
elseif (Has py) { $script:usepy = $true }
elseif (Has python) { }
else {
    if (Has winget) {
        Write-Host "-> Python not found — installing Python 3.12 via winget …"
        winget install -e --id Python.Python.3.12 --silent --accept-source-agreements --accept-package-agreements
        $pyDir = "$env:LOCALAPPDATA\Programs\Python\Python312"
        $env:PATH = "$pyDir;$pyDir\Scripts;$env:PATH"
    }
}
if (!(Has python3.14) -and !(Has py) -and !(Has python)) {
    Write-Host "✖ Python still not found. Fix it in ONE of these ways, then re-run:"
    Write-Host "    1) winget install Python.Python.3.12"
    Write-Host "    2) python.org download — CHECK 'Add python.exe to PATH'"
    Write-Host "    3) Microsoft Store → search 'Python 3.12' → Get"
    Write-Host "  Then CLOSE this PowerShell and open a NEW one."
    Start-Process "https://www.python.org/downloads/"
    pause; exit 1
}
function prun { if ($script:usepy) { $t = & py -3.14 --version 2>$null; if ($LASTEXITCODE -eq 0) { & py -3.14 @args } else { & py -3 @args } } elseif (Has python3.14) { & python3.14 @args } else { & python @args } }
if (!(Test-Path .venv)) { Write-Host "-> creating .venv …"; prun -m venv .venv }
Write-Host "-> installing core deps …"
.\.venv\Scripts\python -m pip install -q --upgrade pip
.\.venv\Scripts\python -m pip install -q numpy requests sounddevice websocket-client
Write-Host "-> installing voice/AI backends (large downloads, each optional) …"
foreach ($pkg in 'onnxruntime','silero-vad','openwakeword','faster-whisper','piper-tts') {
    & .\.venv\Scripts\python -m pip install -q $pkg 2>$null
    if ($LASTEXITCODE -ne 0) { Write-Host "   ! $pkg skipped — LALA still works without it" }
}

# 3. launcher + shortcuts
$lalaBat = "$dir\lala.bat"
"@echo off`r`ncd /d `"$dir`"`r`n`"$dir\.venv\Scripts\python`" -m assistant %*" | Out-File $lalaBat -Encoding ascii
$sm = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\LALA"
New-Item -ItemType Directory -Path $sm -Force | Out-Null
$wsh = New-Object -ComObject WScript.Shell
$s = $wsh.CreateShortcut("$sm\LALA.lnk");  $s.TargetPath = $lalaBat; $s.Arguments = '--app'; $s.WorkingDirectory = $dir; $s.Save()
$d = $wsh.CreateShortcut("$HOME\Desktop\LALA.lnk"); $d.TargetPath = $lalaBat; $d.Arguments = '--app'; $d.WorkingDirectory = $dir; $d.Save()
Write-Host "-> Start Menu + Desktop shortcuts created (they open the full app in your browser)"

# 4. optional extras
$ans = Read-Host "Start LALA at login? (y/N)"
if ($ans -eq 'y') {
    New-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name LALA -Value "`"$lalaBat`"" -PropertyType String -Force | Out-Null
    Write-Host "-> autostart on"
}
$el = Read-Host "Install Electron UI too? needs Node 18+ (y/N)"
if ($el -eq 'y' -and (Has npm)) {
    npm install -q --no-audit --no-fund
    Write-Host "-> Electron UI ready: npm start"
}

Write-Host "==============================================="
Write-Host "  ✔ installed — launching LALA (browser opens) …"
Write-Host "    (keys later via: .\.venv\Scripts\python -m assistant --keys)"
Write-Host "==============================================="
Start-Process $lalaBat -ArgumentList '--app'
