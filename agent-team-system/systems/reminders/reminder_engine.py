"""
Reminder Engine

Scheduled reminder system for best practices, maintenance tasks, and important actions.
"""

import json
import threading
import time
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
import uuid


class ReminderType(Enum):
    """Types of reminders"""
    BEST_PRACTICE = "best_practice"
    CODE_REVIEW = "code_review"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    BACKUP = "backup"
    MAINTENANCE = "maintenance"
    SECURITY = "security"
    PERFORMANCE = "performance"


class ReminderPriority(Enum):
    """Reminder priority levels"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4


class ReminderFrequency(Enum):
    """Reminder frequency"""
    ONCE = "once"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"


class Reminder:
    """Individual reminder"""

    def __init__(
        self,
        reminder_id: str,
        title: str,
        message: str,
        reminder_type: ReminderType,
        priority: ReminderPriority,
        frequency: ReminderFrequency,
        next_trigger: datetime,
        callback: Optional[Callable] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.reminder_id = reminder_id
        self.title = title
        self.message = message
        self.reminder_type = reminder_type
        self.priority = priority
        self.frequency = frequency
        self.next_trigger = next_trigger
        self.callback = callback
        self.metadata = metadata or {}

        self.created_at = datetime.utcnow()
        self.last_triggered = None
        self.trigger_count = 0
        self.snoozed_until = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "reminder_id": self.reminder_id,
            "title": self.title,
            "message": self.message,
            "reminder_type": self.reminder_type.value,
            "priority": self.priority.value,
            "frequency": self.frequency.value,
            "next_trigger": self.next_trigger.isoformat(),
            "created_at": self.created_at.isoformat(),
            "last_triggered": self.last_triggered.isoformat() if self.last_triggered else None,
            "trigger_count": self.trigger_count,
            "snoozed_until": self.snoozed_until.isoformat() if self.snoozed_until else None,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Reminder':
        """Create from dictionary"""
        reminder = cls(
            reminder_id=data["reminder_id"],
            title=data["title"],
            message=data["message"],
            reminder_type=ReminderType(data["reminder_type"]),
            priority=ReminderPriority(data["priority"]),
            frequency=ReminderFrequency(data["frequency"]),
            next_trigger=datetime.fromisoformat(data["next_trigger"]),
            metadata=data.get("metadata", {})
        )

        reminder.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("last_triggered"):
            reminder.last_triggered = datetime.fromisoformat(data["last_triggered"])
        reminder.trigger_count = data.get("trigger_count", 0)
        if data.get("snoozed_until"):
            reminder.snoozed_until = datetime.fromisoformat(data["snoozed_until"])

        return reminder


class ReminderEngine:
    """
    Reminder engine with scheduling and persistence

    Features:
    - Multiple reminder types
    - Flexible scheduling (one-time, recurring)
    - Priority-based triggering
    - Snooze functionality
    - Callback support
    - Persistent storage
    """

    def __init__(self, workspace_dir: Path):
        self.workspace_dir = workspace_dir
        self.reminders_dir = workspace_dir / "reminders"
        self.reminders_file = self.reminders_dir / "reminders.json"

        self.reminders: Dict[str, Reminder] = {}
        self.running = False
        self.check_thread: Optional[threading.Thread] = None

        # Callbacks for reminder types
        self.callbacks: Dict[ReminderType, List[Callable]] = {
            rtype: [] for rtype in ReminderType
        }

        # Setup
        self.reminders_dir.mkdir(parents=True, exist_ok=True)
        self._load_reminders()

    def _load_reminders(self):
        """Load reminders from disk"""
        if not self.reminders_file.exists():
            return

        try:
            with open(self.reminders_file, 'r') as f:
                data = json.load(f)

            for reminder_data in data.get("reminders", []):
                try:
                    reminder = Reminder.from_dict(reminder_data)
                    self.reminders[reminder.reminder_id] = reminder
                except Exception as e:
                    print(f"Failed to load reminder: {e}")

        except Exception as e:
            print(f"Failed to load reminders file: {e}")

    def _save_reminders(self):
        """Save reminders to disk"""
        data = {
            "reminders": [r.to_dict() for r in self.reminders.values()],
            "last_updated": datetime.utcnow().isoformat(),
        }

        with open(self.reminders_file, 'w') as f:
            json.dump(data, f, indent=2)

    def create_reminder(
        self,
        title: str,
        message: str,
        reminder_type: ReminderType,
        trigger_at: datetime,
        priority: ReminderPriority = ReminderPriority.MEDIUM,
        frequency: ReminderFrequency = ReminderFrequency.ONCE,
        callback: Optional[Callable] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new reminder

        Args:
            title: Reminder title
            message: Reminder message
            reminder_type: Type of reminder
            trigger_at: When to trigger
            priority: Priority level
            frequency: How often to repeat
            callback: Optional callback function
            metadata: Optional metadata

        Returns:
            Reminder ID
        """
        reminder_id = f"reminder_{uuid.uuid4().hex[:12]}"

        reminder = Reminder(
            reminder_id=reminder_id,
            title=title,
            message=message,
            reminder_type=reminder_type,
            priority=priority,
            frequency=frequency,
            next_trigger=trigger_at,
            callback=callback,
            metadata=metadata
        )

        self.reminders[reminder_id] = reminder
        self._save_reminders()

        return reminder_id

    def create_recurring_reminder(
        self,
        title: str,
        message: str,
        reminder_type: ReminderType,
        frequency: ReminderFrequency,
        start_time: Optional[datetime] = None,
        priority: ReminderPriority = ReminderPriority.MEDIUM,
        **kwargs
    ) -> str:
        """
        Create a recurring reminder

        Args:
            title: Reminder title
            message: Reminder message
            reminder_type: Type of reminder
            frequency: Recurrence frequency
            start_time: When to start (default: now)
            priority: Priority level

        Returns:
            Reminder ID
        """
        if start_time is None:
            start_time = datetime.utcnow()

        # Calculate first trigger time based on frequency
        if frequency == ReminderFrequency.HOURLY:
            next_trigger = start_time + timedelta(hours=1)
        elif frequency == ReminderFrequency.DAILY:
            next_trigger = start_time + timedelta(days=1)
        elif frequency == ReminderFrequency.WEEKLY:
            next_trigger = start_time + timedelta(weeks=1)
        elif frequency == ReminderFrequency.MONTHLY:
            next_trigger = start_time + timedelta(days=30)
        else:
            next_trigger = start_time

        return self.create_reminder(
            title=title,
            message=message,
            reminder_type=reminder_type,
            trigger_at=next_trigger,
            priority=priority,
            frequency=frequency,
            metadata=kwargs
        )

    def register_callback(self, reminder_type: ReminderType, callback: Callable):
        """Register a callback for a reminder type"""
        self.callbacks[reminder_type].append(callback)

    def snooze_reminder(self, reminder_id: str, duration_minutes: int = 60):
        """Snooze a reminder"""
        if reminder_id not in self.reminders:
            return False

        reminder = self.reminders[reminder_id]
        reminder.snoozed_until = datetime.utcnow() + timedelta(minutes=duration_minutes)
        self._save_reminders()

        return True

    def dismiss_reminder(self, reminder_id: str):
        """Dismiss a one-time reminder"""
        if reminder_id in self.reminders:
            reminder = self.reminders[reminder_id]
            if reminder.frequency == ReminderFrequency.ONCE:
                del self.reminders[reminder_id]
                self._save_reminders()
                return True

        return False

    def get_pending_reminders(self) -> List[Reminder]:
        """Get all pending reminders"""
        now = datetime.utcnow()
        pending = []

        for reminder in self.reminders.values():
            # Skip snoozed reminders
            if reminder.snoozed_until and now < reminder.snoozed_until:
                continue

            # Check if trigger time has passed
            if now >= reminder.next_trigger:
                pending.append(reminder)

        # Sort by priority (highest first) and then by trigger time
        pending.sort(key=lambda r: (-r.priority.value, r.next_trigger))

        return pending

    def start(self):
        """Start the reminder engine"""
        if self.running:
            return

        self.running = True
        self.check_thread = threading.Thread(target=self._check_loop, daemon=True)
        self.check_thread.start()

    def stop(self):
        """Stop the reminder engine"""
        self.running = False
        if self.check_thread:
            self.check_thread.join(timeout=5)

    def _check_loop(self):
        """Main loop for checking reminders"""
        while self.running:
            try:
                pending = self.get_pending_reminders()

                for reminder in pending:
                    self._trigger_reminder(reminder)

                # Check every 60 seconds
                time.sleep(60)

            except Exception as e:
                print(f"Reminder check loop error: {e}")
                time.sleep(60)

    def _trigger_reminder(self, reminder: Reminder):
        """Trigger a reminder"""
        print(f"\n{'='*60}")
        print(f"[{reminder.priority.name}] {reminder.title}")
        print(f"Type: {reminder.reminder_type.value}")
        print(f"Message: {reminder.message}")
        print(f"{'='*60}\n")

        # Update reminder
        reminder.last_triggered = datetime.utcnow()
        reminder.trigger_count += 1

        # Call registered callbacks
        if reminder.callback:
            try:
                reminder.callback(reminder)
            except Exception as e:
                print(f"Callback error: {e}")

        for callback in self.callbacks.get(reminder.reminder_type, []):
            try:
                callback(reminder)
            except Exception as e:
                print(f"Callback error: {e}")

        # Schedule next trigger for recurring reminders
        if reminder.frequency != ReminderFrequency.ONCE:
            reminder.next_trigger = self._calculate_next_trigger(reminder)
        else:
            # Remove one-time reminders
            del self.reminders[reminder.reminder_id]

        self._save_reminders()

    def _calculate_next_trigger(self, reminder: Reminder) -> datetime:
        """Calculate next trigger time for recurring reminder"""
        current_trigger = reminder.next_trigger

        if reminder.frequency == ReminderFrequency.HOURLY:
            return current_trigger + timedelta(hours=1)
        elif reminder.frequency == ReminderFrequency.DAILY:
            return current_trigger + timedelta(days=1)
        elif reminder.frequency == ReminderFrequency.WEEKLY:
            return current_trigger + timedelta(weeks=1)
        elif reminder.frequency == ReminderFrequency.MONTHLY:
            return current_trigger + timedelta(days=30)
        else:
            return current_trigger + timedelta(hours=1)

    def get_status(self) -> Dict[str, Any]:
        """Get reminder engine status"""
        now = datetime.utcnow()
        upcoming = []

        for reminder in self.reminders.values():
            if now < reminder.next_trigger:
                upcoming.append({
                    "id": reminder.reminder_id,
                    "title": reminder.title,
                    "type": reminder.reminder_type.value,
                    "trigger_in": (reminder.next_trigger - now).total_seconds() / 60,  # minutes
                })

        upcoming.sort(key=lambda x: x["trigger_in"])

        return {
            "running": self.running,
            "total_reminders": len(self.reminders),
            "pending": len(self.get_pending_reminders()),
            "upcoming": upcoming[:10],  # Next 10
        }
