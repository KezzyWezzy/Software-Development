# Best Practices Guide - Agent Team System

Version: 1.0.0
Last Updated: 2025-11-07

## Introduction

This guide provides best practices for using and developing with the Agent Team System. Following these practices ensures safe, efficient, and reliable operations.

---

## Table of Contents

1. [System Operation](#system-operation)
2. [Agent Development](#agent-development)
3. [Code Quality](#code-quality)
4. [Testing](#testing)
5. [Security](#security)
6. [Performance](#performance)
7. [Monitoring](#monitoring)
8. [Documentation](#documentation)
9. [Git Workflow](#git-workflow)
10. [What NOT to Do](#what-not-to-do)

---

## System Operation

### ✓ DO: Start with Manual Mode

**DO THIS:**
```bash
python -m agent_team config --autonomy manual
```

**DON'T DO THIS:**
```bash
python -m agent_team config --autonomy full_auto  # On first use
```

**WHY:** Manual mode lets you understand the system before giving it autonomy.

---

### ✓ DO: Regular Health Checks

**DO THIS:**
```bash
# Daily health check routine
python -m agent_team health-check
python -m agent_team status
python -m agent_team logs --level ERROR --since 24h
```

**DON'T DO THIS:**
```bash
# Ignoring health checks until something breaks
```

**WHY:** Proactive monitoring prevents issues before they become critical.

---

### ✓ DO: Review Approvals Carefully

**DO THIS:**
```bash
# Review what the task will do
python -m agent_team task info <task-id>

# Check agent history
python -m agent_team agent history <agent-name>

# Then approve
python -m agent_team approvals approve <task-id>
```

**DON'T DO THIS:**
```bash
# Blindly approving all pending tasks
python -m agent_team approvals approve-all  # DANGEROUS
```

**WHY:** Approval gates exist for your safety. Review before approving.

---

### ✓ DO: Create Backups Before Major Changes

**DO THIS:**
```bash
# Before major change
python -m agent_team backup create --label "before-v2-migration"

# Make changes
# ...

# Verify success before continuing
python -m agent_team validate
```

**DON'T DO THIS:**
```bash
# Making major changes without backup
# Hope it works
```

**WHY:** Backups enable quick recovery if something goes wrong.

---

### ✓ DO: Gradual Autonomy Increase

**DO THIS:**
```bash
# Start with manual
python -m agent_team config --autonomy manual

# After 1 week of successful operation
python -m agent_team config --autonomy semi_auto

# After 1 month of successful operation (if appropriate)
python -m agent_team config --autonomy full_auto
```

**DON'T DO THIS:**
```bash
# Jump straight to full autonomy without testing
```

**WHY:** Gradual increase builds trust and catches issues early.

---

## Agent Development

### ✓ DO: Inherit from BaseAgent

**DO THIS:**
```python
from agent_team.core.agent_base import BaseAgent

class MyAgent(BaseAgent):
    """Properly documented agent."""

    def _execute_task_impl(self, task):
        # Implementation
        pass
```

**DON'T DO THIS:**
```python
class MyAgent:  # Missing BaseAgent inheritance
    def execute(self, task):  # Wrong method name
        pass
```

**WHY:** BaseAgent provides logging, recovery, state management, and more.

---

### ✓ DO: Update Progress Regularly

**DO THIS:**
```python
def _execute_task_impl(self, task):
    self.update_progress(0, "Starting")

    self.update_progress(25, "Loading data")
    data = self.load_data()

    self.update_progress(50, "Processing")
    result = self.process(data)

    self.update_progress(75, "Saving results")
    self.save(result)

    self.update_progress(100, "Complete")
    return result
```

**DON'T DO THIS:**
```python
def _execute_task_impl(self, task):
    # No progress updates
    return self.do_everything()
```

**WHY:** Progress updates provide visibility and help debug stuck tasks.

---

### ✓ DO: Implement Recovery Logic

**DO THIS:**
```python
def _attempt_recovery(self, task, error):
    """Try to recover from error."""
    self.logger.info(f"Attempting recovery from {error}")

    if isinstance(error, NetworkError):
        # Retry with exponential backoff
        return self._retry_with_backoff(task)
    elif isinstance(error, ValidationError):
        # Try with default values
        return self._retry_with_defaults(task)

    return {"recovered": False}
```

**DON'T DO THIS:**
```python
def _attempt_recovery(self, task, error):
    """No recovery logic."""
    return {"recovered": False}
```

**WHY:** Recovery logic makes agents resilient to transient failures.

---

### ✓ DO: Log Important Events

**DO THIS:**
```python
def _execute_task_impl(self, task):
    self.logger.info("Task started", task_id=task["id"])

    try:
        result = self.process(task)
        self.logger.info("Task completed", result_summary=result)
        return result
    except Exception as e:
        self.logger.error("Task failed", error=str(e), traceback=traceback.format_exc())
        raise
```

**DON'T DO THIS:**
```python
def _execute_task_impl(self, task):
    return self.process(task)  # No logging
```

**WHY:** Logs are essential for debugging and monitoring.

---

## Code Quality

### ✓ DO: Write Type Hints

**DO THIS:**
```python
from typing import Dict, List, Optional, Any

def process_data(
    data: List[Dict[str, Any]],
    options: Optional[Dict[str, str]] = None
) -> Dict[str, List[str]]:
    """Process data with options."""
    # Implementation
    pass
```

**DON'T DO THIS:**
```python
def process_data(data, options=None):  # No type hints
    pass
```

**WHY:** Type hints improve code quality and enable better IDE support.

---

### ✓ DO: Write Docstrings

**DO THIS:**
```python
def calculate_metrics(self, data: List[float]) -> Dict[str, float]:
    """
    Calculate statistical metrics for the data.

    Args:
        data: List of numerical values to analyze

    Returns:
        Dictionary with keys: mean, median, std_dev

    Raises:
        ValueError: If data is empty

    Example:
        >>> agent.calculate_metrics([1.0, 2.0, 3.0])
        {'mean': 2.0, 'median': 2.0, 'std_dev': 0.816}
    """
    # Implementation
```

**DON'T DO THIS:**
```python
def calculate_metrics(self, data):
    # Calculate stuff
    pass
```

**WHY:** Good documentation helps others (and future you) understand the code.

---

### ✓ DO: Keep Functions Small

**DO THIS:**
```python
def _execute_task_impl(self, task):
    data = self._load_data(task)
    processed = self._process_data(data)
    result = self._save_results(processed)
    return result

def _load_data(self, task):
    # 10 lines

def _process_data(self, data):
    # 15 lines

def _save_results(self, processed):
    # 10 lines
```

**DON'T DO THIS:**
```python
def _execute_task_impl(self, task):
    # 500 lines of code doing everything
```

**WHY:** Small functions are easier to test, understand, and maintain.

---

## Testing

### ✓ DO: Write Tests for Agents

**DO THIS:**
```python
import pytest

def test_agent_basic_execution(my_agent):
    """Test basic task execution."""
    task = {"name": "test", "params": {"input": "data"}}
    result = my_agent.execute_task(task)

    assert result["status"] == "success"
    assert result["output"] is not None

def test_agent_error_handling(my_agent):
    """Test error handling."""
    task = {"name": "failing_task", "params": {}}

    with pytest.raises(Exception):
        my_agent.execute_task(task, auto_recover=False)

def test_agent_recovery(my_agent):
    """Test recovery mechanism."""
    task = {"name": "recoverable_error", "params": {}}
    result = my_agent.execute_task(task, auto_recover=True)

    assert result is not None  # Should recover
```

**DON'T DO THIS:**
```python
# No tests written
# "I'll test it manually"
```

**WHY:** Tests catch bugs early and prevent regressions.

---

### ✓ DO: Test Edge Cases

**DO THIS:**
```python
@pytest.mark.parametrize("input_data,expected", [
    ([], []),  # Empty list
    ([1], [1]),  # Single item
    ([1, 2, 3], [1, 2, 3]),  # Normal case
    ([1] * 10000, [1] * 10000),  # Large input
    (None, ValueError),  # Null input
])
def test_process_edge_cases(agent, input_data, expected):
    if isinstance(expected, type) and issubclass(expected, Exception):
        with pytest.raises(expected):
            agent.process(input_data)
    else:
        assert agent.process(input_data) == expected
```

**DON'T DO THIS:**
```python
def test_process():
    # Only test happy path
    assert agent.process([1, 2, 3]) == [1, 2, 3]
```

**WHY:** Most bugs occur in edge cases.

---

## Security

### ✓ DO: Never Commit Secrets

**DO THIS:**
```python
import os

API_KEY = os.getenv("API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

if not API_KEY:
    raise ValueError("API_KEY environment variable not set")
```

**DON'T DO THIS:**
```python
API_KEY = "sk_live_123456789"  # NEVER DO THIS
DATABASE_URL = "postgres://user:password@host/db"  # NEVER DO THIS
```

**WHY:** Committed secrets can be accessed by anyone with repo access.

---

### ✓ DO: Validate All Input

**DO THIS:**
```python
def process_user_input(self, user_input: str) -> str:
    # Validate
    if not user_input:
        raise ValueError("Input cannot be empty")

    if len(user_input) > 1000:
        raise ValueError("Input too long")

    # Sanitize
    sanitized = user_input.strip()
    sanitized = re.sub(r'[^\w\s-]', '', sanitized)

    # Validate again after sanitization
    if not sanitized:
        raise ValueError("Input contains no valid characters")

    return sanitized
```

**DON'T DO THIS:**
```python
def process_user_input(self, user_input):
    # Directly use user input in SQL query
    query = f"SELECT * FROM users WHERE name = '{user_input}'"
    # SQL INJECTION VULNERABILITY!
```

**WHY:** Unvalidated input is the #1 security vulnerability.

---

### ✓ DO: Use Parameterized Queries

**DO THIS:**
```python
def get_user(self, user_id: int):
    query = "SELECT * FROM users WHERE id = ?"
    return self.db.execute(query, (user_id,))
```

**DON'T DO THIS:**
```python
def get_user(self, user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"
    return self.db.execute(query)  # SQL injection risk
```

**WHY:** Parameterized queries prevent SQL injection.

---

## Performance

### ✓ DO: Use Batch Operations

**DO THIS:**
```python
def process_items(self, items: List[Item]) -> List[Result]:
    # Process in batches
    batch_size = 100
    results = []

    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        batch_results = self.process_batch(batch)
        results.extend(batch_results)

        # Update progress
        progress = (i + len(batch)) / len(items) * 100
        self.update_progress(progress, f"Processed {i + len(batch)}/{len(items)}")

    return results
```

**DON'T DO THIS:**
```python
def process_items(self, items):
    results = []
    for item in items:
        # Process one at a time with separate DB query
        result = self.db.query(f"INSERT INTO results VALUES ({item})")
        results.append(result)
    return results
```

**WHY:** Batch operations are much more efficient.

---

### ✓ DO: Add Indexes to Frequent Queries

**DO THIS:**
```python
# In database schema
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_tasks_status ON tasks(status, created_at);
```

**DON'T DO THIS:**
```python
# No indexes
# Wonder why queries are slow
```

**WHY:** Indexes dramatically improve query performance.

---

## Monitoring

### ✓ DO: Monitor Key Metrics

**DO THIS:**
```python
def _execute_task_impl(self, task):
    start_time = time.time()

    try:
        result = self.process(task)

        # Log metrics
        duration_ms = (time.time() - start_time) * 1000
        self.logger.log_metric("task_duration", duration_ms, unit="ms", task_type=task["name"])
        self.logger.log_metric("task_success", 1)

        return result
    except Exception as e:
        self.logger.log_metric("task_failure", 1, error_type=type(e).__name__)
        raise
```

**DON'T DO THIS:**
```python
def _execute_task_impl(self, task):
    return self.process(task)  # No metrics
```

**WHY:** Metrics help identify performance issues and trends.

---

## Documentation

### ✓ DO: Keep Documentation Updated

**DO THIS:**
```python
# When you change a function, update the docstring
def process_data(self, data: List[str], new_param: bool = False) -> List[str]:
    """
    Process input data.

    Args:
        data: List of strings to process
        new_param: New parameter added in v1.2 (default: False)

    Returns:
        Processed strings

    Changed in version 1.2:
        Added new_param parameter
    """
```

**DON'T DO THIS:**
```python
# Change function but leave old docstring
def process_data(self, data, new_param=False):
    """Process input data."""  # Outdated, doesn't mention new_param
```

**WHY:** Outdated documentation is worse than no documentation.

---

## Git Workflow

### ✓ DO: Write Descriptive Commit Messages

**DO THIS:**
```bash
git commit -m "feat(agents): add retry logic to database agent

- Implement exponential backoff
- Add max retry configuration
- Log retry attempts for debugging

Fixes #123"
```

**DON'T DO THIS:**
```bash
git commit -m "fix"
git commit -m "update"
git commit -m "changes"
```

**WHY:** Good commit messages help understand the history.

---

### ✓ DO: Use Feature Branches

**DO THIS:**
```bash
git checkout -b feature/add-data-processing-agent
# Make changes
git commit -m "feat: add data processing agent"
git push origin feature/add-data-processing-agent
# Create pull request
```

**DON'T DO THIS:**
```bash
git checkout main
# Make changes directly on main
git commit -m "stuff"
git push origin main
```

**WHY:** Branches enable isolated development and code review.

---

## What NOT to Do

### ✗ DON'T: Run Full Autonomy in Production (Initially)

**WHY:** Start with manual or semi-auto mode to build confidence.

---

### ✗ DON'T: Ignore Error Logs

**WHY:** Errors indicate problems that will worsen if ignored.

---

### ✗ DON'T: Skip Testing

**WHY:** Untested code will break in production.

---

### ✗ DON'T: Hardcode Configuration

**WHY:** Configuration should be external and environment-specific.

---

### ✗ DON'T: Commit Generated Files

**WHY:** Generated files should be created by build process.

---

### ✗ DON'T: Use Global State

**WHY:** Global state makes code hard to test and causes bugs.

---

### ✗ DON'T: Optimize Prematurely

**WHY:** "Premature optimization is the root of all evil" - Donald Knuth. Profile first.

---

### ✗ DON'T: Catch and Ignore Exceptions

**DO THIS:**
```python
try:
    result = dangerous_operation()
except SpecificException as e:
    self.logger.error(f"Operation failed: {e}")
    # Handle or re-raise
    raise
```

**DON'T DO THIS:**
```python
try:
    result = dangerous_operation()
except:
    pass  # Silent failure - VERY BAD
```

---

## Quick Reference Checklist

### Before Each Release

- [ ] All tests pass
- [ ] Code coverage > 80%
- [ ] Documentation updated
- [ ] Changelog updated
- [ ] Version number bumped
- [ ] Security scan passed
- [ ] Performance benchmarks acceptable
- [ ] Backup created

### Daily Operations

- [ ] Health check performed
- [ ] Error logs reviewed
- [ ] Pending approvals reviewed
- [ ] Metrics checked
- [ ] Backups verified

### Weekly Maintenance

- [ ] Old logs cleaned up
- [ ] Old backups cleaned up
- [ ] Security updates applied
- [ ] Performance review
- [ ] Documentation review

---

## Summary

Following these best practices ensures:
- **Safety**: Multiple safeguards prevent accidents
- **Reliability**: Robust error handling and recovery
- **Performance**: Efficient operations at scale
- **Maintainability**: Clean, well-documented code
- **Security**: Protected against common vulnerabilities

Remember: **When in doubt, err on the side of caution!**

---

*This guide is a living document. Suggestions for improvements are welcome!*
