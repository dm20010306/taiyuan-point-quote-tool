@echo off
pushd "%~dp0"
if exist "%~dp0data\" (
  set "POINT_QUOTE_USER_DATA_DIR=%~dp0data"
) else (
  set "POINT_QUOTE_USER_DATA_DIR=%LOCALAPPDATA%\TaiyuanPointQuote\data"
)
PowerShell -NoProfile -ExecutionPolicy Bypass -File "%~dp0verify-windows-path.ps1" -Path "%~dp0." -DataRoot "%POINT_QUOTE_USER_DATA_DIR%"
if errorlevel 1 exit /b 1
set "PYTHONPYCACHEPREFIX=%TEMP%\pointquote-pycache"
set "POINT_QUOTE_LOG_DIR=%LOCALAPPDATA%\TaiyuanPointQuote\logs"
set "POINT_QUOTE_PLAYWRIGHT_ROOT=%USERPROFILE%\TaiyuanPointQuote\frontend\node_modules\playwright"
echo Business data folder: %POINT_QUOTE_USER_DATA_DIR%
"%USERPROFILE%\TaiyuanPointQuote\venv\Scripts\python.exe" -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
echo API stopped. Check any error message above.
pause
