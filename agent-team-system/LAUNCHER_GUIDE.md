# Agent Team System - Launcher & Executable Guide

Complete guide for the GUI launcher and creating standalone executables.

---

## 🚀 Quick Start

### For End Users (Just Want to Use It)

**Option 1: Use Pre-Built Executable** (Recommended)
```batch
# Simply run the launcher
LAUNCH.bat

# Or double-click
dist\AgentTeamLauncher.exe
```

**Option 2: Complete Installation**
```batch
# Run the complete installer
INSTALL.bat

# This will:
# 1. Install all dependencies
# 2. Initialize the system
# 3. Build the executable
# 4. Create desktop shortcut
```

### For Developers (Want to Build)

```batch
# Build the executable yourself
BUILD_EXE.bat

# Or manually
python build_exe.py
```

---

## 📦 What's Included

### 1. **GUI Launcher** (`launcher_gui.py`)

A complete graphical interface with:

#### **Dashboard Tab**
- Start/Stop system with autonomy level selection
- Quick actions (status, backup, workspace, frontend, docs, health check)
- System information display

#### **Agents Tab**
- View all available agents
- Agent details and status
- Submit tasks (coming soon)
- View agent-specific logs

#### **Configuration Tab**
- Workspace directory settings
- Frontend directory settings
- Auto-launch frontend option
- System preferences (backups, reminders, logging)
- Save/load configuration

#### **Logs Tab**
- Real-time log viewing
- Filter by log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Color-coded log levels
- Export logs to file
- Search and filter

#### **Setup Tab**
- Installation status check
- Install dependencies
- Initialize system
- Download frontend (coming soon)
- Install frontend dependencies
- Run all setup steps
- Progress tracking

### 2. **Build System**

#### **build_exe.py**
Python script that creates standalone executable using PyInstaller:
- Single-file executable
- No console window (windowed mode)
- Includes all necessary files
- Automatic dependency detection
- Custom icon support

#### **BUILD_EXE.bat**
Windows batch file for easy building:
- Checks Python installation
- Installs/updates PyInstaller
- Runs build script
- Shows results

### 3. **Installation System**

#### **INSTALL.bat**
Complete automated installation:
1. Verifies Python installation
2. Installs Python dependencies
3. Initializes agent system
4. Builds standalone executable
5. Creates desktop shortcut (optional)

#### **LAUNCH.bat**
Quick launcher:
- Looks for executable first
- Falls back to Python if exe not found
- Handles errors gracefully

---

## 🔧 Building the Executable

### Prerequisites

- Python 3.9 or higher
- Windows (for .exe, other platforms supported)
- ~500MB disk space for build

### Method 1: Use Batch File (Easiest)

```batch
# Double-click or run:
BUILD_EXE.bat
```

This will:
1. Check Python installation
2. Install PyInstaller automatically
3. Build the executable
4. Show output location

### Method 2: Manual Build

```batch
# Install PyInstaller
pip install pyinstaller

# Run build script
python build_exe.py
```

### Method 3: Advanced (Custom Options)

```batch
# Direct PyInstaller command with custom options
pyinstaller launcher_gui.py ^
    --name="AgentTeamLauncher" ^
    --onefile ^
    --windowed ^
    --icon=assets/icon.ico ^
    --add-data="core;core" ^
    --add-data="agents;agents" ^
    --add-data="systems;systems" ^
    --add-data="manuals;manuals" ^
    --add-data="config;config"
```

### Build Output

After building, you'll find:

```
agent-team-system/
├── dist/
│   └── AgentTeamLauncher.exe    # Standalone executable (~50-100MB)
├── build/                        # Temporary build files (can delete)
├── AgentTeamLauncher.spec       # PyInstaller spec file
```

---

## 🖥️ Using the GUI Launcher

### Starting the System

1. **Launch the GUI**
   - Run `LAUNCH.bat`, or
   - Double-click `dist/AgentTeamLauncher.exe`, or
   - Run `python launcher_gui.py`

