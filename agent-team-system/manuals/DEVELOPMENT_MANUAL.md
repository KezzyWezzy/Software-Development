# Agent Team System - Development Manual

Version: 1.0.0
Last Updated: 2025-11-07

## Table of Contents

1. [Introduction](#introduction)
2. [Architecture Deep Dive](#architecture-deep-dive)
3. [Creating Custom Agents](#creating-custom-agents)
4. [Extending the System](#extending-the-system)
5. [API Reference](#api-reference)
6. [Testing](#testing)
7. [Contributing](#contributing)
8. [Advanced Topics](#advanced-topics)

---

## Introduction

This manual is for developers who want to:
- Create custom agents
- Extend system functionality
- Integrate with external systems
- Contribute to the project

### Prerequisites

- Python 3.9+ knowledge
- Understanding of async programming
- Familiarity with design patterns
- Git workflow experience

### Development Setup

```bash
# Clone repository
git clone <repository-url>
cd agent-team-system

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install development dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Run tests
pytest tests/
```

---

## Architecture Deep Dive

### Core Design Principles

1. **Modularity**: Each component is independent and replaceable
2. **Extensibility**: Easy to add new agents and features
3. **Resilience**: Automatic recovery from failures
4. **Observability**: Comprehensive logging and monitoring
5. **Safety**: Multiple levels of approval and safeguards

### Component Overview

```
agent-team-system/
├── core/
│   ├── agent_base.py          # Base agent class
│   ├── orchestrator.py        # Central coordinator
│   ├── state_manager.py       # State persistence
│   └── autonomy_controller.py # Autonomy management
├── agents/
│   ├── code_generator/        # Code generation agent
│   ├── testing_agent/         # Testing agent
│   ├── documentation_agent/   # Documentation agent
│   └── ...
├── systems/
│   ├── logging/               # Logging infrastructure
│   ├── backup/                # Backup system
│   ├── monitoring/            # Monitoring system
│   └── reminders/             # Reminder system
└── api/
    └── rest_api.py           # REST API interface
```

### Class Hierarchy

```
BaseAgent (Abstract)
  ├── CodeGeneratorAgent
  ├── TestingAgent
  ├── DocumentationAgent
  ├── DatabaseAgent
  ├── ValidationAgent
  └── RecoveryAgent

AgentOrchestrator
  ├── TaskQueue
  ├── AgentRegistry
  └── DependencyGraph

StateManager
  ├── VersionControl
  └── SnapshotManager
```

---

## Creating Custom Agents

### Basic Agent Structure

All agents inherit from `BaseAgent`:

```python
from pathlib import Path
from typing import Any, Dict
from agent_team.core.agent_base import BaseAgent

class MyCustomAgent(BaseAgent):
    """
    Custom agent that does something specific.

    This agent demonstrates the basic structure
    of a custom agent implementation.
    """

    def __init__(self, name: str = "my_custom_agent", **kwargs):
        super().__init__(name=name, **kwargs)

        # Initialize agent-specific attributes
        self.custom_config = kwargs.get("config", {})

        # Setup agent-specific resources
        self._setup_resources()

    def _setup_resources(self):
        """Setup any resources needed by this agent"""
        # Create directories, load models, etc.
        self.output_dir = self.workspace_dir / "output" / self.name
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _execute_task_impl(self, task: Dict[str, Any]) -> Any:
        """
        Main task execution logic.

        This method is called by execute_task() and must be implemented.

        Args:
            task: Task dictionary with:
                - name: Task name
                - params: Task parameters
                - Any other custom fields

        Returns:
            Task result (any serializable type)

        Raises:
            Exception: Any exception will be caught and logged
        """
        task_name = task.get("name")
        params = task.get("params", {})

        self.logger.info(f"Executing task: {task_name}")

        # Update progress
        self.update_progress(10, "Starting task")

        try:
            # Perform the actual work
            result = self._do_work(params)

            self.update_progress(90, "Finalizing")

            # Return result
            return {
                "success": True,
                "result": result,
                "metadata": {
                    "task_name": task_name,
                }
            }

        except Exception as e:
            self.logger.error(f"Task failed: {e}")
            raise

    def _do_work(self, params: Dict[str, Any]) -> Any:
        """Agent-specific work implementation"""
        # Your custom logic here
        self.update_progress(50, "Processing")

        # Example: Process input
        input_data = params.get("input")
        output_data = self.process(input_data)

        return output_data

    def process(self, data: Any) -> Any:
        """Custom processing logic"""
        # Implement your agent's core functionality
        return data

    def _attempt_recovery(self, task: Dict[str, Any], error: Exception) -> Dict[str, Any]:
        """
        Custom recovery logic for this agent.

        Override this to implement agent-specific recovery strategies.
        """
        self.logger.info(f"Attempting recovery from: {error}")

        # Try to recover (example: retry with different parameters)
        try:
            # Modify task parameters
            task["params"]["retry"] = True

            # Retry execution
            result = self._execute_task_impl(task)

            return {
                "recovered": True,
                "result": result,
                "recovery_method": "retry_with_modified_params"
            }
        except Exception as e:
            return {
                "recovered": False,
                "error": str(e),
                "original_error": str(error)
            }
```

### Registering Your Agent

```python
from agent_team.core.orchestrator import AgentOrchestrator
from my_agents import MyCustomAgent

# Create orchestrator
orchestrator = AgentOrchestrator()

# Create and register your agent
my_agent = MyCustomAgent(
    name="my_custom_agent",
    workspace_dir=Path("/path/to/workspace"),
    config={"setting": "value"}
)

orchestrator.register_agent(my_agent)

# Submit a task to your agent
task_id = orchestrator.submit_task(
    agent_name="my_custom_agent",
    task={
        "name": "process_data",
        "params": {
            "input": "some data"
        }
    }
)
```

### Advanced Agent Features

#### 1. Stateful Agents

```python
class StatefulAgent(BaseAgent):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.state_data = {}

    def _execute_task_impl(self, task: Dict[str, Any]) -> Any:
        # Access state
        previous_result = self.state_data.get("last_result")

        # Update state
        self.state_data["last_result"] = new_result
        self.metadata["state_data"] = self.state_data

        # State is automatically persisted
        self._save_state()

        return new_result
```

#### 2. Multi-Step Tasks

```python
class MultiStepAgent(BaseAgent):
    def _execute_task_impl(self, task: Dict[str, Any]) -> Any:
        steps = task.get("steps", [])
        results = []

        for i, step in enumerate(steps):
            # Update progress for each step
            progress = (i / len(steps)) * 100
            self.update_progress(progress, f"Executing step {i+1}/{len(steps)}")

            # Execute step
            result = self._execute_step(step)
            results.append(result)

        return {"steps_completed": len(steps), "results": results}
```

#### 3. Agents with Dependencies

```python
class DependentAgent(BaseAgent):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.dependency_agent = kwargs.get("dependency")

    def _execute_task_impl(self, task: Dict[str, Any]) -> Any:
        # Wait for dependency
        if self.dependency_agent:
            dep_result = self.dependency_agent.get_status()
            if dep_result["state"] != "completed":
                raise Exception("Dependency not ready")

        # Continue with task
        return self._process(task)
```

---

## Extending the System

### Adding New Task Types

```python
from enum import Enum

class CustomTaskType(Enum):
    DATA_PROCESSING = "data_processing"
    MODEL_TRAINING = "model_training"
    REPORT_GENERATION = "report_generation"

# Register with orchestrator
orchestrator.register_task_type(CustomTaskType)
```

### Custom Logging

```python
from agent_team.systems.logging import StructuredLogger

class CustomLogger(StructuredLogger):
    def log_custom_event(self, event_name: str, data: Dict[str, Any]):
        """Log custom events specific to your domain"""
        self.log_event(
            event_type=f"custom.{event_name}",
            event_data=data,
            level=LogLevel.INFO
        )

# Use in your agent
logger = CustomLogger("my_agent", log_dir)
logger.log_custom_event("data_processed", {"records": 1000})
```

### Custom Backup Strategies

```python
from agent_team.core.state_manager import StateManager

class CustomStateManager(StateManager):
    def create_snapshot(self, **kwargs):
        # Add custom backup logic
        self._backup_custom_resources()

        # Call parent implementation
        return super().create_snapshot(**kwargs)

    def _backup_custom_resources(self):
        """Backup additional resources"""
        # Backup databases, files, etc.
        pass
```

### Custom Reminders

```python
from agent_team.systems.reminders import ReminderEngine, ReminderType

# Create custom reminder type
class CustomReminderType(Enum):
    DATA_REFRESH = "data_refresh"
    MODEL_RETRAIN = "model_retrain"

# Register callback
def on_data_refresh_reminder(reminder):
    print(f"Time to refresh data: {reminder.message}")
    # Trigger data refresh

engine = ReminderEngine(workspace_dir)
engine.register_callback(CustomReminderType.DATA_REFRESH, on_data_refresh_reminder)
```

---

## API Reference

### BaseAgent API

#### Methods

**`execute_task(task: Dict[str, Any], auto_recover: bool = True) -> Dict[str, Any]`**
- Execute a task with automatic error handling
- Returns: Result dictionary with status and output

**`update_progress(progress: float, message: Optional[str] = None)`**
- Update task progress (0-100)
- Automatically saves state

**`health_check() -> Dict[str, Any]`**
- Perform health check
- Returns: Health status dictionary

**`get_status() -> Dict[str, Any]`**
- Get detailed agent status
- Returns: Status dictionary with state and statistics

**`pause()` / `resume()` / `stop()`**
- Control agent execution state

**`rollback_to_snapshot(snapshot_id: str) -> bool`**
- Rollback to a previous state snapshot

#### Properties

- `name`: Agent name
- `agent_id`: Unique agent identifier
- `state`: Current agent state (AgentState enum)
- `progress`: Current progress (0-100)
- `logger`: Agent's structured logger

### AgentOrchestrator API

#### Methods

**`register_agent(agent: BaseAgent)`**
- Register an agent with the orchestrator

**`submit_task(agent_name: str, task: Dict[str, Any], priority: AgentPriority, ...) -> str`**
- Submit a task for execution
- Returns: Task ID

**`approve_task(task_id: str) -> bool`**
- Approve a pending task

**`get_task_status(task_id: str) -> Optional[Dict[str, Any]]`**
- Get status of a specific task

**`set_autonomy_level(level: AutonomyLevel)`**
- Change system autonomy level

**`start()` / `stop()`**
- Start/stop the orchestrator

**`get_status() -> Dict[str, Any]`**
- Get comprehensive system status

### StructuredLogger API

#### Methods

**`debug(message: str, **kwargs)` / `info(...)` / `warning(...)` / `error(...)` / `critical(...)`**
- Log messages at different levels

**`log_event(event_type: str, event_data: Dict, level: LogLevel)`**
- Log structured events

**`log_metric(metric_name: str, value: float, unit: Optional[str], **tags)`**
- Log metrics

**`push_context(**kwargs)` / `pop_context()`**
- Manage logging context stack

**`search_logs(query: str, level: Optional[LogLevel], ...) -> List[Dict]`**
- Search log entries

### StateManager API

#### Methods

**`create_snapshot(label: Optional[str], increment: str, metadata: Dict) -> str`**
- Create state snapshot
- Returns: New version number

**`restore_snapshot(version: str) -> bool`**
- Restore to a specific version

**`get_version_history() -> List[Dict]`**
- Get version history

**`get_version_diff(version1: str, version2: str) -> Dict`**
- Compare two versions

---

## Testing

### Unit Testing Agents

```python
import pytest
from pathlib import Path
from my_agents import MyCustomAgent

@pytest.fixture
def agent():
    """Create agent for testing"""
    return MyCustomAgent(
        name="test_agent",
        workspace_dir=Path("/tmp/test_workspace")
    )

def test_agent_execution(agent):
    """Test basic task execution"""
    task = {
        "name": "test_task",
        "params": {"input": "test_data"}
    }

    result = agent.execute_task(task)

    assert result["status"] == "success"
    assert result["output"] is not None

def test_agent_recovery(agent):
    """Test recovery mechanism"""
    # Create task that will fail
    task = {
        "name": "failing_task",
        "params": {"cause_error": True}
    }

    result = agent.execute_task(task, auto_recover=True)

    # Check if recovery was attempted
    assert "error" in result or result["status"] == "success"

def test_agent_state_persistence(agent, tmp_path):
    """Test state persistence"""
    agent.workspace_dir = tmp_path

    # Execute task
    task = {"name": "test", "params": {}}
    agent.execute_task(task)

    # Check state was saved
    state_file = tmp_path / "state" / agent.agent_id / "current_state.json"
    assert state_file.exists()
```

### Integration Testing

```python
from agent_team.core.orchestrator import AgentOrchestrator

def test_full_workflow(tmp_path):
    """Test complete workflow"""
    orchestrator = AgentOrchestrator(workspace_dir=tmp_path)

    # Register agents
    agent1 = MyCustomAgent(name="agent1")
    agent2 = MyCustomAgent(name="agent2")
    orchestrator.register_agent(agent1)
    orchestrator.register_agent(agent2)

    # Start orchestrator
    orchestrator.start()

    # Submit tasks
    task1_id = orchestrator.submit_task("agent1", {"name": "task1"})
    task2_id = orchestrator.submit_task("agent2", {"name": "task2"}, dependencies=[task1_id])

    # Wait for completion
    import time
    time.sleep(5)

    # Check results
    task1_status = orchestrator.get_task_status(task1_id)
    task2_status = orchestrator.get_task_status(task2_id)

    assert task1_status["status"] == "completed"
    assert task2_status["status"] == "completed"

    # Cleanup
    orchestrator.stop()
```

### Running Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest --cov=agent_team tests/

# Run specific test file
pytest tests/test_agents.py

# Run with verbose output
pytest -v tests/

# Run tests matching pattern
pytest -k "test_agent" tests/
```

---

## Contributing

### Code Style

We follow PEP 8 with some modifications:

```python
# Good
class MyAgent(BaseAgent):
    """Agent that does X, Y, and Z."""

    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name=name)
        self.config = config

    def process_data(self, data: List[str]) -> List[str]:
        """
        Process input data.

        Args:
            data: List of strings to process

        Returns:
            Processed list of strings
        """
        return [item.upper() for item in data]

# Bad
class myagent(BaseAgent):  # Wrong: class names should be CamelCase
    def processData(self,data):  # Wrong: method names should be snake_case
        return [x.upper() for x in data]  # Missing type hints and docstring
```

### Commit Guidelines

```bash
# Format: <type>(<scope>): <description>

# Types:
# feat: New feature
# fix: Bug fix
# docs: Documentation
# test: Tests
# refactor: Code refactoring
# perf: Performance improvement
# chore: Maintenance

# Examples:
git commit -m "feat(agents): add data processing agent"
git commit -m "fix(orchestrator): resolve task queue deadlock"
git commit -m "docs(api): update agent API documentation"
```

### Pull Request Process

1. Fork the repository
2. Create feature branch: `git checkout -b feature/my-feature`
3. Make changes with tests
4. Run linter: `flake8 agent_team/`
5. Run tests: `pytest tests/`
6. Commit changes
7. Push to fork
8. Create pull request

---

## Advanced Topics

### Performance Optimization

```python
# Use async for I/O-bound operations
import asyncio

class AsyncAgent(BaseAgent):
    async def _execute_task_async(self, task):
        # Async implementation
        results = await asyncio.gather(
            self._fetch_data(),
            self._process_data(),
            self._save_results()
        )
        return results
```

### Custom Storage Backends

```python
from agent_team.core.state_manager import StateManager

class RedisStateManager(StateManager):
    """State manager using Redis"""

    def __init__(self, redis_client, **kwargs):
        super().__init__(**kwargs)
        self.redis = redis_client

    def _save_state(self, state_data):
        """Save to Redis instead of file"""
        self.redis.set(f"state:{self.agent_id}", json.dumps(state_data))
```

### Distributed Agent Teams

```python
# Using message queues for distributed systems
from agent_team.core.orchestrator import AgentOrchestrator
import pika  # RabbitMQ

class DistributedOrchestrator(AgentOrchestrator):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.connection = pika.BlockingConnection()
        self.channel = self.connection.channel()

    def submit_task(self, agent_name, task, **kwargs):
        # Publish to message queue
        self.channel.basic_publish(
            exchange='',
            routing_key=f'agent.{agent_name}',
            body=json.dumps(task)
        )
        return task["id"]
```

---

## Appendix

### Useful Resources

- [Python asyncio documentation](https://docs.python.org/3/library/asyncio.html)
- [Design Patterns in Python](https://refactoring.guru/design-patterns/python)
- [Testing Best Practices](https://docs.pytest.org/en/stable/goodpractices.html)

### Common Patterns

See `examples/` directory for:
- Custom agent implementations
- Integration examples
- Advanced usage patterns
- Performance optimization techniques

---

*This manual is maintained by the development team. Contributions welcome!*
