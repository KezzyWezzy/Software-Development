"""
Agent Team System - Main Entry Point

Command-line interface for the agent team system.

Usage:
    python -m agent_team [command] [options]

Examples:
    python -m agent_team start
    python -m agent_team status
    python -m agent_team task submit --agent code_generator --name "implement-feature"
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent_team.core.orchestrator import AgentOrchestrator, AutonomyLevel, AgentPriority
from agent_team.core.state_manager import StateManager
from agent_team.systems.reminders.reminder_engine import ReminderEngine
from agent_team.systems.reminders.best_practices import BestPracticesManager


class AgentTeamCLI:
    """Command-line interface for the agent team system"""

    def __init__(self):
        self.workspace_dir = Path.cwd() / "agent-team-system"
        self.orchestrator: Optional[AgentOrchestrator] = None

    def main(self):
        """Main entry point"""
        parser = argparse.ArgumentParser(
            description="Agent Team System - Autonomous Development Platform",
            formatter_class=argparse.RawDescriptionHelpFormatter
        )

        subparsers = parser.add_subparsers(dest='command', help='Available commands')

        # Init command
        init_parser = subparsers.add_parser('init', help='Initialize the agent team system')
        init_parser.add_argument('--workspace', type=Path, help='Workspace directory')

        # Start command
        start_parser = subparsers.add_parser('start', help='Start the agent team system')
        start_parser.add_argument('--autonomy', choices=['manual', 'semi_auto', 'full_auto'],
                                   default='semi_auto', help='Autonomy level')

        # Status command
        status_parser = subparsers.add_parser('status', help='Show system status')
        status_parser.add_argument('--agent', help='Show status for specific agent')

        # Stop command
        subparsers.add_parser('stop', help='Stop the agent team system')

        # Config command
        config_parser = subparsers.add_parser('config', help='Configure the system')
        config_parser.add_argument('--autonomy', choices=['manual', 'semi_auto', 'full_auto'],
                                    help='Set autonomy level')
        config_parser.add_argument('--show', help='Show configuration value')

        # Task commands
        task_parser = subparsers.add_parser('task', help='Task management')
        task_subparsers = task_parser.add_subparsers(dest='task_command')

        # Task submit
        task_submit = task_subparsers.add_parser('submit', help='Submit a new task')
        task_submit.add_argument('--agent', required=True, help='Agent name')
        task_submit.add_argument('--name', required=True, help='Task name')
        task_submit.add_argument('--params', help='Task parameters (JSON)')
        task_submit.add_argument('--priority', choices=['low', 'medium', 'high', 'critical'],
                                  default='medium')

        # Task status
        task_status = task_subparsers.add_parser('status', help='Get task status')
        task_status.add_argument('task_id', help='Task ID')

        # Backup commands
        backup_parser = subparsers.add_parser('backup', help='Backup management')
        backup_subparsers = backup_parser.add_subparsers(dest='backup_command')

        backup_create = backup_subparsers.add_parser('create', help='Create backup')
        backup_create.add_argument('--label', help='Backup label')
        backup_create.add_argument('--increment', choices=['major', 'minor', 'patch'],
                                    default='patch')

        backup_list = backup_subparsers.add_parser('list', help='List backups')

        # Health check
        subparsers.add_parser('health-check', help='Perform health check')

        # Version
        version_parser = subparsers.add_parser('version', help='Version management')
        version_parser.add_argument('--show', action='store_true', help='Show current version')

        # Dashboard
        dashboard_parser = subparsers.add_parser('dashboard', help='Start web dashboard')
        dashboard_parser.add_argument('--port', type=int, default=8080, help='Port number')

        args = parser.parse_args()

        if not args.command:
            parser.print_help()
            return 0

        # Execute command
        try:
            if args.command == 'init':
                return self.cmd_init(args)
            elif args.command == 'start':
                return self.cmd_start(args)
            elif args.command == 'stop':
                return self.cmd_stop(args)
            elif args.command == 'status':
                return self.cmd_status(args)
            elif args.command == 'config':
                return self.cmd_config(args)
            elif args.command == 'task':
                return self.cmd_task(args)
            elif args.command == 'backup':
                return self.cmd_backup(args)
            elif args.command == 'health-check':
                return self.cmd_health_check(args)
            elif args.command == 'version':
                return self.cmd_version(args)
            elif args.command == 'dashboard':
                return self.cmd_dashboard(args)
            else:
                print(f"Unknown command: {args.command}")
                return 1

        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            return 1

    def cmd_init(self, args):
        """Initialize the system"""
        if args.workspace:
            self.workspace_dir = args.workspace

        print(f"Initializing agent team system in {self.workspace_dir}")

        # Create directory structure
        directories = [
            "state",
            "backups",
            "logs",
            "logs/agents",
            "output",
            "config",
            "reminders",
            "best_practices",
        ]

        for directory in directories:
            (self.workspace_dir / directory).mkdir(parents=True, exist_ok=True)

        # Create default config
        config_file = self.workspace_dir / "config" / "agent_config.yaml"
        if not config_file.exists():
            default_config = {
                "autonomy_level": "semi_auto",
                "backup_retention": 100,
                "log_level": "INFO",
                "enable_reminders": True,
            }
            import yaml
            with open(config_file, 'w') as f:
                yaml.dump(default_config, f)

        print("✓ Directory structure created")
        print("✓ Default configuration created")
        print("\nInitialization complete!")
        print(f"\nWorkspace: {self.workspace_dir}")
        print("\nNext steps:")
        print("  1. Start the system: python -m agent_team start")
        print("  2. View status: python -m agent_team status")
        print("  3. Read the manual: manuals/OPERATIONS_MANUAL.md")

        return 0

    def cmd_start(self, args):
        """Start the system"""
        print("Starting agent team system...")

        # Initialize orchestrator
        autonomy_level = AutonomyLevel[args.autonomy.upper()]
        self.orchestrator = AgentOrchestrator(
            workspace_dir=self.workspace_dir,
            autonomy_level=autonomy_level
        )

        # TODO: Register agents here
        # Example:
        # code_gen_agent = CodeGeneratorAgent(...)
        # self.orchestrator.register_agent(code_gen_agent)

        # Start orchestrator
        self.orchestrator.start()

        # Start reminder system
        reminder_engine = ReminderEngine(self.workspace_dir)
        best_practices = BestPracticesManager(self.workspace_dir, reminder_engine)
        best_practices.setup_reminders()
        reminder_engine.start()

        print(f"✓ System started with {args.autonomy} autonomy level")
        print(f"✓ Workspace: {self.workspace_dir}")
        print("\nSystem is now running!")
        print("  - View status: python -m agent_team status")
        print("  - Submit task: python -m agent_team task submit --agent <agent> --name <task>")
        print("  - Stop system: python -m agent_team stop")

        # Keep running
        try:
            print("\nPress Ctrl+C to stop...")
            import time
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\nStopping system...")
            self.orchestrator.stop()
            reminder_engine.stop()
            print("System stopped.")

        return 0

    def cmd_stop(self, args):
        """Stop the system"""
        print("Stopping agent team system...")
        # TODO: Implement graceful shutdown
        print("System stopped.")
        return 0

    def cmd_status(self, args):
        """Show system status"""
        if not self.orchestrator:
            # Load status from state files
            state_file = self.workspace_dir / "state" / "orchestrator_state.json"
            if state_file.exists():
                with open(state_file, 'r') as f:
                    state = json.load(f)
                print(json.dumps(state, indent=2))
            else:
                print("System is not running. Start it with: python -m agent_team start")
        else:
            status = self.orchestrator.get_status()
            print(json.dumps(status, indent=2))

        return 0

    def cmd_config(self, args):
        """Configure the system"""
        if args.show:
            # Show config value
            print(f"{args.show}: <value>")
        elif args.autonomy:
            print(f"Setting autonomy level to: {args.autonomy}")
            # TODO: Update config
        else:
            print("No configuration option specified")

        return 0

    def cmd_task(self, args):
        """Task management"""
        if args.task_command == 'submit':
            params = json.loads(args.params) if args.params else {}
            priority = AgentPriority[args.priority.upper()]

            task = {
                "name": args.name,
                "params": params
            }

            if self.orchestrator:
                task_id = self.orchestrator.submit_task(
                    agent_name=args.agent,
                    task=task,
                    priority=priority
                )
                print(f"Task submitted: {task_id}")
            else:
                print("Error: System is not running")
                return 1

        elif args.task_command == 'status':
            if self.orchestrator:
                status = self.orchestrator.get_task_status(args.task_id)
                if status:
                    print(json.dumps(status, indent=2))
                else:
                    print(f"Task not found: {args.task_id}")
            else:
                print("Error: System is not running")
                return 1

        return 0

    def cmd_backup(self, args):
        """Backup management"""
        state_manager = StateManager(self.workspace_dir)

        if args.backup_command == 'create':
            version = state_manager.create_snapshot(
                label=args.label,
                increment=args.increment
            )
            print(f"Backup created: v{version}")

        elif args.backup_command == 'list':
            versions = state_manager.get_version_history()
            print("\nAvailable backups:")
            for version in versions:
                print(f"  v{version['version']} - {version['timestamp']}")
                if version.get('label'):
                    print(f"    Label: {version['label']}")

        return 0

    def cmd_health_check(self, args):
        """Perform health check"""
        print("Performing health check...")

        checks = {
            "Workspace": self.workspace_dir.exists(),
            "State directory": (self.workspace_dir / "state").exists(),
            "Logs directory": (self.workspace_dir / "logs").exists(),
            "Config directory": (self.workspace_dir / "config").exists(),
        }

        all_passed = True
        for check, passed in checks.items():
            status = "✓" if passed else "✗"
            print(f"  {status} {check}")
            if not passed:
                all_passed = False

        if all_passed:
            print("\n✓ All health checks passed")
            return 0
        else:
            print("\n✗ Some health checks failed")
            return 1

    def cmd_version(self, args):
        """Version management"""
        print("Agent Team System v1.0.0")
        return 0

    def cmd_dashboard(self, args):
        """Start web dashboard"""
        print(f"Starting dashboard on port {args.port}...")
        print(f"Dashboard will be available at: http://localhost:{args.port}")
        print("\nDashboard feature coming soon!")
        return 0


def main():
    """Main entry point"""
    cli = AgentTeamCLI()
    sys.exit(cli.main())


if __name__ == '__main__':
    main()
