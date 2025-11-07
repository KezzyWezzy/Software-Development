"""
Agent Team System - GUI Launcher

Graphical interface for launching and managing the agent team system.
Can be compiled to standalone .exe using PyInstaller.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import json
import subprocess
import threading
import sys
from pathlib import Path
from datetime import datetime
import os


class AgentTeamLauncher(tk.Tk):
    """Main launcher window for the Agent Team System"""

    def __init__(self):
        super().__init__()

        self.title("Agent Team System - Launcher v1.0.0")
        self.geometry("900x700")
        self.resizable(True, True)

        # Set icon if available
        try:
            icon_path = Path(__file__).parent / "assets" / "icon.ico"
            if icon_path.exists():
                self.iconbitmap(str(icon_path))
        except:
            pass

        # System state
        self.system_running = False
        self.system_process = None
        self.workspace_dir = Path.cwd() / "agent-team-system"
        self.frontend_dir = Path.cwd() / "frontend"

        # Setup UI
        self.setup_ui()
        self.check_installation()

    def setup_ui(self):
        """Setup the user interface"""
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Create tabs
        self.create_dashboard_tab()
        self.create_agents_tab()
        self.create_configuration_tab()
        self.create_logs_tab()
        self.create_setup_tab()

        # Status bar
        self.status_bar = ttk.Label(
            self,
            text="System Status: Not Running",
            relief=tk.SUNKEN,
            anchor=tk.W
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def create_dashboard_tab(self):
        """Create the main dashboard tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Dashboard")

        # Title
        title = ttk.Label(
            tab,
            text="Agent Team System",
            font=("Arial", 20, "bold")
        )
        title.pack(pady=20)

        # System controls frame
        controls_frame = ttk.LabelFrame(tab, text="System Controls", padding=10)
        controls_frame.pack(fill=tk.X, padx=20, pady=10)

        # Autonomy level selection
        autonomy_frame = ttk.Frame(controls_frame)
        autonomy_frame.pack(fill=tk.X, pady=5)

        ttk.Label(autonomy_frame, text="Autonomy Level:").pack(side=tk.LEFT, padx=5)

        self.autonomy_var = tk.StringVar(value="semi_auto")
        autonomy_options = [
            ("Manual (Safest)", "manual"),
            ("Semi-Auto (Recommended)", "semi_auto"),
            ("Full Auto (Advanced)", "full_auto")
        ]

        for text, value in autonomy_options:
            ttk.Radiobutton(
                autonomy_frame,
                text=text,
                variable=self.autonomy_var,
                value=value
            ).pack(side=tk.LEFT, padx=10)

        # Control buttons
        buttons_frame = ttk.Frame(controls_frame)
        buttons_frame.pack(pady=10)

        self.start_button = ttk.Button(
            buttons_frame,
            text="▶ Start System",
            command=self.start_system,
            width=20
        )
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = ttk.Button(
            buttons_frame,
            text="⏹ Stop System",
            command=self.stop_system,
            state=tk.DISABLED,
            width=20
        )
        self.stop_button.pack(side=tk.LEFT, padx=5)

        ttk.Button(
            buttons_frame,
            text="🔄 Restart",
            command=self.restart_system,
            width=20
        ).pack(side=tk.LEFT, padx=5)

        # Quick actions frame
        actions_frame = ttk.LabelFrame(tab, text="Quick Actions", padding=10)
        actions_frame.pack(fill=tk.X, padx=20, pady=10)

        actions = [
            ("📊 View Status", self.view_status),
            ("💾 Create Backup", self.create_backup),
            ("📁 Open Workspace", self.open_workspace),
            ("🌐 Launch Frontend", self.launch_frontend),
            ("📖 Open Documentation", self.open_documentation),
            ("🔧 Health Check", self.run_health_check),
        ]

        for i, (text, command) in enumerate(actions):
            row = i // 3
            col = i % 3
            ttk.Button(
                actions_frame,
                text=text,
                command=command,
                width=25
            ).grid(row=row, column=col, padx=5, pady=5)

        # System info frame
        info_frame = ttk.LabelFrame(tab, text="System Information", padding=10)
        info_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        self.info_text = scrolledtext.ScrolledText(
            info_frame,
            height=10,
            wrap=tk.WORD,
            font=("Courier", 9)
        )
        self.info_text.pack(fill=tk.BOTH, expand=True)

        # Update info
        self.update_system_info()

    def create_agents_tab(self):
        """Create the agents management tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Agents")

        # Available agents list
        agents_frame = ttk.LabelFrame(tab, text="Available Agents", padding=10)
        agents_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Agents listbox
        list_frame = ttk.Frame(agents_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.agents_listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            font=("Courier", 10)
        )
        self.agents_listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.agents_listbox.yview)

        # Agent details
        details_frame = ttk.LabelFrame(tab, text="Agent Details", padding=10)
        details_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.agent_details = scrolledtext.ScrolledText(
            details_frame,
            height=8,
            wrap=tk.WORD,
            font=("Courier", 9)
        )
        self.agent_details.pack(fill=tk.BOTH, expand=True)

        # Agent actions
        actions_frame = ttk.Frame(tab)
        actions_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Button(
            actions_frame,
            text="Submit Task",
            command=self.submit_task
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            actions_frame,
            text="View Agent Logs",
            command=self.view_agent_logs
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            actions_frame,
            text="Refresh Agents",
            command=self.refresh_agents
        ).pack(side=tk.LEFT, padx=5)

        # Load agents
        self.refresh_agents()

    def create_configuration_tab(self):
        """Create configuration tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Configuration")

        # Workspace configuration
        workspace_frame = ttk.LabelFrame(tab, text="Workspace Settings", padding=10)
        workspace_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(workspace_frame, text="Workspace Directory:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.workspace_entry = ttk.Entry(workspace_frame, width=50)
        self.workspace_entry.insert(0, str(self.workspace_dir))
        self.workspace_entry.grid(row=0, column=1, padx=5)

        ttk.Button(
            workspace_frame,
            text="Browse",
            command=self.browse_workspace
        ).grid(row=0, column=2, padx=5)

        # Frontend configuration
        frontend_frame = ttk.LabelFrame(tab, text="Frontend Settings", padding=10)
        frontend_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(frontend_frame, text="Frontend Directory:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.frontend_entry = ttk.Entry(frontend_frame, width=50)
        self.frontend_entry.insert(0, str(self.frontend_dir))
        self.frontend_entry.grid(row=0, column=1, padx=5)

        ttk.Button(
            frontend_frame,
            text="Browse",
            command=self.browse_frontend
        ).grid(row=0, column=2, padx=5)

        self.auto_launch_frontend = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frontend_frame,
            text="Auto-launch frontend with system",
            variable=self.auto_launch_frontend
        ).grid(row=1, column=0, columnspan=3, sticky=tk.W, pady=5)

        # System preferences
        prefs_frame = ttk.LabelFrame(tab, text="System Preferences", padding=10)
        prefs_frame.pack(fill=tk.X, padx=10, pady=10)

        self.auto_backup = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            prefs_frame,
            text="Enable automatic backups",
            variable=self.auto_backup
        ).pack(anchor=tk.W, pady=2)

        self.show_reminders = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            prefs_frame,
            text="Show best practice reminders",
            variable=self.show_reminders
        ).pack(anchor=tk.W, pady=2)

        self.enable_logging = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            prefs_frame,
            text="Enable detailed logging",
            variable=self.enable_logging
        ).pack(anchor=tk.W, pady=2)

        # Save button
        ttk.Button(
            tab,
            text="Save Configuration",
            command=self.save_configuration
        ).pack(pady=10)

    def create_logs_tab(self):
        """Create logs viewing tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Logs")

        # Controls
        controls_frame = ttk.Frame(tab)
        controls_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(controls_frame, text="Log Level:").pack(side=tk.LEFT, padx=5)

        self.log_level_var = tk.StringVar(value="INFO")
        log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        ttk.Combobox(
            controls_frame,
            textvariable=self.log_level_var,
            values=log_levels,
            width=15,
            state="readonly"
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            controls_frame,
            text="Refresh Logs",
            command=self.refresh_logs
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            controls_frame,
            text="Clear Display",
            command=self.clear_logs
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            controls_frame,
            text="Export Logs",
            command=self.export_logs
        ).pack(side=tk.LEFT, padx=5)

        # Log display
        log_frame = ttk.Frame(tab)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            wrap=tk.WORD,
            font=("Courier", 9)
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # Configure text tags for different log levels
        self.log_text.tag_config("DEBUG", foreground="gray")
        self.log_text.tag_config("INFO", foreground="black")
        self.log_text.tag_config("WARNING", foreground="orange")
        self.log_text.tag_config("ERROR", foreground="red")
        self.log_text.tag_config("CRITICAL", foreground="red", background="yellow")

    def create_setup_tab(self):
        """Create setup/installation tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Setup")

        # Installation status
        status_frame = ttk.LabelFrame(tab, text="Installation Status", padding=10)
        status_frame.pack(fill=tk.X, padx=10, pady=10)

        self.install_status_text = scrolledtext.ScrolledText(
            status_frame,
            height=8,
            wrap=tk.WORD,
            font=("Courier", 9)
        )
        self.install_status_text.pack(fill=tk.BOTH, expand=True)

        # Installation actions
        actions_frame = ttk.LabelFrame(tab, text="Setup Actions", padding=10)
        actions_frame.pack(fill=tk.X, padx=10, pady=10)

        setup_actions = [
            ("Install Dependencies", self.install_dependencies),
            ("Initialize System", self.initialize_system),
            ("Download Frontend", self.download_frontend),
            ("Install Frontend Dependencies", self.install_frontend_deps),
            ("Run All Setup Steps", self.run_full_setup),
        ]

        for text, command in setup_actions:
            ttk.Button(
                actions_frame,
                text=text,
                command=command,
                width=30
            ).pack(pady=5)

        # Progress bar
        self.setup_progress = ttk.Progressbar(
            tab,
            mode='indeterminate'
        )
        self.setup_progress.pack(fill=tk.X, padx=10, pady=10)

    # ==================== System Control Methods ====================

    def start_system(self):
        """Start the agent team system"""
        if self.system_running:
            messagebox.showwarning("Already Running", "System is already running!")
            return

        autonomy = self.autonomy_var.get()
        self.log_message(f"Starting system with {autonomy} autonomy level...")

        try:
            # Start system in background thread
            def run_system():
                cmd = [
                    sys.executable,
                    "-m",
                    "agent_team",
                    "start",
                    "--autonomy",
                    autonomy
                ]

                self.system_process = subprocess.Popen(
                    cmd,
                    cwd=self.workspace_dir.parent,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )

                # Monitor output
                for line in self.system_process.stdout:
                    self.log_message(line.strip())

            thread = threading.Thread(target=run_system, daemon=True)
            thread.start()

            self.system_running = True
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.status_bar.config(text=f"System Status: Running ({autonomy})")

            # Auto-launch frontend if enabled
            if self.auto_launch_frontend.get():
                self.after(3000, self.launch_frontend)

            messagebox.showinfo("Success", "System started successfully!")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to start system: {e}")
            self.log_message(f"ERROR: {e}")

    def stop_system(self):
        """Stop the agent team system"""
        if not self.system_running:
            return

        self.log_message("Stopping system...")

        try:
            if self.system_process:
                self.system_process.terminate()
                self.system_process.wait(timeout=10)

            self.system_running = False
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.status_bar.config(text="System Status: Stopped")

            messagebox.showinfo("Success", "System stopped successfully!")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to stop system: {e}")

    def restart_system(self):
        """Restart the system"""
        self.stop_system()
        self.after(2000, self.start_system)

    # ==================== Action Methods ====================

    def view_status(self):
        """View system status"""
        try:
            cmd = [sys.executable, "-m", "agent_team", "status"]
            result = subprocess.run(
                cmd,
                cwd=self.workspace_dir.parent,
                capture_output=True,
                text=True
            )
            messagebox.showinfo("System Status", result.stdout or "No status available")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to get status: {e}")

    def create_backup(self):
        """Create a system backup"""
        label = f"GUI_Backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        try:
            cmd = [
                sys.executable,
                "-m",
                "agent_team",
                "backup",
                "create",
                "--label",
                label
            ]
            subprocess.run(cmd, cwd=self.workspace_dir.parent, check=True)
            messagebox.showinfo("Success", f"Backup created: {label}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create backup: {e}")

    def open_workspace(self):
        """Open workspace directory"""
        if self.workspace_dir.exists():
            if sys.platform == "win32":
                os.startfile(self.workspace_dir)
            elif sys.platform == "darwin":
                subprocess.run(["open", str(self.workspace_dir)])
            else:
                subprocess.run(["xdg-open", str(self.workspace_dir)])

    def launch_frontend(self):
        """Launch the frontend application"""
        if not self.frontend_dir.exists():
            response = messagebox.askyesno(
                "Frontend Not Found",
                "Frontend not installed. Download now?"
            )
            if response:
                self.download_frontend()
            return

        try:
            # Check for package.json (npm project)
            package_json = self.frontend_dir / "package.json"
            if package_json.exists():
                subprocess.Popen(
                    ["npm", "start"],
                    cwd=self.frontend_dir,
                    shell=True
                )
                messagebox.showinfo("Success", "Frontend launched!")
            else:
                # Check for index.html (static site)
                index_html = self.frontend_dir / "index.html"
                if index_html.exists():
                    import webbrowser
                    webbrowser.open(f"file://{index_html.absolute()}")
                else:
                    messagebox.showerror("Error", "Frontend entry point not found")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch frontend: {e}")

    def open_documentation(self):
        """Open documentation"""
        docs_dir = self.workspace_dir / "manuals"
        if docs_dir.exists():
            self.open_workspace()
        else:
            messagebox.showwarning("Not Found", "Documentation not found")

    def run_health_check(self):
        """Run system health check"""
        try:
            cmd = [sys.executable, "-m", "agent_team", "health-check"]
            result = subprocess.run(
                cmd,
                cwd=self.workspace_dir.parent,
                capture_output=True,
                text=True
            )
            messagebox.showinfo("Health Check", result.stdout)
        except Exception as e:
            messagebox.showerror("Error", f"Health check failed: {e}")

    # ==================== Helper Methods ====================

    def check_installation(self):
        """Check if system is properly installed"""
        status = []

        # Check workspace
        if self.workspace_dir.exists():
            status.append("✓ Workspace directory found")
        else:
            status.append("✗ Workspace directory not found")

        # Check core files
        core_dir = self.workspace_dir / "core"
        if core_dir.exists():
            status.append("✓ Core system files found")
        else:
            status.append("✗ Core system files not found")

        # Check requirements
        req_file = self.workspace_dir / "requirements.txt"
        if req_file.exists():
            status.append("✓ Requirements file found")
        else:
            status.append("✗ Requirements file not found")

        self.install_status_text.delete(1.0, tk.END)
        self.install_status_text.insert(tk.END, "\n".join(status))

    def update_system_info(self):
        """Update system information display"""
        info = []
        info.append(f"Version: 1.0.0")
        info.append(f"Workspace: {self.workspace_dir}")
        info.append(f"Frontend: {self.frontend_dir}")
        info.append(f"Python: {sys.version.split()[0]}")
        info.append(f"Platform: {sys.platform}")
        info.append("")
        info.append("System Features:")
        info.append("  • 3 Autonomy Levels (Manual, Semi-Auto, Full-Auto)")
        info.append("  • Automatic Recovery & Backups")
        info.append("  • Structured Logging & Monitoring")
        info.append("  • Best Practice Reminders")
        info.append("  • Multi-Domain Support")
        info.append("  • Style Guide Enforcement")
        info.append("  • Component Reuse System")

        self.info_text.delete(1.0, tk.END)
        self.info_text.insert(tk.END, "\n".join(info))

    def log_message(self, message, level="INFO"):
        """Add message to log display"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted = f"[{timestamp}] [{level}] {message}\n"

        self.log_text.insert(tk.END, formatted, level)
        self.log_text.see(tk.END)

    def refresh_logs(self):
        """Refresh log display"""
        self.log_text.delete(1.0, tk.END)
        self.log_message("Logs refreshed")

    def clear_logs(self):
        """Clear log display"""
        self.log_text.delete(1.0, tk.END)

    def export_logs(self):
        """Export logs to file"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".log",
            filetypes=[("Log Files", "*.log"), ("Text Files", "*.txt")]
        )
        if filename:
            try:
                with open(filename, 'w') as f:
                    f.write(self.log_text.get(1.0, tk.END))
                messagebox.showinfo("Success", f"Logs exported to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export logs: {e}")

    def browse_workspace(self):
        """Browse for workspace directory"""
        directory = filedialog.askdirectory()
        if directory:
            self.workspace_entry.delete(0, tk.END)
            self.workspace_entry.insert(0, directory)
            self.workspace_dir = Path(directory)

    def browse_frontend(self):
        """Browse for frontend directory"""
        directory = filedialog.askdirectory()
        if directory:
            self.frontend_entry.delete(0, tk.END)
            self.frontend_entry.insert(0, directory)
            self.frontend_dir = Path(directory)

    def save_configuration(self):
        """Save configuration to file"""
        config = {
            "workspace_dir": str(self.workspace_dir),
            "frontend_dir": str(self.frontend_dir),
            "auto_launch_frontend": self.auto_launch_frontend.get(),
            "auto_backup": self.auto_backup.get(),
            "show_reminders": self.show_reminders.get(),
            "enable_logging": self.enable_logging.get(),
            "autonomy_level": self.autonomy_var.get(),
        }

        config_file = Path.cwd() / "launcher_config.json"
        try:
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
            messagebox.showinfo("Success", "Configuration saved!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save configuration: {e}")

    def refresh_agents(self):
        """Refresh agents list"""
        self.agents_listbox.delete(0, tk.END)

        agents = [
            "code_generator - Code Generation Agent",
            "testing_agent - Automated Testing Agent (Coming Soon)",
            "documentation_agent - Documentation Generator (Coming Soon)",
            "database_agent - Database Schema Manager (Coming Soon)",
        ]

        for agent in agents:
            self.agents_listbox.insert(tk.END, agent)

    def submit_task(self):
        """Submit a task to an agent"""
        messagebox.showinfo("Coming Soon", "Task submission UI coming soon!\nUse CLI for now: python -m agent_team task submit")

    def view_agent_logs(self):
        """View logs for selected agent"""
        messagebox.showinfo("Coming Soon", "Agent-specific logs viewer coming soon!")

    # ==================== Setup Methods ====================

    def install_dependencies(self):
        """Install Python dependencies"""
        self.setup_progress.start()
        self.log_message("Installing dependencies...")

        def install():
            try:
                req_file = self.workspace_dir / "requirements.txt"
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", "-r", str(req_file)],
                    check=True
                )
                self.log_message("Dependencies installed successfully!")
                messagebox.showinfo("Success", "Dependencies installed!")
            except Exception as e:
                self.log_message(f"ERROR: {e}")
                messagebox.showerror("Error", f"Installation failed: {e}")
            finally:
                self.setup_progress.stop()

        threading.Thread(target=install, daemon=True).start()

    def initialize_system(self):
        """Initialize the agent team system"""
        self.log_message("Initializing system...")

        try:
            cmd = [sys.executable, "-m", "agent_team", "init"]
            subprocess.run(cmd, cwd=self.workspace_dir.parent, check=True)
            self.log_message("System initialized successfully!")
            messagebox.showinfo("Success", "System initialized!")
            self.check_installation()
        except Exception as e:
            messagebox.showerror("Error", f"Initialization failed: {e}")

    def download_frontend(self):
        """Download pre-made frontend"""
        messagebox.showinfo(
            "Coming Soon",
            "Frontend download feature coming soon!\n\n"
            "For now, you can:\n"
            "1. Clone a frontend template\n"
            "2. Place it in the 'frontend' directory\n"
            "3. Use the 'Browse' button to select it"
        )

    def install_frontend_deps(self):
        """Install frontend dependencies"""
        if not self.frontend_dir.exists():
            messagebox.showwarning("Not Found", "Frontend directory not found")
            return

        package_json = self.frontend_dir / "package.json"
        if not package_json.exists():
            messagebox.showwarning("Not Found", "package.json not found")
            return

        self.setup_progress.start()
        self.log_message("Installing frontend dependencies...")

        def install():
            try:
                subprocess.run(
                    ["npm", "install"],
                    cwd=self.frontend_dir,
                    check=True,
                    shell=True
                )
                self.log_message("Frontend dependencies installed!")
                messagebox.showinfo("Success", "Frontend dependencies installed!")
            except Exception as e:
                self.log_message(f"ERROR: {e}")
                messagebox.showerror("Error", f"Installation failed: {e}")
            finally:
                self.setup_progress.stop()

        threading.Thread(target=install, daemon=True).start()

    def run_full_setup(self):
        """Run complete setup process"""
        if messagebox.askyesno(
            "Full Setup",
            "This will run all setup steps:\n"
            "1. Install dependencies\n"
            "2. Initialize system\n"
            "3. Install frontend dependencies (if available)\n\n"
            "Continue?"
        ):
            self.install_dependencies()
            self.after(5000, self.initialize_system)
            if self.frontend_dir.exists():
                self.after(10000, self.install_frontend_deps)


def main():
    """Main entry point"""
    app = AgentTeamLauncher()
    app.mainloop()


if __name__ == "__main__":
    main()
