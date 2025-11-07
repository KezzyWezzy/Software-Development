"""
Structured Logging System

Advanced logging with structured data, aggregation, and analysis capabilities.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from enum import Enum


class LogLevel(Enum):
    """Log levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class StructuredLogger:
    """
    Advanced structured logger with JSON output and rich metadata.

    Features:
    - Structured JSON logging
    - Context enrichment
    - Multiple output destinations
    - Log rotation
    - Performance tracking
    """

    def __init__(
        self,
        name: str,
        log_dir: Path,
        level: LogLevel = LogLevel.INFO,
        enable_console: bool = True
    ):
        self.name = name
        self.log_dir = log_dir
        self.level = level
        self.enable_console = enable_console

        # Setup
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = log_dir / f"{name}.jsonl"

        # Context stack for hierarchical logging
        self.context_stack: List[Dict[str, Any]] = []

        # Setup logger
        self._setup_logger()

    def _setup_logger(self):
        """Setup Python logger"""
        self.logger = logging.getLogger(f"structured.{self.name}")
        self.logger.setLevel(getattr(logging, self.level.value))

        # Clear existing handlers
        self.logger.handlers.clear()

        # JSON formatter
        class JsonFormatter(logging.Formatter):
            def format(self, record):
                log_entry = {
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                    "module": record.module,
                    "function": record.funcName,
                    "line": record.lineno,
                }

                # Add all extra fields
                for key, value in record.__dict__.items():
                    if key not in ['name', 'msg', 'args', 'created', 'filename', 'funcName',
                                   'levelname', 'levelno', 'lineno', 'module', 'msecs',
                                   'message', 'pathname', 'process', 'processName',
                                   'relativeCreated', 'thread', 'threadName', 'exc_info',
                                   'exc_text', 'stack_info']:
                        log_entry[key] = value

                # Add exception info if present
                if record.exc_info:
                    log_entry['exception'] = self.format_exception(record.exc_info)

                return json.dumps(log_entry)

            def format_exception(self, exc_info):
                import traceback
                return {
                    'type': exc_info[0].__name__ if exc_info[0] else None,
                    'message': str(exc_info[1]) if exc_info[1] else None,
                    'traceback': traceback.format_exception(*exc_info)
                }

        # File handler
        file_handler = logging.FileHandler(self.log_file)
        file_handler.setFormatter(JsonFormatter())
        self.logger.addHandler(file_handler)

        # Console handler (optional)
        if self.enable_console:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(
                logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            )
            self.logger.addHandler(console_handler)

    def debug(self, message: str, **kwargs):
        """Log debug message"""
        self._log(LogLevel.DEBUG, message, kwargs)

    def info(self, message: str, **kwargs):
        """Log info message"""
        self._log(LogLevel.INFO, message, kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message"""
        self._log(LogLevel.WARNING, message, kwargs)

    def error(self, message: str, **kwargs):
        """Log error message"""
        self._log(LogLevel.ERROR, message, kwargs)

    def critical(self, message: str, **kwargs):
        """Log critical message"""
        self._log(LogLevel.CRITICAL, message, kwargs)

    def _log(self, level: LogLevel, message: str, extra: Dict[str, Any]):
        """Internal logging method"""
        # Enrich with context
        for context in self.context_stack:
            extra.update(context)

        # Get logger method
        log_method = getattr(self.logger, level.value.lower())

        # Log with extra fields
        log_method(message, extra=extra)

    def push_context(self, **kwargs):
        """Push a new logging context"""
        self.context_stack.append(kwargs)

    def pop_context(self):
        """Pop the current logging context"""
        if self.context_stack:
            self.context_stack.pop()

    def log_event(self, event_type: str, event_data: Dict[str, Any], level: LogLevel = LogLevel.INFO):
        """
        Log a structured event

        Args:
            event_type: Type of event (e.g., 'task_started', 'error_occurred')
            event_data: Event data dictionary
            level: Log level
        """
        self._log(level, f"Event: {event_type}", {
            "event_type": event_type,
            "event_data": event_data,
        })

    def log_metric(self, metric_name: str, value: float, unit: Optional[str] = None, **tags):
        """
        Log a metric value

        Args:
            metric_name: Name of the metric
            value: Metric value
            unit: Optional unit
            tags: Additional tags for the metric
        """
        self.info(f"Metric: {metric_name} = {value}", **{
            "metric_name": metric_name,
            "metric_value": value,
            "metric_unit": unit,
            "metric_tags": tags,
        })

    def log_performance(self, operation: str, duration_ms: float, **extra):
        """
        Log performance data

        Args:
            operation: Operation name
            duration_ms: Duration in milliseconds
            extra: Additional fields
        """
        self.info(f"Performance: {operation} took {duration_ms:.2f}ms", **{
            "operation": operation,
            "duration_ms": duration_ms,
            "performance": True,
            **extra
        })

    def log_audit(self, action: str, user: str, resource: str, result: str, **extra):
        """
        Log audit trail entry

        Args:
            action: Action performed
            user: User/agent who performed the action
            resource: Resource affected
            result: Result of the action
            extra: Additional audit fields
        """
        self.info(f"Audit: {user} {action} {resource}", **{
            "audit": True,
            "action": action,
            "user": user,
            "resource": resource,
            "result": result,
            **extra
        })

    def get_recent_logs(self, count: int = 100, level: Optional[LogLevel] = None) -> List[Dict[str, Any]]:
        """
        Get recent log entries

        Args:
            count: Number of entries to retrieve
            level: Optional filter by log level

        Returns:
            List of log entries
        """
        if not self.log_file.exists():
            return []

        logs = []
        try:
            with open(self.log_file, 'r') as f:
                for line in f:
                    try:
                        log_entry = json.loads(line.strip())
                        if level is None or log_entry.get("level") == level.value:
                            logs.append(log_entry)
                    except json.JSONDecodeError:
                        continue

            # Return last N entries
            return logs[-count:]

        except Exception as e:
            self.error(f"Failed to read logs: {e}")
            return []

    def search_logs(
        self,
        query: str,
        level: Optional[LogLevel] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Search logs with filters

        Args:
            query: Search query (matches message)
            level: Optional log level filter
            start_time: Optional start time (ISO format)
            end_time: Optional end time (ISO format)
            limit: Maximum results

        Returns:
            Matching log entries
        """
        if not self.log_file.exists():
            return []

        results = []
        query_lower = query.lower()

        try:
            with open(self.log_file, 'r') as f:
                for line in f:
                    if len(results) >= limit:
                        break

                    try:
                        log_entry = json.loads(line.strip())

                        # Apply filters
                        if level and log_entry.get("level") != level.value:
                            continue

                        if start_time and log_entry.get("timestamp", "") < start_time:
                            continue

                        if end_time and log_entry.get("timestamp", "") > end_time:
                            continue

                        # Search in message
                        message = log_entry.get("message", "").lower()
                        if query_lower in message:
                            results.append(log_entry)

                    except json.JSONDecodeError:
                        continue

            return results

        except Exception as e:
            self.error(f"Failed to search logs: {e}")
            return []

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get log statistics

        Returns:
            Statistics dictionary
        """
        if not self.log_file.exists():
            return {"total_entries": 0}

        stats = {
            "total_entries": 0,
            "by_level": {level.value: 0 for level in LogLevel},
            "errors": [],
            "warnings": [],
        }

        try:
            with open(self.log_file, 'r') as f:
                for line in f:
                    try:
                        log_entry = json.loads(line.strip())
                        stats["total_entries"] += 1

                        level = log_entry.get("level", "INFO")
                        if level in stats["by_level"]:
                            stats["by_level"][level] += 1

                        # Collect recent errors and warnings
                        if level == "ERROR" and len(stats["errors"]) < 10:
                            stats["errors"].append(log_entry)
                        elif level == "WARNING" and len(stats["warnings"]) < 10:
                            stats["warnings"].append(log_entry)

                    except json.JSONDecodeError:
                        continue

        except Exception as e:
            self.error(f"Failed to get statistics: {e}")

        return stats


class LogAggregator:
    """
    Aggregates logs from multiple sources

    Features:
    - Multi-source aggregation
    - Filtering and search
    - Statistics generation
    - Export capabilities
    """

    def __init__(self, log_dir: Path):
        self.log_dir = log_dir

    def aggregate_logs(
        self,
        sources: Optional[List[str]] = None,
        level: Optional[LogLevel] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Aggregate logs from multiple sources

        Args:
            sources: Optional list of log sources (file names)
            level: Optional log level filter
            start_time: Optional start time
            end_time: Optional end time

        Returns:
            Aggregated log entries sorted by timestamp
        """
        all_logs = []

        # Get log files
        if sources:
            log_files = [self.log_dir / f"{source}.jsonl" for source in sources]
        else:
            log_files = list(self.log_dir.glob("*.jsonl"))

        # Read all log files
        for log_file in log_files:
            if not log_file.exists():
                continue

            try:
                with open(log_file, 'r') as f:
                    for line in f:
                        try:
                            log_entry = json.loads(line.strip())

                            # Apply filters
                            if level and log_entry.get("level") != level.value:
                                continue

                            if start_time and log_entry.get("timestamp", "") < start_time:
                                continue

                            if end_time and log_entry.get("timestamp", "") > end_time:
                                continue

                            # Add source
                            log_entry["source"] = log_file.stem

                            all_logs.append(log_entry)

                        except json.JSONDecodeError:
                            continue

            except Exception:
                continue

        # Sort by timestamp
        all_logs.sort(key=lambda x: x.get("timestamp", ""))

        return all_logs

    def generate_report(self, output_file: Path):
        """
        Generate a log report

        Args:
            output_file: Output file path
        """
        logs = self.aggregate_logs()

        report = {
            "generated_at": datetime.utcnow().isoformat(),
            "total_entries": len(logs),
            "by_level": {},
            "by_source": {},
            "error_summary": [],
            "warning_summary": [],
        }

        # Analyze logs
        for log in logs:
            level = log.get("level", "INFO")
            source = log.get("source", "unknown")

            report["by_level"][level] = report["by_level"].get(level, 0) + 1
            report["by_source"][source] = report["by_source"].get(source, 0) + 1

            if level == "ERROR" and len(report["error_summary"]) < 50:
                report["error_summary"].append({
                    "timestamp": log.get("timestamp"),
                    "source": source,
                    "message": log.get("message"),
                })

            if level == "WARNING" and len(report["warning_summary"]) < 50:
                report["warning_summary"].append({
                    "timestamp": log.get("timestamp"),
                    "source": source,
                    "message": log.get("message"),
                })

        # Write report
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
