@echo off
setlocal EnableExtensions
set "START_LOG=%TEMP%\PointQuote-startup.log"
set "FAIL_REASON="
>"%START_LOG%" echo [%date% %time%] PointQuote Windows startup began.

pushd "%~dp0"
if errorlevel 1 (
  set "FAIL_REASON=Windows could not open the local tool directory."
  goto failed
)

set /p "APP_VERSION="<"%~dp0VERSION"
if not defined APP_VERSION (
  set "FAIL_REASON=VERSION file is missing or empty."
  goto failed
)
>>"%START_LOG%" echo Version: %APP_VERSION%
>>"%START_LOG%" echo Source: %~dp0

rem Keep this file ASCII-only. Windows cmd may parse UTF-8 Chinese paths incorrectly.
set "LOCAL_DATA_ROOT=%LOCALAPPDATA%\TaiyuanPointQuote\data"
if not defined LOCALAPPDATA (
  set "FAIL_REASON=Windows local application data folder could not be located."
  goto failed
)
if exist "%~dp0data\" (
  set "POINT_QUOTE_USER_DATA_DIR=%~dp0data"
  set "DATA_MODE=portable tool-folder data"
) else (
  set "POINT_QUOTE_USER_DATA_DIR=%LOCAL_DATA_ROOT%"
  set "DATA_MODE=per-computer local data"
)
>>"%START_LOG%" echo Data mode: %DATA_MODE%
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0prepare-user-data.ps1" -SourceDataPath "%~dp0data" -DataRoot "%POINT_QUOTE_USER_DATA_DIR%"
if errorlevel 1 (
  set "FAIL_REASON=Local business data could not be prepared. Existing data was left untouched."
  goto failed
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0verify-windows-path.ps1" -Path "%~dp0." -DataRoot "%POINT_QUOTE_USER_DATA_DIR%"
if errorlevel 1 (
  set "FAIL_REASON=The tool and business data must be on local fixed disks before starting."
  goto failed
)
if not exist "%~dp0backend\app.py" (
  set "FAIL_REASON=Backend files are missing from the tool directory."
  goto failed
)
if not exist "%~dp0frontend\package.json" (
  set "FAIL_REASON=Frontend files are missing from the tool directory."
  goto failed
)

echo Closing old PointQuote processes on ports 8000 and 5173...
>>"%START_LOG%" echo Stopping old processes.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop-windows-runtime.ps1"
if errorlevel 1 (
  set "FAIL_REASON=Windows could not release ports 8000 and 5173."
  goto failed
)

set "RUNTIME=%USERPROFILE%\TaiyuanPointQuote"
set "VENV=%RUNTIME%\venv"
set "WEB=%RUNTIME%\frontend"
set "LOCK_FILE=%RUNTIME%\package-lock.sha256"
set "POINT_QUOTE_PLAYWRIGHT_ROOT=%WEB%\node_modules\playwright"

where npm >nul 2>&1
if errorlevel 1 (
  set "FAIL_REASON=Node.js 20 or newer is required, and npm must be available in PATH."
  goto failed
)

if not exist "%VENV%\Scripts\python.exe" (
  echo Creating the Windows Python environment...
  where py >nul 2>&1
  if not errorlevel 1 (
    py -3 -m venv "%VENV%"
  ) else (
    python -m venv "%VENV%"
  )
  if errorlevel 1 (
    set "FAIL_REASON=Python 3 could not create the local Windows environment."
    goto failed
  )
)

"%VENV%\Scripts\python.exe" -c "import fastapi, uvicorn, fitz, openpyxl, yaml, PIL, multipart, reportlab, httpx" >nul 2>&1
if errorlevel 1 (
  echo Installing Python dependencies...
  "%VENV%\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 (
    set "FAIL_REASON=Python dependencies could not be installed. Check the network and NAS permissions."
    goto failed
  )
)

echo Mirroring PointQuote V%APP_VERSION% web files from this local tool folder...
>>"%START_LOG%" echo Mirroring frontend files.
robocopy "%CD%\frontend" "%WEB%" /MIR /XD node_modules dist .git /XF *.tsbuildinfo >nul
if errorlevel 8 (
  set "FAIL_REASON=Frontend files could not be copied from this local tool folder."
  goto failed
)
if exist "%WEB%\node_modules\.vite" rmdir /s /q "%WEB%\node_modules\.vite"
if exist "%WEB%\dist" rmdir /s /q "%WEB%\dist"

set "LOCK_HASH="
for /f "usebackq delims=" %%H in (`powershell -NoProfile -Command "$sha = [Security.Cryptography.SHA256]::Create(); try { [BitConverter]::ToString($sha.ComputeHash([IO.File]::ReadAllBytes($env:WEB + '\package-lock.json'))).Replace('-', '') } finally { $sha.Dispose() }"`) do set "LOCK_HASH=%%H"
if not defined LOCK_HASH (
  set "FAIL_REASON=Could not calculate the web dependency lock hash."
  goto failed
)
set "INSTALLED_LOCK="
if exist "%LOCK_FILE%" set /p "INSTALLED_LOCK="<"%LOCK_FILE%"
if not exist "%WEB%\node_modules\.bin\vite.cmd" set "INSTALLED_LOCK="
if /I not "%LOCK_HASH%"=="%INSTALLED_LOCK%" (
  echo Installing or updating web dependencies...
  pushd "%WEB%"
  call npm ci
  if errorlevel 1 (
    popd
    set "FAIL_REASON=Web dependencies could not be installed. Check the npm error above."
    goto failed
  )
  popd
  >"%LOCK_FILE%" echo %LOCK_HASH%
)

set "PLAYWRIGHT_READY=%RUNTIME%\playwright-%LOCK_HASH%.ready"
if not exist "%PLAYWRIGHT_READY%" (
  echo Installing the PDF print engine...
  pushd "%WEB%"
  call npx playwright install chromium
  if errorlevel 1 (
    popd
    set "FAIL_REASON=The PDF print engine could not be installed. Check the network and npm output above."
    goto failed
  )
  popd
  >"%PLAYWRIGHT_READY%" echo ready
)

start "PointQuote API V%APP_VERSION%" "%~dp0run-windows-api.bat"
start "PointQuote Web V%APP_VERSION%" "%~dp0run-windows-web.bat"

echo Checking API and web versions...
>>"%START_LOG%" echo Waiting for API and web services.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0wait-windows-runtime.ps1" -ExpectedVersion "%APP_VERSION%" -TimeoutSeconds 120
if errorlevel 1 (
  set "FAIL_REASON=API or web service did not start. Check the two service windows for the detailed error."
  goto failed
)

echo Open http://127.0.0.1:5173/?version=%APP_VERSION%
start "" "http://127.0.0.1:5173/?version=%APP_VERSION%"
>>"%START_LOG%" echo [%date% %time%] Startup completed successfully.
exit /b 0

:failed
if not defined FAIL_REASON set "FAIL_REASON=Startup or version verification failed."
>>"%START_LOG%" echo [%date% %time%] ERROR: %FAIL_REASON%
echo.
echo ERROR: %FAIL_REASON%
echo Startup log: %START_LOG%
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop-windows-runtime.ps1" >nul 2>&1
echo Keep this window open, or send the startup log for troubleshooting.
pause
exit /b 1
