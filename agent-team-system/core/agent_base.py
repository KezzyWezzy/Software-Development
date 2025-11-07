"""
Base Agent Class with Recovery, Logging, and State Management

All agents inherit from this base class to get:
- Structured logging
- State persistence
- Error recovery
- Progress tracking
- Health monitoring
"""

import json
import logging
import traceback
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
import uuid


class AgentState(Enum):
    """Agent execution states"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    RECOVERING = "recovering"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentPriority(Enum):
    """Task priority levels"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class BaseAgent(ABC):
    """
    Base class for all agents in the system.

    Provides:
    - Lifecycle management (start, pause, resume, stop)
    - State persistence and recovery
    - Structured logging
    - Error handling and recovery
    - Progress tracking
    - Health checks
    """

    def __init__(
        self,
        name: str,
        agent_id: Optional[str] = None,
        workspace_dir: Optional[Path] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        self.name = name
        self.agent_id = agent_id or f"{name}_{uuid.uuid4().hex[:8]}"
        self.workspace_dir = workspace_dir or Path.cwd() / "agent-team-system"
        self.config = config or {}

        # State management
        self.state = AgentState.IDLE
        self.current_task: Optional[Dict[str, Any]] = None
        self.progress = 0.0  # 0.0 to 100.0
        self.metadata: Dict[str, Any] = {}

        # History and recovery
        self.task_history: List[Dict[str, Any]] = []
        self.error_history: List[Dict[str, Any]] = []
        self.state_snapshots: List[Dict[str, Any]] = []

        # Setup logging
        self._setup_logging()

        # Setup directories
        self._setup_directories()

        # Load previous state if exists
        self._load_state()

        self.logger.info(f"Agent {self.agent_id} initialized", extra={
            "agent_name": self.name,
            "agent_id": self.agent_id,
            "workspace": str(self.workspace_dir)
        })

    def _setup_logging(self):
        """Setup structured logging for this agent"""
        logs_dir = self.workspace_dir / "logs" / "agents"
        logs_dir.mkdir(parents=True, exist_ok=True)

        log_file = logs_dir / f"{self.name}_{self.agent_id}.jsonl"

        # Create logger
        self.logger = logging.getLogger(f"agent.{self.name}.{self.agent_id}")
        self.logger.setLevel(logging.DEBUG)

        # JSON formatter for structured logs
        class JsonFormatter(logging.Formatter):
            def format(self, record):
                log_data = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "level": record.levelname,
                    "agent_id": getattr(record, 'agent_id', None),
                    "agent_name": getattr(record, 'agent_name', None),
                    "message": record.getMessage(),
                    "module": record.module,
                    "function": record.funcName,
                    "line": record.lineno,
                }

                # Add extra fields
                if hasattr(record, 'task_id'):
                    log_data['task_id'] = record.task_id
                if hasattr(record, 'error'):
                    log_data['error'] = record.error
                if hasattr(record, 'traceback'):
                    log_data['traceback'] = record.traceback

                return json.dumps(log_data)

        # File handler with JSON format
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(JsonFormatter())
        self.logger.addHandler(file_handler)

        # Console handler with simple format
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
        self.logger.addHandler(console_handler)

    def _setup_directories(self):
        """Create necessary directories for agent operation"""
        directories = [
            self.workspace_dir / "state" / self.agent_id,
            self.workspace_dir / "backups" / self.agent_id,
            self.workspace_dir / "logs" / "agents",
            self.workspace_dir / "output" / self.agent_id,
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    def _save_state(self):
        """Persist current agent state to disk"""
        state_file = self.workspace_dir / "state" / self.agent_id / "current_state.json"

        state_data = {
            "agent_id": self.agent_id,
            "agent_name": self.name,
            "state": self.state.value,
            "progress": self.progress,
            "current_task": self.current_task,
            "metadata": self.metadata,
            "task_history": self.task_history[-100:],  # Keep last 100
            "error_history": self.error_history[-50:],  # Keep last 50
            "timestamp": datetime.utcnow().isoformat(),
        }

        with open(state_file, 'w') as f:
            json.dump(state_data, f, indent=2)

        # Also create a timestamped snapshot
        snapshot_file = self.workspace_dir / "backups" / self.agent_id / f"snapshot_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        with open(snapshot_file, 'w') as f:
            json.dump(state_data, f, indent=2)

        self.logger.debug("State saved", extra={"state_file": str(state_file)})

    def _load_state(self):
        """Load previous agent state from disk"""
        state_file = self.workspace_dir / "state" / self.agent_id / "current_state.json"

        if not state_file.exists():
            self.logger.debug("No previous state found, starting fresh")
            return

        try:
            with open(state_file, 'r') as f:
                state_data = json.load(f)

            self.state = AgentState(state_data.get("state", "idle"))
            self.progress = state_data.get("progress", 0.0)
            self.current_task = state_data.get("current_task")
            self.metadata = state_data.get("metadata", {})
            self.task_history = state_data.get("task_history", [])
            self.error_history = state_data.get("error_history", [])

            self.logger.info("Previous state loaded", extra={
                "state": self.state.value,
                "tasks_completed": len(self.task_history)
            })
        except Exception as e:
            self.logger.error(f"Failed to load state: {e}", extra={
                "error": str(e),
                "traceback": traceback.format_exc()
            })

    def execute_task(
        self,
        task: Dict[str, Any],
        auto_recover: bool = True
    ) -> Dict[str, Any]:
        """
        Execute a task with automatic error handling and recovery

        Args:
            task: Task dictionary with at minimum: {"name": "task_name", "params": {...}}
            auto_recover: Whether to automatically attempt recovery on errors

        Returns:
            Result dictionary with status, output, and metadata
        """
        task_id = task.get("id", f"task_{uuid.uuid4().hex[:8]}")
        task["id"] = task_id

        self.logger.info(f"Starting task: {task.get('name')}", extra={
            "task_id": task_id,
            "task_name": task.get('name')
        })

        # Update state
        self.state = AgentState.RUNNING
        self.current_task = task
        self.progress = 0.0
        self._save_state()

        result = {
            "task_id": task_id,
            "task_name": task.get("name"),
            "status": "unknown",
            "output": None,
            "error": None,
            "started_at": datetime.utcnow().isoformat(),
            "completed_at": None,
        }

        try:
            # Execute the actual task (implemented by subclass)
            output = self._execute_task_impl(task)

            result["status"] = "success"
            result["output"] = output
            result["completed_at"] = datetime.utcnow().isoformat()

            self.state = AgentState.COMPLETED
            self.progress = 100.0

            # Add to history
            self.task_history.append(result)

            self.logger.info(f"Task completed successfully: {task.get('name')}", extra={
                "task_id": task_id,
                "duration": self._calculate_duration(result["started_at"], result["completed_at"])
            })

        except Exception as e:
            self.logger.error(f"Task failed: {task.get('name')}", extra={
                "task_id": task_id,
                "error": str(e),
                "traceback": traceback.format_exc()
            })

            result["status"] = "error"
            result["error"] = str(e)
            result["traceback"] = traceback.format_exc()
            result["completed_at"] = datetime.utcnow().isoformat()

            self.state = AgentState.ERROR
            self.error_history.append(result)

            # Attempt recovery if enabled
            if auto_recover:
                self.logger.info("Attempting automatic recovery")
                recovery_result = self._attempt_recovery(task, e)
                if recovery_result.get("recovered"):
                    result = recovery_result["result"]
                    self.state = AgentState.COMPLETED

        finally:
            self.current_task = None
            self._save_state()

        return result

    @abstractmethod
    def _execute_task_impl(self, task: Dict[str, Any]) -> Any:
        """
        Actual task execution - must be implemented by subclasses

        Args:
            task: Task dictionary with parameters

        Returns:
            Task output/result
        """
        pass

    def _attempt_recovery(self, task: Dict[str, Any], error: Exception) -> Dict[str, Any]:
        """
        Attempt to recover from an error

        Default implementation just logs the error.
        Subclasses can override for specific recovery strategies.
        """
        self.state = AgentState.RECOVERING
        self._save_state()

        self.logger.warning(f"No recovery strategy defined for {self.name}")

        return {
            "recovered": False,
            "error": str(error),
            "message": "No recovery strategy available"
        }

    def update_progress(self, progress: float, message: Optional[str] = None):
        """Update task progress (0-100)"""
        self.progress = max(0.0, min(100.0, progress))

        if message:
            self.logger.info(f"Progress: {self.progress:.1f}% - {message}", extra={
                "progress": self.progress,
                "task_id": self.current_task.get("id") if self.current_task else None
            })

        self._save_state()

    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on this agent

        Returns:
            Health status dictionary
        """
        return {
            "agent_id": self.agent_id,
            "agent_name": self.name,
            "state": self.state.value,
            "healthy": self.state not in [AgentState.ERROR, AgentState.FAILED],
            "current_task": self.current_task.get("name") if self.current_task else None,
            "progress": self.progress,
            "tasks_completed": len(self.task_history),
            "errors_encountered": len(self.error_history),
            "last_error": self.error_history[-1] if self.error_history else None,
            "uptime": self._calculate_uptime(),
        }

    def get_status(self) -> Dict[str, Any]:
        """Get detailed agent status"""
        return {
            "agent_id": self.agent_id,
            "agent_name": self.name,
            "state": self.state.value,
            "progress": self.progress,
            "current_task": self.current_task,
            "metadata": self.metadata,
            "statistics": {
                "tasks_completed": len(self.task_history),
                "tasks_failed": len(self.error_history),
                "success_rate": self._calculate_success_rate(),
            }
        }

    def pause(self):
        """Pause agent execution"""
        if self.state == AgentState.RUNNING:
            self.state = AgentState.PAUSED
            self._save_state()
            self.logger.info("Agent paused")

    def resume(self):
        """Resume agent execution"""
        if self.state == AgentState.PAUSED:
            self.state = AgentState.RUNNING
            self._save_state()
            self.logger.info("Agent resumed")

    def stop(self):
        """Stop agent execution"""
        self.state = AgentState.IDLE
        self.current_task = None
        self.progress = 0.0
        self._save_state()
        self.logger.info("Agent stopped")

    def _calculate_duration(self, start: str, end: str) -> float:
        """Calculate duration in seconds between two ISO timestamps"""
        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end)
        return (end_dt - start_dt).total_seconds()

    def _calculate_success_rate(self) -> float:
        """Calculate task success rate"""
        total = len(self.task_history) + len(self.error_history)
        if total == 0:
            return 100.0
        return (len(self.task_history) / total) * 100.0

    def _calculate_uptime(self) -> str:
        """Calculate agent uptime - placeholder for now"""
        return "N/A"

    def rollback_to_snapshot(self, snapshot_id: str) -> bool:
        """
        Rollback agent state to a previous snapshot

        Args:
            snapshot_id: Snapshot identifier or timestamp

        Returns:
            True if rollback successful
        """
        backup_dir = self.workspace_dir / "backups" / self.agent_id
        snapshots = list(backup_dir.glob("snapshot_*.json"))

        # Find matching snapshot
        target_snapshot = None
        for snapshot in snapshots:
            if snapshot_id in snapshot.name:
                target_snapshot = snapshot
                break

        if not target_snapshot:
            self.logger.error(f"Snapshot not found: {snapshot_id}")
            return False

        try:
            with open(target_snapshot, 'r') as f:
                state_data = json.load(f)

            # Restore state
            self.state = AgentState(state_data.get("state", "idle"))
            self.progress = state_data.get("progress", 0.0)
            self.current_task = state_data.get("current_task")
            self.metadata = state_data.get("metadata", {})

            self._save_state()

            self.logger.info(f"Rolled back to snapshot: {snapshot_id}")
            return True

        except Exception as e:
            self.logger.error(f"Rollback failed: {e}")
            return False
