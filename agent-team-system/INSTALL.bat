@echo off
REM Complete installation script for Agent Team System

echo ============================================================
echo Agent Team System - Complete Installation
echo ============================================================
echo.
echo This will:
echo   1. Check Python installation
echo   2. Install Python dependencies
echo   3. Initialize the agent system
echo   4. Build the standalone executable
echo   5. Create desktop shortcut (optional)
echo.
echo Press any key to continue or Ctrl+C to cancel...
pause >nul
echo.

REM ========== Check Python ==========
echo [1/5] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found!
    echo.
    echo Please install Python 3.9 or higher from:
    echo   https://www.python.org/downloads/
    echo.
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

python --version
echo Python OK!
echo.

REM ========== Install Dependencies ==========
echo [2/5] Installing Python dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)
echo Dependencies installed!
echo.

REM ========== Initialize System ==========
echo [3/5] Initializing agent team system...
python -m agent_team init
if errorlevel 1 (
    echo WARNING: Initialization had issues, but continuing...
)
echo System initialized!
echo.

REM ========== Build Executable ==========
echo [4/5] Building standalone executable...
echo This may take a few minutes...
python build_exe.py
if errorlevel 1 (
    echo WARNING: Executable build failed, but you can still use the Python version
    echo You can try building again later with BUILD_EXE.bat
) else (
    echo Executable built successfully!
)
echo.

REM ========== Create Shortcut ==========
echo [5/5] Create desktop shortcut?
set /p CREATE_SHORTCUT="Create shortcut? (Y/N): "
if /i "%CREATE_SHORTCUT%"=="Y" (
    echo Creating desktop shortcut...

    REM Create VBS script to create shortcut
    echo Set oWS = WScript.CreateObject("WScript.Shell") > CreateShortcut.vbs
    echo sLinkFile = oWS.SpecialFolders("Desktop") ^& "\Agent Team System.lnk" >> CreateShortcut.vbs
    echo Set oLink = oWS.CreateShortcut(sLinkFile) >> CreateShortcut.vbs
    echo oLink.TargetPath = "%CD%\dist\AgentTeamLauncher.exe" >> CreateShortcut.vbs
    echo oLink.WorkingDirectory = "%CD%" >> CreateShortcut.vbs
    echo oLink.Description = "Agent Team System Launcher" >> CreateShortcut.vbs
    echo oLink.Save >> CreateShortcut.vbs

    cscript //nologo CreateShortcut.vbs
    del CreateShortcut.vbs

    echo Desktop shortcut created!
)
echo.

echo ============================================================
echo Installation Complete!
echo ============================================================
echo.
echo You can now:
echo   1. Double-click 'LAUNCH.bat' to start the GUI
echo   2. Run 'dist\AgentTeamLauncher.exe' directly
echo   3. Use the desktop shortcut (if created)
echo   4. Read the documentation in 'manuals\' folder
echo.
echo Quick Start:
echo   1. Launch the application
echo   2. Click "Start System" on the Dashboard tab
echo   3. Submit tasks to agents
echo.
echo For help, see:
echo   - AGENT_TEAM_SYSTEM_README.md (overview)
echo   - manuals\OPERATIONS_MANUAL.md (detailed guide)
echo.

pause
