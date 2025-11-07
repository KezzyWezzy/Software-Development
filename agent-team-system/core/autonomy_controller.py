"""
Autonomy Controller

Manages system autonomy levels and controls what operations
agents can perform without human approval.
"""

import json
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
import logging


class OperationCategory(Enum):
    """Categories of operations agents can perform"""
    READ_FILE = "read_file"
    WRITE_FILE = "write_file"
    DELETE_FILE = "delete_file"
    EXECUTE_COMMAND = "execute_command"
    NETWORK_REQUEST = "network_request"
    DATABASE_QUERY = "database_query"
    DATABASE_WRITE = "database_write"
    GIT_COMMIT = "git_commit"
    GIT_PUSH = "git_push"
    INSTALL_PACKAGE = "install_package"
    MODIFY_CONFIG = "modify_config"
    CREATE_BACKUP = "create_backup"
    RESTORE_BACKUP = "restore_backup"


class OperationRisk(Enum):
    """Risk levels for operations"""
    SAFE = "safe"  # Read-only, no side effects
    LOW = "low"  # Reversible operations
    MEDIUM = "medium"  # Operations with side effects
    HIGH = "high"  # Potentially destructive
    CRITICAL = "critical"  # Highly destructive or sensitive


class AutonomyController:
    """
    Controls what operations agents can perform autonomously.

    Features:
    - Configurable autonomy levels
    - Operation categorization and risk assessment
    - Pre-approved operation lists
    - Safety boundaries
    - Approval requirement checking
    """

    def __init__(self, workspace_dir: Path, config_file: Optional[Path] = None):
        self.workspace_dir = workspace_dir
        self.config_file = config_file or workspace_dir / "config" / "autonomy_config.json"

        # Default autonomy settings
        self.autonomy_level = "semi_auto"  # manual, semi_auto, full_auto

        # Pre-approved categories per autonomy level
        self.approved_categories: Dict[str, Set[OperationCategory]] = {
            "manual": set(),  # Nothing approved
            "semi_auto": {
                OperationCategory.READ_FILE,
                OperationCategory.WRITE_FILE,
                OperationCategory.EXECUTE_COMMAND,
                OperationCategory.DATABASE_QUERY,
                OperationCategory.CREATE_BACKUP,
            },
            "full_auto": {
                OperationCategory.READ_FILE,
                OperationCategory.WRITE_FILE,
                OperationCategory.DELETE_FILE,
                OperationCategory.EXECUTE_COMMAND,
                OperationCategory.NETWORK_REQUEST,
                OperationCategory.DATABASE_QUERY,
                OperationCategory.DATABASE_WRITE,
                OperationCategory.GIT_COMMIT,
                OperationCategory.CREATE_BACKUP,
                OperationCategory.MODIFY_CONFIG,
            }
        }

        # Operation risk levels
        self.operation_risks: Dict[OperationCategory, OperationRisk] = {
            OperationCategory.READ_FILE: OperationRisk.SAFE,
            OperationCategory.WRITE_FILE: OperationRisk.LOW,
            OperationCategory.DELETE_FILE: OperationRisk.HIGH,
            OperationCategory.EXECUTE_COMMAND: OperationRisk.MEDIUM,
            OperationCategory.NETWORK_REQUEST: OperationRisk.MEDIUM,
            OperationCategory.DATABASE_QUERY: OperationRisk.SAFE,
            OperationCategory.DATABASE_WRITE: OperationRisk.MEDIUM,
            OperationCategory.GIT_COMMIT: OperationRisk.LOW,
            OperationCategory.GIT_PUSH: OperationRisk.HIGH,
            OperationCategory.INSTALL_PACKAGE: OperationRisk.MEDIUM,
            OperationCategory.MODIFY_CONFIG: OperationRisk.MEDIUM,
            OperationCategory.CREATE_BACKUP: OperationRisk.SAFE,
            OperationCategory.RESTORE_BACKUP: OperationRisk.HIGH,
        }

        # Safety boundaries - operations never allowed without approval
        self.always_require_approval: Set[OperationCategory] = {
            OperationCategory.GIT_PUSH,
            OperationCategory.RESTORE_BACKUP,
        }

        # Load config
        self._load_config()

        # Setup logging
        self.logger = logging.getLogger("autonomy_controller")

    def _load_config(self):
        """Load autonomy configuration from file"""
        if not self.config_file.exists():
            self._save_config()  # Create default
            return

        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)

            self.autonomy_level = config.get("autonomy_level", "semi_auto")

            # Load approved categories
            for level, categories in config.get("approved_categories", {}).items():
                self.approved_categories[level] = {
                    OperationCategory(cat) for cat in categories
                }

            # Load always_require_approval
            if "always_require_approval" in config:
                self.always_require_approval = {
                    OperationCategory(cat) for cat in config["always_require_approval"]
                }

        except Exception as e:
            self.logger.error(f"Failed to load autonomy config: {e}")

    def _save_config(self):
        """Save autonomy configuration to file"""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)

        config = {
            "autonomy_level": self.autonomy_level,
            "approved_categories": {
                level: [cat.value for cat in categories]
                for level, categories in self.approved_categories.items()
            },
            "always_require_approval": [cat.value for cat in self.always_require_approval],
            "last_updated": datetime.utcnow().isoformat(),
        }

        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)

    def set_autonomy_level(self, level: str):
        """
        Set system autonomy level

        Args:
            level: One of 'manual', 'semi_auto', 'full_auto'
        """
        if level not in ["manual", "semi_auto", "full_auto"]:
            raise ValueError(f"Invalid autonomy level: {level}")

        old_level = self.autonomy_level
        self.autonomy_level = level
        self._save_config()

        self.logger.info(f"Autonomy level changed: {old_level} -> {level}")

    def requires_approval(
        self,
        operation: OperationCategory,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Check if an operation requires approval

        Args:
            operation: Operation category
            context: Optional context about the operation

        Returns:
            True if approval required
        """
        # Always require approval for certain operations
        if operation in self.always_require_approval:
            return True

        # In manual mode, everything requires approval
        if self.autonomy_level == "manual":
            return True

        # Check if operation is approved for current autonomy level
        approved = self.approved_categories.get(self.autonomy_level, set())

        if operation not in approved:
            return True

        # Context-based checks
        if context:
            # Check risk level
            risk = self.operation_risks.get(operation, OperationRisk.MEDIUM)

            # In semi_auto mode, require approval for high-risk operations
            if self.autonomy_level == "semi_auto" and risk in [OperationRisk.HIGH, OperationRisk.CRITICAL]:
                return True

            # Check specific context flags
            if context.get("force_approval"):
                return True

            # Check path restrictions
            if operation in [OperationCategory.WRITE_FILE, OperationCategory.DELETE_FILE]:
                path = context.get("path", "")
                if self._is_protected_path(path):
                    return True

        return False

    def _is_protected_path(self, path: str) -> bool:
        """Check if path is protected and requires approval"""
        protected_patterns = [
            ".git/",
            "config/",
            ".env",
            "secrets",
            "credentials",
        ]

        path_lower = path.lower()
        return any(pattern in path_lower for pattern in protected_patterns)

    def approve_operation(
        self,
        operation: OperationCategory,
        reason: str,
        expiry: Optional[str] = None
    ) -> str:
        """
        Manually approve an operation category

        Args:
            operation: Operation to approve
            reason: Reason for approval
            expiry: Optional expiry timestamp

        Returns:
            Approval ID
        """
        # Add to approved categories for current level
        if self.autonomy_level in self.approved_categories:
            self.approved_categories[self.autonomy_level].add(operation)

        self._save_config()

        approval_id = f"approval_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        self.logger.info(f"Operation approved: {operation.value}", extra={
            "approval_id": approval_id,
            "reason": reason,
            "expiry": expiry
        })

        return approval_id

    def revoke_approval(self, operation: OperationCategory):
        """Revoke approval for an operation category"""
        for level in self.approved_categories:
            self.approved_categories[level].discard(operation)

        self._save_config()
        self.logger.info(f"Operation approval revoked: {operation.value}")

    def get_approved_operations(self) -> List[str]:
        """Get list of currently approved operations"""
        approved = self.approved_categories.get(self.autonomy_level, set())
        return [op.value for op in approved]

    def get_status(self) -> Dict[str, Any]:
        """Get autonomy controller status"""
        return {
            "autonomy_level": self.autonomy_level,
            "approved_operations": self.get_approved_operations(),
            "always_require_approval": [op.value for op in self.always_require_approval],
            "operation_count_by_risk": self._count_operations_by_risk(),
        }

    def _count_operations_by_risk(self) -> Dict[str, int]:
        """Count operations by risk level"""
        counts = {risk.value: 0 for risk in OperationRisk}

        for op, risk in self.operation_risks.items():
            counts[risk.value] += 1

        return counts

    def create_safety_report(self) -> Dict[str, Any]:
        """
        Generate a safety report for current configuration

        Returns:
            Safety analysis report
        """
        approved = self.approved_categories.get(self.autonomy_level, set())

        high_risk_approved = [
            op.value for op in approved
            if self.operation_risks.get(op, OperationRisk.MEDIUM) in [OperationRisk.HIGH, OperationRisk.CRITICAL]
        ]

        return {
            "autonomy_level": self.autonomy_level,
            "total_approved_operations": len(approved),
            "high_risk_operations_approved": len(high_risk_approved),
            "high_risk_operations_list": high_risk_approved,
            "safety_score": self._calculate_safety_score(approved),
            "recommendations": self._generate_safety_recommendations(approved),
            "timestamp": datetime.utcnow().isoformat(),
        }

    def _calculate_safety_score(self, approved_operations: Set[OperationCategory]) -> int:
        """Calculate safety score (0-100, higher is safer)"""
        if not approved_operations:
            return 100

        total_risk = 0
        risk_values = {
            OperationRisk.SAFE: 0,
            OperationRisk.LOW: 1,
            OperationRisk.MEDIUM: 2,
            OperationRisk.HIGH: 4,
            OperationRisk.CRITICAL: 8,
        }

        for op in approved_operations:
            risk = self.operation_risks.get(op, OperationRisk.MEDIUM)
            total_risk += risk_values[risk]

        max_possible_risk = len(approved_operations) * 8
        safety_score = max(0, 100 - int((total_risk / max_possible_risk) * 100))

        return safety_score

    def _generate_safety_recommendations(self, approved_operations: Set[OperationCategory]) -> List[str]:
        """Generate safety recommendations based on approved operations"""
        recommendations = []

        # Check for high-risk operations
        high_risk_ops = [
            op for op in approved_operations
            if self.operation_risks.get(op, OperationRisk.MEDIUM) in [OperationRisk.HIGH, OperationRisk.CRITICAL]
        ]

        if high_risk_ops and self.autonomy_level == "full_auto":
            recommendations.append(
                "Consider switching to semi_auto mode due to approved high-risk operations"
            )

        if OperationCategory.DELETE_FILE in approved_operations:
            recommendations.append(
                "DELETE_FILE is approved - ensure backup system is active"
            )

        if OperationCategory.GIT_PUSH in approved_operations:
            recommendations.append(
                "GIT_PUSH is approved - ensure proper branch protection is configured"
            )

        if not recommendations:
            recommendations.append("Current configuration appears safe")

        return recommendations