2. **Select Autonomy Level**
   - **Manual**: Every action requires approval (safest)
   - **Semi-Auto**: Pre-approved actions run automatically (recommended)
   - **Full Auto**: Maximum automation (advanced users)

3. **Click "Start System"**
   - System starts in background
   - Monitor logs in real-time
   - Status bar shows current state

### Quick Actions

**📊 View Status**: Check current system state and agent status

**💾 Create Backup**: Create manual backup with timestamp

**📁 Open Workspace**: Open workspace folder in file explorer

**🌐 Launch Frontend**: Start the frontend application
   - Automatically detects npm projects
   - Falls back to static HTML
   - Auto-launch option available

**📖 Open Documentation**: Open manuals folder

**🔧 Health Check**: Run system health diagnostics

### Managing Agents

1. Go to **Agents** tab
2. View list of available agents
3. Select agent to see details
4. Submit tasks (CLI for now, GUI coming soon)
5. View agent-specific logs

### Configuration

1. Go to **Configuration** tab
2. Set workspace directory
3. Set frontend directory
4. Configure preferences:
   - Auto-launch frontend
   - Automatic backups
   - Best practice reminders
   - Detailed logging
5. Click **Save Configuration**

### Viewing Logs

1. Go to **Logs** tab
2. Select log level to filter
3. Click **Refresh Logs** to update
4. **Export Logs** to save to file
5. **Clear Display** to clean up

### Setup & Installation

1. Go to **Setup** tab
2. View installation status
3. Run setup steps:
   - **Install Dependencies**: Python packages
   - **Initialize System**: Create workspace structure
   - **Download Frontend**: Get pre-made frontend (coming soon)
   - **Install Frontend Dependencies**: npm install
   - **Run All Setup Steps**: Complete automated setup

---

## 🌐 Frontend Integration

The launcher supports launching pre-made frontend applications automatically.

### Supported Frontend Types

#### 1. **npm/Node.js Projects**
```
frontend/
├── package.json
├── src/
└── public/
```

Launcher will run: `npm start`

#### 2. **Static HTML Sites**
```
frontend/
├── index.html
├── css/
└── js/
```

Launcher will open `index.html` in browser

### Setting Up Frontend

**Option 1: Configuration Tab**
1. Open launcher
2. Go to Configuration tab
3. Click "Browse" next to Frontend Directory
4. Select your frontend folder
5. Enable "Auto-launch frontend with system"
6. Save configuration

**Option 2: Manual**
1. Place your frontend in `frontend/` directory
2. Launcher will auto-detect it

### Frontend Requirements

For npm projects:
```bash
cd frontend
npm install
```

The launcher's Setup tab can do this automatically.

### Auto-Launch

Enable in Configuration tab:
- ☑ Auto-launch frontend with system

Frontend will start 3 seconds after system starts.

---

## 🔧 Advanced Configuration

### Custom Icon

1. Create `assets/icon.ico` file
2. Rebuild executable:
   ```batch
   BUILD_EXE.bat
   ```

### Launcher Configuration File

Located at: `launcher_config.json`

```json
{
  "workspace_dir": "C:/path/to/workspace",
  "frontend_dir": "C:/path/to/frontend",
  "auto_launch_frontend": true,
  "auto_backup": true,
  "show_reminders": true,
  "enable_logging": true,
  "autonomy_level": "semi_auto"
}
```

Edit manually or use Configuration tab.

### Adding Custom Frontend Templates

Create directory structure:
```
frontend-templates/
├── industrial-scada/
│   ├── package.json
│   └── src/
├── business-dashboard/
│   ├── package.json
│   └── src/
└── engineering-tool/
    ├── package.json
    └── src/
```

Future versions will support template selection in GUI.

---

## 📋 Distribution

### Distributing Your Executable

After building, you can distribute:

