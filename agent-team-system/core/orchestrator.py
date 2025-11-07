"""
Agent Team Orchestrator

Central controller that manages all agents, coordinates tasks,
handles dependencies, and ensures smooth operation of the agent team.
"""

import json
import logging
import threading
import time
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from queue import Queue, PriorityQueue
import uuid

from .agent_base import BaseAgent, AgentState, AgentPriority


class AutonomyLevel(Enum):
    """System autonomy levels"""
    MANUAL = "manual"  # Every action requires approval
    SEMI_AUTO = "semi_auto"  # Pre-approved categories can run
    FULL_AUTO = "full_auto"  # Full autonomy within safety boundaries


class TaskStatus(Enum):
    """Task execution status"""
    QUEUED = "queued"
    WAITING_APPROVAL = "waiting_approval"
    APPROVED = "approved"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentOrchestrator:
    """
    Central orchestrator for managing the agent team.

    Features:
    - Agent lifecycle management
    - Task queuing and scheduling
    - Dependency resolution
    - Autonomy control
    - Health monitoring
    - Automatic recovery
    """

    def __init__(
        self,
        workspace_dir: Optional[Path] = None,
        autonomy_level: AutonomyLevel = AutonomyLevel.SEMI_AUTO,
        config: Optional[Dict[str, Any]] = None
    ):
        self.workspace_dir = workspace_dir or Path.cwd() / "agent-team-system"
        self.autonomy_level = autonomy_level
        self.config = config or {}

        # Agent registry
        self.agents: Dict[str, BaseAgent] = {}
        self.agent_types: Dict[str, type] = {}

        # Task management
        self.task_queue: PriorityQueue = PriorityQueue()
        self.pending_approval: List[Dict[str, Any]] = []
        self.active_tasks: Dict[str, Dict[str, Any]] = {}
        self.completed_tasks: List[Dict[str, Any]] = []
        self.task_graph: Dict[str, Set[str]] = {}  # Task dependencies

        # State
        self.running = False
        self.orchestrator_id = f"orchestrator_{uuid.uuid4().hex[:8]}"

        # Threading
        self.worker_thread: Optional[threading.Thread] = None
        self.monitor_thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()

        # Setup
        self._setup_logging()
        self._setup_directories()
        self._load_state()

        self.logger.info(f"Orchestrator {self.orchestrator_id} initialized", extra={
            "autonomy_level": self.autonomy_level.value,
            "workspace": str(self.workspace_dir)
        })

    def _setup_logging(self):
        """Setup orchestrator logging"""
        logs_dir = self.workspace_dir / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)

        log_file = logs_dir / "orchestrator.jsonl"

        self.logger = logging.getLogger(f"orchestrator.{self.orchestrator_id}")
        self.logger.setLevel(logging.DEBUG)

        # JSON formatter
        class JsonFormatter(logging.Formatter):
            def format(self, record):
                log_data = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "level": record.levelname,
                    "component": "orchestrator",
                    "message": record.getMessage(),
                    "module": record.module,
                    "function": record.funcName,
                }
                for key, value in record.__dict__.items():
                    if key not in ['name', 'msg', 'args', 'created', 'filename', 'funcName',
                                   'levelname', 'levelno', 'lineno', 'module', 'msecs',
                                   'message', 'pathname', 'process', 'processName',
                                   'relativeCreated', 'thread', 'threadName']:
                        log_data[key] = value
                return json.dumps(log_data)

        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(JsonFormatter())
        self.logger.addHandler(file_handler)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
        self.logger.addHandler(console_handler)

    def _setup_directories(self):
        """Create necessary directories"""
        directories = [
            self.workspace_dir / "state",
            self.workspace_dir / "logs",
            self.workspace_dir / "backups",
            self.workspace_dir / "output",
        ]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    def _save_state(self):
        """Save orchestrator state"""
        state_file = self.workspace_dir / "state" / "orchestrator_state.json"

        state_data = {
            "orchestrator_id": self.orchestrator_id,
            "autonomy_level": self.autonomy_level.value,
            "agents": {
                agent_id: {
                    "name": agent.name,
                    "state": agent.state.value,
                    "type": type(agent).__name__
                }
                for agent_id, agent in self.agents.items()
            },
            "active_tasks": self.active_tasks,
            "completed_tasks": self.completed_tasks[-100:],  # Last 100
            "pending_approval": self.pending_approval,
            "timestamp": datetime.utcnow().isoformat(),
        }

        with open(state_file, 'w') as f:
            json.dump(state_data, f, indent=2)

    def _load_state(self):
        """Load orchestrator state"""
        state_file = self.workspace_dir / "state" / "orchestrator_state.json"

        if not state_file.exists():
            return

        try:
            with open(state_file, 'r') as f:
                state_data = json.load(f)

            self.autonomy_level = AutonomyLevel(state_data.get("autonomy_level", "semi_auto"))
            self.completed_tasks = state_data.get("completed_tasks", [])
            self.pending_approval = state_data.get("pending_approval", [])

            self.logger.info("Orchestrator state loaded")
        except Exception as e:
            self.logger.error(f"Failed to load state: {e}")

    def register_agent(self, agent: BaseAgent):
        """
        Register an agent with the orchestrator

        Args:
            agent: Agent instance to register
        """
        with self.lock:
            self.agents[agent.agent_id] = agent
            self.agent_types[agent.name] = type(agent)

            self.logger.info(f"Agent registered: {agent.name}", extra={
                "agent_id": agent.agent_id,
                "agent_type": type(agent).__name__
            })

            self._save_state()

    def unregister_agent(self, agent_id: str):
        """Unregister an agent"""
        with self.lock:
            if agent_id in self.agents:
                agent = self.agents.pop(agent_id)
                self.logger.info(f"Agent unregistered: {agent.name}", extra={
                    "agent_id": agent_id
                })
                self._save_state()

    def submit_task(
        self,
        agent_name: str,
        task: Dict[str, Any],
        priority: AgentPriority = AgentPriority.MEDIUM,
        dependencies: Optional[List[str]] = None,
        requires_approval: bool = False
    ) -> str:
        """
        Submit a task to the orchestrator

        Args:
            agent_name: Name of the agent to execute the task
            task: Task dictionary with parameters
            priority: Task priority level
            dependencies: List of task IDs that must complete first
            requires_approval: Whether task needs approval regardless of autonomy level

        Returns:
            Task ID
        """
        task_id = task.get("id", f"task_{uuid.uuid4().hex[:8]}")
        task["id"] = task_id

        task_wrapper = {
            "task_id": task_id,
            "agent_name": agent_name,
            "task": task,
            "priority": priority,
            "dependencies": dependencies or [],
            "requires_approval": requires_approval or (self.autonomy_level == AutonomyLevel.MANUAL),
            "status": TaskStatus.QUEUED,
            "submitted_at": datetime.utcnow().isoformat(),
            "started_at": None,
            "completed_at": None,
            "result": None,
        }

        # Store dependencies
        if dependencies:
            self.task_graph[task_id] = set(dependencies)

        # Check if approval needed
        if task_wrapper["requires_approval"]:
            self.pending_approval.append(task_wrapper)
            task_wrapper["status"] = TaskStatus.WAITING_APPROVAL
            self.logger.info(f"Task submitted (pending approval): {task_id}", extra={
                "task_id": task_id,
                "agent_name": agent_name,
                "task_name": task.get("name")
            })
        else:
            # Add to queue (priority, task)
            self.task_queue.put((priority.value, task_wrapper))
            self.logger.info(f"Task submitted: {task_id}", extra={
                "task_id": task_id,
                "agent_name": agent_name,
                "priority": priority.value,
                "task_name": task.get("name")
            })

        self._save_state()
        return task_id

    def approve_task(self, task_id: str):
        """Approve a pending task"""
        with self.lock:
            for i, task_wrapper in enumerate(self.pending_approval):
                if task_wrapper["task_id"] == task_id:
                    task_wrapper = self.pending_approval.pop(i)
                    task_wrapper["status"] = TaskStatus.APPROVED
                    self.task_queue.put((task_wrapper["priority"].value, task_wrapper))

                    self.logger.info(f"Task approved: {task_id}")
                    self._save_state()
                    return True

            self.logger.warning(f"Task not found in pending approval: {task_id}")
            return False

    def reject_task(self, task_id: str, reason: str = "User rejected"):
        """Reject a pending task"""
        with self.lock:
            for i, task_wrapper in enumerate(self.pending_approval):
                if task_wrapper["task_id"] == task_id:
                    task_wrapper = self.pending_approval.pop(i)
                    task_wrapper["status"] = TaskStatus.CANCELLED
                    task_wrapper["result"] = {"error": reason}
                    self.completed_tasks.append(task_wrapper)

                    self.logger.info(f"Task rejected: {task_id}", extra={"reason": reason})
                    self._save_state()
                    return True

            return False

    def get_pending_approvals(self) -> List[Dict[str, Any]]:
        """Get list of tasks pending approval"""
        return self.pending_approval.copy()

    def set_autonomy_level(self, level: AutonomyLevel):
        """Change system autonomy level"""
        old_level = self.autonomy_level
        self.autonomy_level = level

        self.logger.info(f"Autonomy level changed: {old_level.value} -> {level.value}")
        self._save_state()

    def start(self):
        """Start the orchestrator"""
        if self.running:
            self.logger.warning("Orchestrator already running")
            return

        self.running = True

        # Start worker thread
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()

        # Start monitor thread
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()

        self.logger.info("Orchestrator started")

    def stop(self):
        """Stop the orchestrator"""
        self.running = False

        if self.worker_thread:
            self.worker_thread.join(timeout=5)

        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)

        self.logger.info("Orchestrator stopped")

    def _worker_loop(self):
        """Main worker loop for processing tasks"""
        while self.running:
            try:
                # Get next task (with timeout to allow checking self.running)
                if not self.task_queue.empty():
                    priority, task_wrapper = self.task_queue.get(timeout=1)

                    # Check dependencies
                    if not self._dependencies_met(task_wrapper["task_id"]):
                        # Re-queue with lower priority
                        self.task_queue.put((priority + 1, task_wrapper))
                        continue

                    # Execute task
                    self._execute_task(task_wrapper)
                else:
                    time.sleep(0.1)

            except Exception as e:
                self.logger.error(f"Worker loop error: {e}")
                time.sleep(1)

    def _monitor_loop(self):
        """Monitor agent health and system status"""
        while self.running:
            try:
                # Perform health checks every 30 seconds
                for agent_id, agent in self.agents.items():
                    health = agent.health_check()
                    if not health["healthy"]:
                        self.logger.warning(f"Agent unhealthy: {agent.name}", extra={
                            "agent_id": agent_id,
                            "health": health
                        })

                # Save state periodically
                self._save_state()

                time.sleep(30)

            except Exception as e:
                self.logger.error(f"Monitor loop error: {e}")
                time.sleep(5)

    def _dependencies_met(self, task_id: str) -> bool:
        """Check if all task dependencies are met"""
        if task_id not in self.task_graph:
            return True

        dependencies = self.task_graph[task_id]
        completed_ids = {t["task_id"] for t in self.completed_tasks if t["status"] == TaskStatus.COMPLETED}

        return dependencies.issubset(completed_ids)

    def _execute_task(self, task_wrapper: Dict[str, Any]):
        """Execute a task"""
        task_id = task_wrapper["task_id"]
        agent_name = task_wrapper["agent_name"]

        # Find agent
        agent = self._find_agent_by_name(agent_name)
        if not agent:
            self.logger.error(f"Agent not found: {agent_name}", extra={"task_id": task_id})
            task_wrapper["status"] = TaskStatus.FAILED
            task_wrapper["result"] = {"error": f"Agent not found: {agent_name}"}
            self.completed_tasks.append(task_wrapper)
            return

        # Update status
        task_wrapper["status"] = TaskStatus.RUNNING
        task_wrapper["started_at"] = datetime.utcnow().isoformat()
        self.active_tasks[task_id] = task_wrapper

        self.logger.info(f"Executing task: {task_id}", extra={
            "task_id": task_id,
            "agent_name": agent_name,
            "agent_id": agent.agent_id
        })

        try:
            # Execute task on agent
            result = agent.execute_task(task_wrapper["task"])

            task_wrapper["result"] = result
            task_wrapper["status"] = TaskStatus.COMPLETED if result["status"] == "success" else TaskStatus.FAILED
            task_wrapper["completed_at"] = datetime.utcnow().isoformat()

            self.logger.info(f"Task completed: {task_id}", extra={
                "task_id": task_id,
                "status": task_wrapper["status"].value
            })

        except Exception as e:
            self.logger.error(f"Task execution failed: {task_id}", extra={
                "task_id": task_id,
                "error": str(e)
            })
            task_wrapper["status"] = TaskStatus.FAILED
            task_wrapper["result"] = {"error": str(e)}

        finally:
            # Move to completed
            self.active_tasks.pop(task_id, None)
            self.completed_tasks.append(task_wrapper)
            self._save_state()

    def _find_agent_by_name(self, agent_name: str) -> Optional[BaseAgent]:
        """Find an agent by name"""
        for agent in self.agents.values():
            if agent.name == agent_name:
                return agent
        return None

    def get_status(self) -> Dict[str, Any]:
        """Get orchestrator status"""
        return {
            "orchestrator_id": self.orchestrator_id,
            "running": self.running,
            "autonomy_level": self.autonomy_level.value,
            "agents": {
                agent_id: agent.get_status()
                for agent_id, agent in self.agents.items()
            },
            "tasks": {
                "queued": self.task_queue.qsize(),
                "pending_approval": len(self.pending_approval),
                "active": len(self.active_tasks),
                "completed": len(self.completed_tasks),
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific task"""
        # Check active tasks
        if task_id in self.active_tasks:
            return self.active_tasks[task_id]

        # Check completed tasks
        for task in self.completed_tasks:
            if task["task_id"] == task_id:
                return task

        # Check pending approval
        for task in self.pending_approval:
            if task["task_id"] == task_id:
                return task

        return None
