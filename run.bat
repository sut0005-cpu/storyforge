@echo off
setlocal enabledelayedexpansion

:: ============================================================
::  StoryForge -- Windows one-click launcher
::  Campfire Studio Clone v2.0
:: ============================================================

title StoryForge Launcher

:: %~dp0 always ends with a backslash -- strip it for safe quoting
set "SCRIPT_DIR=%~dp0"
if "!SCRIPT_DIR:~-1!"=="\" set "SCRIPT_DIR=!SCRIPT_DIR:~0,-1!"

set "VENV_DIR=!SCRIPT_DIR!\venv"
set "PYTHON_EXEC=!VENV_DIR!\Scripts\python.exe"
set "REQ_FILE=!SCRIPT_DIR!\requirements.txt"
set "MAIN_FILE=!SCRIPT_DIR!\app.py"

echo.
echo  =============================================
echo   StoryForge -- Campfire Studio Clone v2.0
echo  =============================================
echo.

:: -- 1. Locate Python 3.10+ ------------------------------------------
echo  [1/4] Checking for Python 3.10+...
set "PYTHON_CMD="
for %%P in (python python3) do (
    if "!PYTHON_CMD!"=="" (
        where %%P >nul 2>&1
        if !errorlevel!==0 (
            for /f "tokens=2 delims= " %%V in ('%%P --version 2^>^&1') do (
                set "PY_VER=%%V"
            )
            :: Accept 3.10 and above (3.10, 3.11, ... 3.14, ...)
            echo !PY_VER! | findstr /r "^3\.[1-9][0-9]" >nul 2>&1
            if !errorlevel!==0 set "PYTHON_CMD=%%P"
        )
    )
)

if "!PYTHON_CMD!"=="" (
    echo.
    echo  [ERROR] Python 3.10 or newer was not found in PATH.
    echo          Download it from https://www.python.org/downloads/
    echo          Tick "Add Python to PATH" during install.
    echo.
    pause
    exit /b 1
)
echo         Found: !PYTHON_CMD! !PY_VER!

:: -- 2. Validate or rebuild the virtual environment ------------------
echo  [2/4] Setting up virtual environment...

:: Check venv has a working python.exe AND pip is available
set "VENV_OK=0"
if exist "!PYTHON_EXEC!" (
    "!PYTHON_EXEC!" --version >nul 2>&1
    if !errorlevel!==0 (
        if exist "!VENV_DIR!\Scripts\pip.exe" set "VENV_OK=1"
    )
)

if "!VENV_OK!"=="0" (
    if exist "!VENV_DIR!" (
        echo         Removing broken or incomplete venv...
        rmdir /s /q "!VENV_DIR!"
        if !errorlevel! neq 0 (
            echo  [ERROR] Could not remove old venv. Close any programs using
            echo          files inside !VENV_DIR! and try again.
            pause
            exit /b 1
        )
    )
    echo         Creating venv at !VENV_DIR!
    !PYTHON_CMD! -m venv "!VENV_DIR!"
    if !errorlevel! neq 0 (
        echo  [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    :: Bootstrap pip if the installer omitted it
    if not exist "!VENV_DIR!\Scripts\pip.exe" (
        echo         Bootstrapping pip via ensurepip...
        "!PYTHON_EXEC!" -m ensurepip --upgrade >nul 2>&1
        "!PYTHON_EXEC!" -m pip install --quiet --upgrade pip
    )
) else (
    echo         Venv OK -- skipping creation.
)

:: -- 3. Install / upgrade dependencies -------------------------------
echo  [3/4] Installing dependencies from requirements.txt...
if not exist "!REQ_FILE!" (
    echo  [ERROR] requirements.txt not found at !REQ_FILE!
    pause
    exit /b 1
)

"!PYTHON_EXEC!" -m pip install --quiet --upgrade pip
"!PYTHON_EXEC!" -m pip install --quiet -r "!REQ_FILE!"
if !errorlevel! neq 0 (
    echo.
    echo  [ERROR] Dependency installation failed.
    echo          - Check your internet connection.
    echo          - Try running as Administrator on managed machines.
    echo.
    pause
    exit /b 1
)
echo         Dependencies OK.

:: -- 4. Launch application -------------------------------------------
echo  [4/4] Launching StoryForge...
echo.
cd /d "!SCRIPT_DIR!"

"!PYTHON_EXEC!" "!MAIN_FILE!"
set "EXIT_CODE=!errorlevel!"

if !EXIT_CODE! neq 0 (
    echo.
    echo  [WARNING] StoryForge exited with code !EXIT_CODE!.
    echo            Check the console output above for errors.
    pause
)

endlocal
exit /b %EXIT_CODE%