**Files to Include:**
```
dist/
├── AgentTeamLauncher.exe      # Main executable
└── README.txt                  # Quick start guide
```

**User Requirements:**
- Windows 7 or later
- ~100MB disk space
- No Python installation needed!

### Creating an Installer

**Option 1: Use Inno Setup** (Recommended)

1. Download Inno Setup: https://jrsoftware.org/isinfo.php
2. Create installer script: `installer.iss`
3. Compile to create setup.exe

**Option 2: Use NSIS**

1. Download NSIS: https://nsis.sourceforge.io/
2. Create installer script
3. Compile

**Example Inno Setup Script:**
```iss
[Setup]
AppName=Agent Team System
AppVersion=1.0.0
DefaultDirName={pf}\AgentTeamSystem
DefaultGroupName=Agent Team System
OutputDir=installer_output
OutputBaseFilename=AgentTeamSystem_Setup

[Files]
Source: "dist\AgentTeamLauncher.exe"; DestDir: "{app}"
Source: "manuals\*"; DestDir: "{app}\manuals"; Flags: recursesubdirs

[Icons]
Name: "{group}\Agent Team System"; Filename: "{app}\AgentTeamLauncher.exe"
Name: "{commondesktop}\Agent Team System"; Filename: "{app}\AgentTeamLauncher.exe"
```

---

## 🐛 Troubleshooting

### Build Issues

**"PyInstaller not found"**
```batch
pip install pyinstaller
```

**"Module not found during build"**
Add to `build_exe.py`:
```python
'--hidden-import=missing_module_name',
```

**"Executable is too large"**
Use `--onedir` instead of `--onefile` in build script.

### Runtime Issues

**"System not starting"**
1. Check logs in Logs tab
2. Verify workspace directory exists
3. Run health check
4. Try initializing again in Setup tab

**"Frontend not launching"**
1. Verify frontend directory path
2. Check if `package.json` exists (for npm)
3. Install frontend dependencies in Setup tab
4. Try manual launch: `cd frontend && npm start`

**"Dependencies missing"**
1. Go to Setup tab
2. Click "Install Dependencies"
3. Wait for completion
4. Try starting system again

### GUI Issues

**"Window doesn't open"**
- Executable might be running in background
- Check Task Manager for `AgentTeamLauncher.exe`
- Kill process and try again

**"Logs not showing"**
- Click "Refresh Logs"
- Check log level filter
- Verify logging is enabled in Configuration

---

## 🔄 Updates & Maintenance

### Updating the Launcher

1. Pull latest code from git
2. Rebuild executable:
   ```batch
   BUILD_EXE.bat
   ```
3. Replace old exe with new one

### Updating Agent System

1. Go to Setup tab
2. Click "Install Dependencies" (updates packages)
3. Restart system

### Backup Before Updates

Always create backup before major updates:
```batch
# In launcher
Dashboard → Create Backup

# Or via CLI
python -m agent_team backup create --label "before_update"
```

---

## 📚 Additional Resources

- **Main README**: `../AGENT_TEAM_SYSTEM_README.md`
- **Operations Manual**: `manuals/OPERATIONS_MANUAL.md`
- **Development Manual**: `manuals/DEVELOPMENT_MANUAL.md`
- **Best Practices**: `manuals/BEST_PRACTICES.md`

---

## 🎯 Next Steps

1. **Build your executable**
   ```batch
   BUILD_EXE.bat
   ```

2. **Launch the GUI**
   ```batch
   LAUNCH.bat
   ```

3. **Configure your workspace**
   - Set workspace directory
   - Set frontend directory
   - Configure preferences

4. **Start the system**
   - Select autonomy level
   - Click "Start System"
   - Monitor in real-time

5. **Launch your frontend** (if available)
   - Click "Launch Frontend"
   - Or enable auto-launch

---

**The launcher makes the Agent Team System accessible to everyone, not just Python developers!**

*Version 1.0.0 - Complete GUI launcher with executable support*
