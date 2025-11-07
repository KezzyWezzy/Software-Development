@echo off
REM Quick launch script for Agent Team System

echo ============================================================
echo Agent Team System - Launcher
echo ============================================================
echo.

REM Check for executable
if exist "dist\AgentTeamLauncher.exe" (
    echo Launching GUI...
    start "" "dist\AgentTeamLauncher.exe"
) else (
    echo Executable not found. Launching Python GUI...
    python launcher_gui.py
    if errorlevel 1 (
        echo.
        echo ERROR: Could not launch GUI
        echo.
        echo Please build the executable first:
        echo   Run BUILD_EXE.bat
        echo.
        echo Or install dependencies:
        echo   pip install -r requirements.txt
        pause
    )
)
