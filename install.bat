@echo off
rem ============================================================
rem  LALA one-click install (Windows). Double-click me.
rem  - installs Python for you if missing (winget)
rem  - installs LALA's brain + voice components
rem  - puts a LALA shortcut on your Desktop + Start Menu
rem  - LALA opens as an app in your browser (no Node needed)
rem ============================================================
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ===============================================
echo   LALA - one-click install
echo ===============================================

rem ---------- 1) find or install Python ----------
set "PY="
where python >nul 2>&1 && set "PY=python"
if not defined PY (
  where py >nul 2>&1 && set "PY=py -3"
)

if not defined PY (
  where winget >nul 2>&1 && (
    echo Python not found - installing it now via winget...
    winget install -e --id Python.Python.3.12 --silent --accept-source-agreements --accept-package-agreements
    set "PATH=%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts;!PATH!"
    where python >nul 2>&1 && set "PY=python"
  )
)

if not defined PY (
  echo.
  echo Could not install Python automatically.
  echo Opening python.org - click the big Download button, run the
  echo installer and CHECK "Add python.exe to PATH", then double-click
  echo install.bat again.
  start "" "https://www.python.org/downloads/"
  pause
  exit /b 1
)
echo = using Python launcher: %PY%

rem ---------- 2) virtual environment ----------
if not exist .venv (
  echo = creating .venv ...
  %PY% -m venv .venv
)
.venv\Scripts\python -m pip install -q --upgrade pip

rem ---------- 3) dependencies: core first, heavy ones best-effort ----------
echo = installing core dependencies ...
.venv\Scripts\python -m pip install -q numpy requests sounddevice websocket-client
if errorlevel 1 (
  echo   ^! core install hit a problem - retrying once ...
  .venv\Scripts\python -m pip install numpy requests sounddevice websocket-client
)

echo = installing voice/AI backends ^(large downloads, each optional^) ...
for %%P in (onnxruntime silero-vad openwakeword faster-whisper piper-tts) do (
  .venv\Scripts\python -m pip install -q %%P 2>nul || echo   ^! %%P skipped - LALA still works without it
)

rem ---------- 4) launcher + shortcuts ----------
set "LALABAT=%~dp0lala.bat"
> "%LALABAT%" (
  echo @echo off
  echo cd /d "%~dp0"
  echo "%~dp0.venv\Scripts\python" -m assistant %%*
)

set "SM=%APPDATA%\Microsoft\Windows\Start Menu\Programs\LALA"
if not exist "%SM%" mkdir "%SM%"
powershell -NoProfile -Command "$w=New-Object -ComObject WScript.Shell;$s=$w.CreateShortcut('%SM%\LALA.lnk');$s.TargetPath='%LALABAT%';$s.Arguments='--app';$s.WorkingDirectory='%~dp0';$s.Save();$d=$w.CreateShortcut('%USERPROFILE%\Desktop\LALA.lnk');$d.TargetPath='%LALABAT%';$d.Arguments='--app';$d.WorkingDirectory='%~dp0';$d.Save();$a=$w.CreateShortcut('%USERPROFILE%\Desktop\LALA Desktop App.lnk');$a.TargetPath='%~dp0LALA-APP.bat';$a.WorkingDirectory='%~dp0';$a.Save()"
echo = Shortcuts created: "LALA" (browser app) + "LALA Desktop App" (own window)

set /p AUTO="Start LALA automatically when you log in? [y/N] "
if /i "%AUTO%"=="y" (
  reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v LALA /t REG_SZ /d "\"%LALABAT%\" --app" /f >nul
  echo = autostart on
)

set /p EL="Also install the Electron desktop UI? (needs Node 18+; say n if unsure) [y/N] "
if /i "%EL%"=="y" (
  where npm >nul 2>&1 && ( call npm install -q --no-audit --no-fund & echo = Electron UI ready: npm start ) || echo   ^(npm not found - skipped, the browser app works anyway^)
)

echo ===============================================
echo   ^ installed - launching LALA ...
echo     (a browser window opens; allow the microphone
echo      when Chrome asks, and talk to me)
echo     keys later:  .venv\Scripts\python -m assistant --keys
echo ===============================================
start "" "%LALABAT%" --app
pause
