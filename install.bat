@echo off
rem LALA one-click install (Windows). Double-click me.
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ===============================================
echo   LALA - one-click install
echo ===============================================

rem --- find python: `python` or the `py` launcher ---
set "PY="
where python >nul 2>&1 && set "PY=python"
if not defined PY (
  where py >nul 2>&1 && set "PY=py -3"
)
if not defined PY (
  echo ✖ Python not found. Fix ONE of these, then re-run:
  echo    1^) winget install Python.Python.3.12
  echo    2^) python.org download — CHECK "Add python.exe to PATH"
  echo    3^) Microsoft Store → search "Python 3.12" → Get
  echo   Then CLOSE this window and open a NEW one.
  pause
  exit /b 1
)
echo → using Python launcher: %PY%

if not exist .venv (
  echo → creating .venv …
  %PY% -m venv .venv
)

echo → installing Python dependencies (STT/TTS/VAD/wake; heavy ones optional) …
.venv\Scripts\python -m pip install -q --upgrade pip
.venv\Scripts\python -m pip install -q -r assistant\requirements.txt

rem --- launcher + shortcuts ---
set "LALABAT=%~dp0lala.bat"
> "%LALABAT%" (
  echo @echo off
  echo cd /d "%~dp0"
  echo "%~dp0.venv\Scripts\python" -m assistant %%*
)
set "SM=%APPDATA%\Microsoft\Windows\Start Menu\Programs\LALA"
if not exist "%SM%" mkdir "%SM%"
powershell -NoProfile -Command "$w=New-Object -ComObject WScript.Shell;$s=$w.CreateShortcut('%SM%\LALA.lnk');$s.TargetPath='%LALABAT%';$s.WorkingDirectory='%~dp0';$s.Save();$d=$w.CreateShortcut('%USERPROFILE%\Desktop\LALA.lnk');$d.TargetPath='%LALABAT%';$d.WorkingDirectory='%~dp0';$d.Save()"
echo → Start Menu + Desktop shortcuts created

set /p AUTO="Start LALA at login? [y/N] "
if /i "%AUTO%"=="y" (
  reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v LALA /t REG_SZ /d "\"%LALABAT%\"" /f >nul
  echo → autostart on
)

set /p EL="Install Electron UI too? needs Node 18+ [y/N] "
if /i "%EL%"=="y" (
  where npm >nul 2>&1 && ( call npm install -q --no-audit --no-fund & echo → Electron UI ready: npm start ) || echo   (npm not found — skipped)
)

echo ===============================================
echo   ✔ installed — launching LALA …
echo     keys later via: .venv\Scripts\python -m assistant --keys
echo ===============================================
start "" "%LALABAT%"
pause
