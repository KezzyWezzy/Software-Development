# Agent Team System - Operations Manual

Version: 1.0.0
Last Updated: 2025-11-07

## Table of Contents

1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
3. [System Architecture](#system-architecture)
4. [Operating the System](#operating-the-system)
5. [Autonomy Levels](#autonomy-levels)
6. [Monitoring and Status](#monitoring-and-status)
7. [Backup and Recovery](#backup-and-recovery)
8. [Troubleshooting](#troubleshooting)
9. [Best Practices](#best-practices)
10. [Reminders System](#reminders-system)

---

## Introduction

The Agent Team System is a comprehensive, autonomous agent orchestration platform designed for software development. It provides:

- **Multiple specialized agents** for different tasks
- **Flexible autonomy levels** from manual to fully automatic
- **Advanced logging and monitoring**
- **Automatic backup and recovery**
- **Best practices enforcement**
- **Scheduled reminders**

### Who Should Use This Manual

- **DevOps Engineers**: Setting up and maintaining the system
- **Team Leads**: Configuring autonomy and oversight
- **Developers**: Daily operation and task submission
- **QA Engineers**: Monitoring and validation

---

## Getting Started

### Prerequisites

- Python 3.9 or higher
- Git
- 4GB RAM minimum (8GB recommended)
- 10GB disk space

### Installation

```bash
# Clone the repository
cd /home/user/Software-Development

# Install dependencies
pip install -r requirements.txt

# Initialize the system
python -m agent_team init

# Start the system
python -m agent_team start
```

### First-Time Setup

1. **Configure Workspace**
   ```bash
   export AGENT_WORKSPACE=/path/to/workspace
   ```

2. **Set Autonomy Level**
   ```bash
   python -m agent_team config --autonomy semi_auto
   ```

3. **Start Dashboard**
   ```bash
   python -m agent_team dashboard --port 8080
   ```

4. **Verify Installation**
   ```bash
   python -m agent_team health-check
   ```

---

## System Architecture

### Core Components

```
┌─────────────────────────────────────────┐
│         Orchestrator                    │
│  (Central Coordination & Scheduling)    │
└──────────────┬──────────────────────────┘
               │
       ┌───────┴───────┐
       │               │
┌──────▼──────┐ ┌─────▼──────┐
│   Agents    │ │  Systems   │
│             │ │            │
│ • Code Gen  │ │ • Logging  │
│ • Testing   │ │ • Backup   │
│ • Docs      │ │ • Monitor  │
│ • Database  │ │ • Reminder │
│ • Recovery  │ │ • Metrics  │
└─────────────┘ └────────────┘
```

### Agent Types

1. **Code Generator Agent**: Generates code from specifications
2. **Testing Agent**: Creates and runs tests
3. **Documentation Agent**: Auto-generates documentation
4. **Database Agent**: Manages schemas and migrations
5. **Validation Agent**: Code quality and security checks
6. **Recovery Agent**: Handles errors and recovery

### Support Systems

1. **Logging System**: Structured logging with multiple levels
2. **Backup System**: Automatic snapshots and versioning
3. **Monitoring System**: Real-time health and status
4. **Reminder System**: Scheduled best practice reminders
5. **State Manager**: Persistent state with recovery

---

## Operating the System

### Starting the System

```bash
# Start all components
python -m agent_team start

# Start specific components
python -m agent_team start --components orchestrator,agents

# Start in background
python -m agent_team start --daemon
```

### Stopping the System

```bash
# Graceful shutdown
python -m agent_team stop

# Force stop
python -m agent_team stop --force

# Stop specific agent
python -m agent_team stop --agent code_generator
```

### Submitting Tasks

#### Via CLI

```bash
# Submit a task
python -m agent_team task submit \
  --agent code_generator \
  --name "implement-user-auth" \
  --priority high \
  --params '{"spec_file": "specs/auth.md"}'
```

#### Via Python API

```python
from agent_team import AgentOrchestrator, AgentPriority

orchestrator = AgentOrchestrator()

task_id = orchestrator.submit_task(
    agent_name="code_generator",
    task={
        "name": "implement-user-auth",
        "spec_file": "specs/auth.md"
    },
    priority=AgentPriority.HIGH
)

# Monitor task
status = orchestrator.get_task_status(task_id)
print(f"Status: {status['status']}")
```

### Checking Status

```bash
# Overall system status
python -m agent_team status

# Agent-specific status
python -m agent_team status --agent testing_agent

# Task status
python -m agent_team task status <task-id>

# Queue status
python -m agent_team queue
```

---

## Autonomy Levels

The system supports three autonomy levels:

### 1. Manual Mode (`manual`)

- **Every action requires approval**
- Safest mode for sensitive operations
- Best for: Production systems, critical infrastructure

```bash
python -m agent_team config --autonomy manual
```

**Behavior:**
- All tasks go to approval queue
- User must explicitly approve each operation
- Maximum oversight and control

### 2. Semi-Autonomous Mode (`semi_auto`)

- **Pre-approved categories run automatically**
- Balanced safety and productivity
- Best for: Development teams, staging environments

```bash
python -m agent_team config --autonomy semi_auto
```

**Pre-approved Operations:**
- Read files
- Write files (non-config)
- Run tests
- Database queries (read-only)
- Create backups

**Require Approval:**
- Delete files
- Git push
- Database writes
- Config changes
- Package installation

### 3. Full Autonomous Mode (`full_auto`)

- **Maximum automation within safety boundaries**
- Highest productivity
- Best for: Personal projects, trusted environments

```bash
python -m agent_team config --autonomy full_auto
```

**Auto-approved:**
- Most development operations
- Testing and validation
- Documentation updates
- Git commits
- Database operations

**Always Require Approval:**
- Git push to remote
- System restore from backup
- Production deployments

### Changing Autonomy Levels

```bash
# View current level
python -m agent_team config --show autonomy

# Change level
python -m agent_team config --autonomy <level>

# Temporarily override for specific task
python -m agent_team task submit --autonomy manual --agent <agent> ...
```

### Approving Tasks

When in manual or semi_auto mode:

```bash
# View pending approvals
python -m agent_team approvals list

# Approve a task
python -m agent_team approvals approve <task-id>

# Reject a task
python -m agent_team approvals reject <task-id> --reason "Security concern"

# Approve all from specific agent
python -m agent_team approvals approve-all --agent testing_agent
```

---

## Monitoring and Status

### Real-Time Dashboard

```bash
# Start web dashboard
python -m agent_team dashboard --port 8080

# Open in browser: http://localhost:8080
```

Dashboard features:
- Live agent status
- Task queue visualization
- System health metrics
- Log viewer
- Performance graphs

### Command-Line Monitoring

```bash
# Watch status (updates every 2 seconds)
watch -n 2 python -m agent_team status

# Stream logs
python -m agent_team logs --follow

# Filter logs by level
python -m agent_team logs --level ERROR

# Search logs
python -m agent_team logs --search "task failed"
```

### Health Checks

```bash
# Overall health
python -m agent_team health-check

# Detailed health report
python -m agent_team health-check --detailed

# Check specific agent
python -m agent_team health-check --agent code_generator
```

### Metrics and Statistics

```bash
# Task statistics
python -m agent_team metrics tasks

# Agent performance
python -m agent_team metrics agents

# Success rates
python -m agent_team metrics success-rate

# Export metrics to JSON
python -m agent_team metrics export --output metrics.json
```

---

## Backup and Recovery

### Automatic Backups

The system automatically creates backups:
- **Every 5 minutes**: Incremental state snapshot
- **Every hour**: Full system snapshot
- **Before destructive operations**: Safety snapshot
- **On shutdown**: Final state snapshot

### Manual Backups

```bash
# Create manual snapshot
python -m agent_team backup create --label "before-major-change"

# Create snapshot with version bump
python -m agent_team backup create --increment major --label "v2.0-release"

# List all snapshots
python -m agent_team backup list

# View snapshot details
python -m agent_team backup info <snapshot-id>
```

### Recovery Operations

```bash
# List available recovery points
python -m agent_team recover list

# Preview recovery (dry-run)
python -m agent_team recover --to <snapshot-id> --dry-run

# Perform recovery
python -m agent_team recover --to <snapshot-id>

# Recover specific agent state
python -m agent_team recover --agent code_generator --to <snapshot-id>
```

### Version Control

```bash
# View version history
python -m agent_team version history

# Compare versions
python -m agent_team version diff v1.2.0 v1.3.0

# Tag current version
python -m agent_team version tag --label "stable-release"

# Rollback to version
python -m agent_team version rollback v1.2.0
```

---

## Troubleshooting

### Common Issues

#### 1. Agent Not Responding

**Symptoms:**
- Agent shows "running" but no progress
- Tasks stuck in queue

**Solutions:**
```bash
# Check agent health
python -m agent_team health-check --agent <agent-name>

# View agent logs
python -m agent_team logs --agent <agent-name> --level ERROR

# Restart agent
python -m agent_team restart --agent <agent-name>

# If unresponsive, force restart
python -m agent_team restart --agent <agent-name> --force
```

#### 2. High Memory Usage

**Symptoms:**
- System slowdown
- Out of memory errors

**Solutions:**
```bash
# Check resource usage
python -m agent_team metrics resources

# Clear old logs
python -m agent_team logs cleanup --older-than 30d

# Clean up old snapshots
python -m agent_team backup cleanup --keep 50

# Restart with memory limits
python -m agent_team start --max-memory 4GB
```

#### 3. Task Failures

**Symptoms:**
- Tasks completing with errors
- High failure rate

**Solutions:**
```bash
# View failed tasks
python -m agent_team tasks --status failed --limit 10

# Analyze failure patterns
python -m agent_team analyze failures

# Retry failed task
python -m agent_team task retry <task-id>

# Check agent error history
python -m agent_team logs --agent <agent-name> --level ERROR
```

#### 4. Database Errors

**Symptoms:**
- State loading failures
- Corruption warnings

**Solutions:**
```bash
# Validate state
python -m agent_team validate state

# Repair state files
python -m agent_team repair state

# Restore from backup if needed
python -m agent_team recover --to <last-good-snapshot>
```

### Getting Help

```bash
# View system diagnostics
python -m agent_team diagnostics

# Generate debug report
python -m agent_team debug-report --output debug.zip

# Check system requirements
python -m agent_team check-requirements

# View logs for specific time period
python -m agent_team logs --start "2025-11-07 10:00" --end "2025-11-07 11:00"
```

---

## Best Practices

### Daily Operations

1. **Morning Checklist**
   ```bash
   python -m agent_team health-check
   python -m agent_team status
   python -m agent_team logs --level ERROR --since 24h
   ```

2. **Review Pending Approvals**
   ```bash
   python -m agent_team approvals list
   # Review and approve/reject as needed
   ```

3. **Monitor Dashboard**
   - Check agent health
   - Review task completion rates
   - Watch for anomalies

### Weekly Maintenance

1. **Review Logs**
   ```bash
   python -m agent_team logs analyze --period 7d
   ```

2. **Clean Up**
   ```bash
   python -m agent_team logs cleanup --older-than 30d
   python -m agent_team backup cleanup --keep 100
   ```

3. **Update Documentation**
   ```bash
   python -m agent_team docs update
   ```

4. **Review Metrics**
   ```bash
   python -m agent_team metrics report --period weekly
   ```

### Monthly Tasks

1. **Version Snapshot**
   ```bash
   python -m agent_team backup create --increment minor --label "monthly-$(date +%Y-%m)"
   ```

2. **Performance Review**
   ```bash
   python -m agent_team metrics report --period monthly --export
   ```

3. **System Audit**
   ```bash
   python -m agent_team audit --comprehensive
   ```

---

## Reminders System

### Viewing Reminders

```bash
# List all reminders
python -m agent_team reminders list

# View upcoming reminders
python -m agent_team reminders upcoming

# View reminders by type
python -m agent_team reminders list --type best_practice
```

### Managing Reminders

```bash
# Snooze a reminder
python -m agent_team reminders snooze <reminder-id> --duration 1h

# Dismiss a reminder
python -m agent_team reminders dismiss <reminder-id>

# Create custom reminder
python -m agent_team reminders create \
  --title "Review test coverage" \
  --message "Ensure all modules have >80% coverage" \
  --type testing \
  --frequency daily \
  --priority high
```

### Best Practice Reminders

The system automatically reminds you about:

- **Critical Security Practices**: Daily
- **Testing Practices**: Before commits
- **Code Review**: Before pushes
- **Documentation**: Weekly
- **Backup Verification**: Daily
- **Performance Checks**: Weekly

Configure reminder frequency:

```bash
python -m agent_team reminders configure \
  --type best_practice \
  --frequency daily \
  --priority high
```

---

## Emergency Procedures

### System Crash Recovery

1. **Verify backup integrity**
   ```bash
   python -m agent_team backup validate
   ```

2. **Restore from last good state**
   ```bash
   python -m agent_team recover --to last-good
   ```

3. **Restart system**
   ```bash
   python -m agent_team start --safe-mode
   ```

### Data Corruption

1. **Stop system immediately**
   ```bash
   python -m agent_team stop --force
   ```

2. **Validate state**
   ```bash
   python -m agent_team validate state
   ```

3. **Restore from backup**
   ```bash
   python -m agent_team recover --to <snapshot-before-corruption>
   ```

### Security Incident

1. **Switch to manual mode**
   ```bash
   python -m agent_team config --autonomy manual
   ```

2. **Review audit logs**
   ```bash
   python -m agent_team logs --audit --since 24h
   ```

3. **Revoke all approvals**
   ```bash
   python -m agent_team approvals revoke-all
   ```

---

## Support and Resources

### Documentation
- Development Manual: `manuals/DEVELOPMENT_MANUAL.md`
- Best Practices: `manuals/BEST_PRACTICES.md`
- Troubleshooting Guide: `manuals/TROUBLESHOOTING.md`
- API Reference: `docs/api/`

### Getting Help
- GitHub Issues: Report bugs and request features
- Discussion Forum: Community support
- Email Support: For enterprise users

### Version Information

Current Version: 1.0.0

Check for updates:
```bash
python -m agent_team version check
```

---

*This manual is maintained by the Agent Team System. Last updated: 2025-11-07*
