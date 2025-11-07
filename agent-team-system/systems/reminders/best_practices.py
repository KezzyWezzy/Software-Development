"""
Best Practices System

Defines and enforces best practices for agent team development.
Provides dos and don'ts with contextual reminders.
"""

import json
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from .reminder_engine import ReminderEngine, ReminderType, ReminderPriority, ReminderFrequency


class PracticeCategory(Enum):
    """Categories of best practices"""
    CODE_QUALITY = "code_quality"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    SECURITY = "security"
    PERFORMANCE = "performance"
    GIT_WORKFLOW = "git_workflow"
    DEPLOYMENT = "deployment"
    MONITORING = "monitoring"


class PracticeSeverity(Enum):
    """Severity levels for practice violations"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class BestPractice:
    """Individual best practice"""

    def __init__(
        self,
        practice_id: str,
        title: str,
        category: PracticeCategory,
        do_this: str,
        dont_do_this: str,
        reason: str,
        severity: PracticeSeverity,
        examples: Optional[Dict[str, str]] = None,
        resources: Optional[List[str]] = None
    ):
        self.practice_id = practice_id
        self.title = title
        self.category = category
        self.do_this = do_this
        self.dont_do_this = dont_do_this
        self.reason = reason
        self.severity = severity
        self.examples = examples or {}
        self.resources = resources or []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "practice_id": self.practice_id,
            "title": self.title,
            "category": self.category.value,
            "do_this": self.do_this,
            "dont_do_this": self.dont_do_this,
            "reason": self.reason,
            "severity": self.severity.value,
            "examples": self.examples,
            "resources": self.resources,
        }


class BestPracticesManager:
    """
    Manages best practices and integrates with reminder system

    Features:
    - Pre-defined best practices
    - Custom practice definitions
    - Automated reminders
    - Violation tracking
    - Practice suggestions
    """

    def __init__(self, workspace_dir: Path, reminder_engine: Optional[ReminderEngine] = None):
        self.workspace_dir = workspace_dir
        self.practices_dir = workspace_dir / "best_practices"
        self.practices_file = self.practices_dir / "practices.json"
        self.violations_file = self.practices_dir / "violations.json"

        self.reminder_engine = reminder_engine

        self.practices: Dict[str, BestPractice] = {}
        self.violations: List[Dict[str, Any]] = []

        # Setup
        self.practices_dir.mkdir(parents=True, exist_ok=True)
        self._load_practices()
        self._load_violations()
        self._initialize_default_practices()

    def _initialize_default_practices(self):
        """Initialize default best practices"""
        default_practices = [
            # Code Quality
            BestPractice(
                practice_id="cq_001",
                title="Write Descriptive Commit Messages",
                category=PracticeCategory.CODE_QUALITY,
                do_this="Write clear, descriptive commit messages that explain WHY the change was made",
                dont_do_this="Use vague messages like 'fix', 'update', or 'changes'",
                reason="Good commit messages help team members understand the history and intent of changes",
                severity=PracticeSeverity.WARNING,
                examples={
                    "good": "Add input validation to prevent SQL injection in user login",
                    "bad": "fix login"
                },
                resources=["https://chris.beams.io/posts/git-commit/"]
            ),
            BestPractice(
                practice_id="cq_002",
                title="Keep Functions Small and Focused",
                category=PracticeCategory.CODE_QUALITY,
                do_this="Write functions that do one thing well, typically under 50 lines",
                dont_do_this="Create large functions that do multiple unrelated things",
                reason="Small, focused functions are easier to test, understand, and maintain",
                severity=PracticeSeverity.WARNING,
                examples={
                    "good": "Separate data fetching, processing, and display into different functions",
                    "bad": "One 500-line function that does everything"
                }
            ),

            # Testing
            BestPractice(
                practice_id="test_001",
                title="Write Tests Before Pushing Code",
                category=PracticeCategory.TESTING,
                do_this="Write unit tests for new features and ensure they pass before committing",
                dont_do_this="Push code without any tests or with failing tests",
                reason="Tests catch bugs early and ensure code works as expected",
                severity=PracticeSeverity.ERROR,
                examples={
                    "good": "Write tests for all public methods and edge cases",
                    "bad": "Skip testing and hope it works in production"
                }
            ),
            BestPractice(
                practice_id="test_002",
                title="Test Edge Cases and Error Conditions",
                category=PracticeCategory.TESTING,
                do_this="Test boundary conditions, null values, empty inputs, and error scenarios",
                dont_do_this="Only test the 'happy path' where everything works perfectly",
                reason="Most bugs occur in edge cases and error handling",
                severity=PracticeSeverity.WARNING
            ),

            # Documentation
            BestPractice(
                practice_id="doc_001",
                title="Document Complex Logic and Decisions",
                category=PracticeCategory.DOCUMENTATION,
                do_this="Add comments explaining WHY complex code works the way it does",
                dont_do_this="Leave complex algorithms and business logic uncommented",
                reason="Future developers (including yourself) need to understand the reasoning",
                severity=PracticeSeverity.WARNING,
                examples={
                    "good": "# Using binary search here because data is pre-sorted, giving O(log n) complexity",
                    "bad": "# Loop through data"
                }
            ),
            BestPractice(
                practice_id="doc_002",
                title="Keep Documentation Up-to-Date",
                category=PracticeCategory.DOCUMENTATION,
                do_this="Update documentation when code changes",
                dont_do_this="Let documentation become outdated and inaccurate",
                reason="Outdated documentation is worse than no documentation",
                severity=PracticeSeverity.WARNING
            ),

            # Security
            BestPractice(
                practice_id="sec_001",
                title="Never Commit Secrets or Credentials",
                category=PracticeCategory.SECURITY,
                do_this="Use environment variables or secret managers for sensitive data",
                dont_do_this="Hardcode API keys, passwords, or tokens in source code",
                reason="Committed secrets can be accessed by anyone with repo access",
                severity=PracticeSeverity.CRITICAL,
                examples={
                    "good": "api_key = os.getenv('API_KEY')",
                    "bad": "api_key = 'sk_live_123456789'"
                }
            ),
            BestPractice(
                practice_id="sec_002",
                title="Validate and Sanitize All User Input",
                category=PracticeCategory.SECURITY,
                do_this="Validate, sanitize, and escape all user input before using it",
                dont_do_this="Trust user input or directly use it in queries/commands",
                reason="Unvalidated input is the #1 security vulnerability",
                severity=PracticeSeverity.CRITICAL
            ),

            # Performance
            BestPractice(
                practice_id="perf_001",
                title="Optimize Database Queries",
                category=PracticeCategory.PERFORMANCE,
                do_this="Use indexes, limit results, and avoid N+1 query problems",
                dont_do_this="Load entire tables or make queries in loops",
                reason="Poor database queries are often the biggest performance bottleneck",
                severity=PracticeSeverity.WARNING
            ),

            # Git Workflow
            BestPractice(
                practice_id="git_001",
                title="Create Feature Branches for New Work",
                category=PracticeCategory.GIT_WORKFLOW,
                do_this="Create a new branch for each feature or bug fix",
                dont_do_this="Commit directly to main/master branch",
                reason="Branches allow for isolated development and easier code review",
                severity=PracticeSeverity.WARNING
            ),
            BestPractice(
                practice_id="git_002",
                title="Review Changes Before Committing",
                category=PracticeCategory.GIT_WORKFLOW,
                do_this="Use git diff to review changes before staging them",
                dont_do_this="Blindly commit all changes with git add .",
                reason="Prevents committing unintended changes or debug code",
                severity=PracticeSeverity.WARNING
            ),

            # Deployment
            BestPractice(
                practice_id="deploy_001",
                title="Create Backups Before Deployment",
                category=PracticeCategory.DEPLOYMENT,
                do_this="Always create a backup before deploying to production",
                dont_do_this="Deploy without a rollback plan",
                reason="Enables quick recovery if deployment goes wrong",
                severity=PracticeSeverity.CRITICAL
            ),

            # Monitoring
            BestPractice(
                practice_id="mon_001",
                title="Log Important Operations",
                category=PracticeCategory.MONITORING,
                do_this="Log important operations, errors, and state changes",
                dont_do_this="Run without logging or only log to console",
                reason="Logs are essential for debugging and monitoring production issues",
                severity=PracticeSeverity.WARNING
            ),
        ]

        # Add practices that don't already exist
        for practice in default_practices:
            if practice.practice_id not in self.practices:
                self.practices[practice.practice_id] = practice

        self._save_practices()

    def _load_practices(self):
        """Load practices from disk"""
        if not self.practices_file.exists():
            return

        try:
            with open(self.practices_file, 'r') as f:
                data = json.load(f)

            for practice_data in data.get("practices", []):
                practice = BestPractice(
                    practice_id=practice_data["practice_id"],
                    title=practice_data["title"],
                    category=PracticeCategory(practice_data["category"]),
                    do_this=practice_data["do_this"],
                    dont_do_this=practice_data["dont_do_this"],
                    reason=practice_data["reason"],
                    severity=PracticeSeverity(practice_data["severity"]),
                    examples=practice_data.get("examples", {}),
                    resources=practice_data.get("resources", [])
                )
                self.practices[practice.practice_id] = practice

        except Exception as e:
            print(f"Failed to load practices: {e}")

    def _save_practices(self):
        """Save practices to disk"""
        data = {
            "practices": [p.to_dict() for p in self.practices.values()],
            "last_updated": datetime.utcnow().isoformat(),
        }

        with open(self.practices_file, 'w') as f:
            json.dump(data, f, indent=2)

    def _load_violations(self):
        """Load violation history"""
        if not self.violations_file.exists():
            return

        try:
            with open(self.violations_file, 'r') as f:
                data = json.load(f)
            self.violations = data.get("violations", [])
        except Exception:
            self.violations = []

    def _save_violations(self):
        """Save violation history"""
        data = {
            "violations": self.violations[-1000:],  # Keep last 1000
            "last_updated": datetime.utcnow().isoformat(),
        }

        with open(self.violations_file, 'w') as f:
            json.dump(data, f, indent=2)

    def record_violation(
        self,
        practice_id: str,
        context: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """Record a best practice violation"""
        if practice_id not in self.practices:
            return

        practice = self.practices[practice_id]

        violation = {
            "practice_id": practice_id,
            "title": practice.title,
            "category": practice.category.value,
            "severity": practice.severity.value,
            "context": context,
            "details": details or {},
            "timestamp": datetime.utcnow().isoformat(),
        }

        self.violations.append(violation)
        self._save_violations()

    def get_practices_by_category(self, category: PracticeCategory) -> List[BestPractice]:
        """Get all practices in a category"""
        return [
            p for p in self.practices.values()
            if p.category == category
        ]

    def get_practice(self, practice_id: str) -> Optional[BestPractice]:
        """Get a specific practice"""
        return self.practices.get(practice_id)

    def setup_reminders(self):
        """Setup automated reminders for best practices"""
        if not self.reminder_engine:
            return

        # Daily reminders for critical practices
        critical_practices = [
            p for p in self.practices.values()
            if p.severity == PracticeSeverity.CRITICAL
        ]

        for practice in critical_practices[:3]:  # Top 3 critical
            self.reminder_engine.create_recurring_reminder(
                title=f"Best Practice: {practice.title}",
                message=f"✓ DO: {practice.do_this}\n✗ DON'T: {practice.dont_do_this}\n\nWhy: {practice.reason}",
                reminder_type=ReminderType.BEST_PRACTICE,
                frequency=ReminderFrequency.DAILY,
                priority=ReminderPriority.HIGH,
                start_time=datetime.utcnow() + timedelta(hours=1),
                practice_id=practice.practice_id
            )

        # Weekly reminders for warnings
        warning_practices = [
            p for p in self.practices.values()
            if p.severity == PracticeSeverity.WARNING
        ]

        for i, practice in enumerate(warning_practices[:5]):  # Top 5 warnings
            self.reminder_engine.create_recurring_reminder(
                title=f"Best Practice: {practice.title}",
                message=f"✓ DO: {practice.do_this}\n✗ DON'T: {practice.dont_do_this}\n\nWhy: {practice.reason}",
                reminder_type=ReminderType.BEST_PRACTICE,
                frequency=ReminderFrequency.WEEKLY,
                priority=ReminderPriority.MEDIUM,
                start_time=datetime.utcnow() + timedelta(days=i),
                practice_id=practice.practice_id
            )

    def generate_checklist(self, category: Optional[PracticeCategory] = None) -> str:
        """Generate a checklist of best practices"""
        if category:
            practices = self.get_practices_by_category(category)
            title = f"{category.value.replace('_', ' ').title()} Best Practices Checklist"
        else:
            practices = list(self.practices.values())
            title = "All Best Practices Checklist"

        # Sort by severity
        practices.sort(key=lambda p: -p.severity.value.count('c'))  # Critical first

        lines = [
            f"# {title}",
            "",
            f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
            ""
        ]

        for practice in practices:
            lines.extend([
                f"## [{practice.severity.value.upper()}] {practice.title}",
                "",
                f"**✓ DO:** {practice.do_this}",
                "",
                f"**✗ DON'T:** {practice.dont_do_this}",
                "",
                f"**Why:** {practice.reason}",
                ""
            ])

            if practice.examples:
                lines.append("**Examples:**")
                for label, example in practice.examples.items():
                    lines.append(f"- {label}: `{example}`")
                lines.append("")

            lines.append("---")
            lines.append("")

        return "\n".join(lines)

    def get_violation_summary(self) -> Dict[str, Any]:
        """Get summary of violations"""
        by_category = {}
        by_severity = {}

        for violation in self.violations:
            category = violation["category"]
            severity = violation["severity"]

            by_category[category] = by_category.get(category, 0) + 1
            by_severity[severity] = by_severity.get(severity, 0) + 1

        return {
            "total_violations": len(self.violations),
            "by_category": by_category,
            "by_severity": by_severity,
            "recent_violations": self.violations[-10:],
        }
