"""
Build Script for Agent Team System Executable

Creates a standalone Windows .exe file using PyInstaller.

Usage:
    python build_exe.py

Output:
    dist/AgentTeamLauncher.exe - Standalone executable
"""

import PyInstaller.__main__
import shutil
from pathlib import Path
import sys


def build_exe():
    """Build the executable"""
    print("=" * 60)
    print("Building Agent Team System Launcher Executable")
    print("=" * 60)
    print()

    # Get paths
    script_dir = Path(__file__).parent
    launcher_script = script_dir / "launcher_gui.py"

    if not launcher_script.exists():
        print(f"ERROR: launcher_gui.py not found at {launcher_script}")
        sys.exit(1)

    # PyInstaller arguments
    args = [
        str(launcher_script),
        '--name=AgentTeamLauncher',
        '--onefile',
        '--windowed',  # No console window
        '--icon=assets/icon.ico' if (script_dir / 'assets' / 'icon.ico').exists() else '--noconsole',

        # Add data files
        f'--add-data=core{Path.pathsep}core',
        f'--add-data=agents{Path.pathsep}agents',
        f'--add-data=systems{Path.pathsep}systems',
        f'--add-data=manuals{Path.pathsep}manuals',
        f'--add-data=config{Path.pathsep}config',
        f'--add-data=requirements.txt{Path.pathsep}.',

        # Hidden imports
        '--hidden-import=tkinter',
        '--hidden-import=tkinter.ttk',
        '--hidden-import=json',
        '--hidden-import=subprocess',
        '--hidden-import=threading',

        # Other options
        '--clean',
        f'--distpath={script_dir / "dist"}',
        f'--workpath={script_dir / "build"}',
        f'--specpath={script_dir}',
    ]

    print("Building executable with PyInstaller...")
    print(f"Script: {launcher_script}")
    print()

    try:
        PyInstaller.__main__.run(args)

        print()
        print("=" * 60)
        print("Build Complete!")
        print("=" * 60)
        print(f"Executable location: {script_dir / 'dist' / 'AgentTeamLauncher.exe'}")
        print()
        print("You can now:")
        print("1. Run dist/AgentTeamLauncher.exe directly")
        print("2. Copy the .exe anywhere and run it")
        print("3. Create a desktop shortcut")
        print()

    except Exception as e:
        print()
        print("=" * 60)
        print("Build Failed!")
        print("=" * 60)
        print(f"Error: {e}")
        print()
        print("Make sure PyInstaller is installed:")
        print("  pip install pyinstaller")
        sys.exit(1)


def install_pyinstaller():
    """Install PyInstaller if not available"""
    try:
        import PyInstaller
    except ImportError:
        print("PyInstaller not found. Installing...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("PyInstaller installed successfully!")


if __name__ == "__main__":
    install_pyinstaller()
    build_exe()
