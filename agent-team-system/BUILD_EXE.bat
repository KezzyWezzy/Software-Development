@echo off
REM Build Agent Team System Launcher Executable
REM This creates a standalone .exe file for Windows

echo ============================================================
echo Agent Team System - Build Executable
echo ============================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found!
    echo Please install Python 3.9 or higher from python.org
    pause
    exit /b 1
)

echo Python found!
echo.

REM Install PyInstaller if needed
echo Installing/Updating PyInstaller...
python -m pip install --upgrade pyinstaller
echo.

REM Run build script
echo Building executable...
python build_exe.py

echo.
echo ============================================================
echo Build process complete!
echo ============================================================
echo.
echo Check the 'dist' folder for AgentTeamLauncher.exe
echo.

pause
